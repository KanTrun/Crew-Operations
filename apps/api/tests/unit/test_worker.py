"""Worker nhắc việc — tất định với đồng hồ giả, không sleep, không mạng."""

from __future__ import annotations

from dataclasses import dataclass, field
try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc

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


# ── Việc định kỳ: brief sáng / solver tuần / tổng kết ngày ───────────────────


@pytest.fixture
def _reset_dinh_ky(monkeypatch: pytest.MonkeyPatch) -> None:
    kv_set("worker_viec", {})
    kv_set("phan_cong", {"w1_c01": ["nv_01"]})
    kv_set("treo", [{"id": "t1", "noi_dung": "hết ống hút", "trang_thai": "dang_cho"}])
    kv_set("tieu_thu", [{"hang": "sua_tuoi", "so_luong": 1, "duoi_nguong": True, "ngay": "2026-09-06"}])
    monkeypatch.setattr(worker, "_da_chay", lambda k, m: False)


def test_sinh_brief_sang(_reset_dinh_ky: None) -> None:
    res = worker._sinh_brief_sang()
    brief = kv_get("brief_hom_nay", None)
    assert brief is not None
    assert brief["so_ca"] == 1
    assert brief["so_treo_mo"] == 1
    assert "sua_tuoi" in brief["ton_canh_bao"]
    assert "ca=1" in res


def test_solver_tuan_tao_de_xuat_cho_duyet(_reset_dinh_ky: None) -> None:
    """Worker xếp lịch nhưng KHÔNG công bố — đề xuất chờ quản lý.

    Tạo đủ 16 NV thật trước khi xếp: 3 user mặc định không thể phủ 70
    role-slot (91 lượt; mỗi ngày 10 role-slot mà C03/C04 chặn 1 người
    2 khung trùng) — solver INFEASIBLE là đúng, không phải bug.
    """
    from ca_api.persist import register

    for i in range(13):
        register(f"nv_pool_{i}", f"matkhautot{i}9x", f"NV Pool {i}")
    worker._chay_solver_tuan()
    de = kv_get("worker_de_xuat_lich", None)
    assert de is not None
    assert de["trang_thai"] == "cho_duyet"
    assert de["tong_so_luot"] > 0
    lifecycle = kv_get("lich_tuan_lifecycle", {})
    # chưa duyệt → lifecycle không đổi thành công bố
    assert lifecycle.get("trang_thai") != "da_cong_bo"


def test_quet_dinh_ky_chay_dung_mot_lan(_reset_dinh_ky: None) -> None:
    lan1 = worker._quet_dinh_ky()
    # giờ thật ≥ 6h sáng nên brief phải chạy ngay (nếu máy chạy ban ngày)
    # — nhưng để tất định, kiểm tra logic mốc: gọi lần 2 với _da_chay thật
    monkey = worker._da_chay
    worker._da_chay = lambda k, m: True  # giả đã chạy
    lan2 = worker._quet_dinh_ky()
    worker._da_chay = monkey
    assert isinstance(lan1, list)
    assert lan2 == []


def test_tong_ket_ngay(_reset_dinh_ky: None) -> None:
    from datetime import datetime, timezone

    hom_nay = datetime.now(timezone.utc).date().isoformat()
    kv_set("tieu_thu", [{"hang": "sua_tuoi", "so_luong": 8, "duoi_nguong": False, "ngay": hom_nay}])
    kv_set("waste_notes", [{"id": "hp1", "noi_dung": "đổ 2 ly", "ngay": hom_nay}])
    res = worker._tong_ket_ngay()
    tong = kv_get("tong_ket_ngay", None)
    assert tong is not None
    assert "kiem_ke=1" in res
    assert tong["so_ghi_hao_phi"] == 1
