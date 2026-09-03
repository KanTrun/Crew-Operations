"""Worker nhắc việc — tất định với đồng hồ giả, không sleep, không mạng."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from ca_agents.messaging import SendResult
from ca_api import worker
from ca_api.orchestration import Clock
from ca_api.persist import kv_get, kv_set
from ca_ops import dump_run, start_phieu


@dataclass
class FakeClock(Clock):
    ms: int

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.ms / 1000, UTC)

    def now_ms(self) -> int:
        return self.ms

    def now_iso(self) -> str:
        return self.now().strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RecordingPort:
    name = "fake"
    sent: list[tuple[str, str]] = field(default_factory=list)

    def send(self, to: str, text: str) -> SendResult:
        self.sent.append((to, text))
        return SendResult(ok=True, backend="fake", detail="recorded")


@pytest.fixture
def _reset_worker_state() -> None:
    kv_set("phieu", {})
    kv_set("worker_da_nhac", {})


def _mo_phieu(run_id: str, started_ms: int) -> None:
    run = start_phieu(
        run_id=run_id,
        mau="ban_giao_ca",
        nv_id="nv_03",
        ca_id="w1_c01",
        now_ms=started_ms,
        diem_danh=True,
    )
    bag = kv_get("phieu", {})
    bag[run_id] = dump_run(run)
    kv_set("phieu", bag)


PHUT = 60_000


def test_quet_im_lang_khi_chua_den_han(_reset_worker_state: None) -> None:
    _mo_phieu("p1", started_ms=0)
    port = RecordingPort()
    n = worker._quet(FakeClock(ms=10 * PHUT), port, han_phut=30)
    assert n == 0
    assert port.sent == []


def test_quet_nhan_vien_mot_lan_o_cap_nhac(_reset_worker_state: None) -> None:
    _mo_phieu("p1", started_ms=0)
    port = RecordingPort()
    assert worker._quet(FakeClock(ms=40 * PHUT), port, han_phut=30) == 1
    assert port.sent[0][0] == "nv_03"
    assert "hoàn thành" in port.sent[0][1]
    # lượt sau cùng cấp — không nhắn lại
    assert worker._quet(FakeClock(ms=50 * PHUT), port, han_phut=30) == 0
    assert len(port.sent) == 1


def test_quet_len_cap_bao_chu_quan(_reset_worker_state: None) -> None:
    _mo_phieu("p1", started_ms=0)
    port = RecordingPort()
    worker._quet(FakeClock(ms=40 * PHUT), port, han_phut=30)
    n = worker._quet(FakeClock(ms=70 * PHUT), port, han_phut=30)
    assert n == 1
    assert port.sent[-1][0] == "nv_02"  # hung — chủ quán, nv_02
    assert "chủ quán" in port.sent[-1][1]
    assert set(kv_get("worker_da_nhac", {})) == {"p1:nhac_nhan_vien", "p1:bao_chu_quan"}


def test_quet_bo_qua_phieu_dong(_reset_worker_state: None) -> None:
    _mo_phieu("p1", started_ms=0)
    bag = kv_get("phieu", {})
    bag["p1"]["closed"] = True
    kv_set("phieu", bag)
    port = RecordingPort()
    assert worker._quet(FakeClock(ms=999 * PHUT), port, han_phut=30) == 0
    assert port.sent == []
