"""Worker nền NHỊP QUÁN — bộ chạy việc định kỳ với cổng thời gian tiêm được.

Việc hiện có: nhắc hai cấp cho phiếu đang mở (nhắc nhân viên → báo chủ quán),
theo `ca_ops.escalate`. Lõi `_quet(clock, port)` không đụng `time` nên test tất
định được bằng đồng hồ giả; `main()` chỉ thêm nhịp ngủ thật.

Mỗi cặp (phiếu, cấp) chỉ nhắn một lần — nhãn đã nhắn lưu ở kv `worker_da_nhac`,
đọc-ghi atomic qua `kv_mutate` nên api và worker không giẫm nhau.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from ca_agents.messaging import MessagePort, get_port
from ca_ops import escalate, load_run

from ca_api.orchestration import Clock
from ca_api.persist import kv_get, kv_mutate, list_users

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ca_api.worker")

NHAC_TEXT = "Phiếu {mau} ({id}) đang chờ bước tiếp theo — hoàn thành giúp quán nhé."
BAO_TEXT = "Phiếu {mau} ({id}) quá hạn hai lần ngưỡng — cần chủ quán để mắt."


def _chu_quan_nv_id() -> str:
    for u in list_users():
        if u.get("role") == "chu_quan":
            return str(u.get("nv_id") or u.get("username"))
    return "chu_quan"


def _quet(clock: Clock, port: MessagePort, *, han_phut: int = 30) -> int:
    """Một lượt quét: trả số tin đã gửi. Không ngủ, không đọc đồng hồ thật."""
    now_ms = clock.now_ms()
    runs: dict[str, Any] = kv_get("phieu", {})
    da_nhac: dict[str, str] = dict(kv_get("worker_da_nhac", {}))
    gui = 0

    for run_id, raw in sorted(runs.items()):
        if not isinstance(raw, dict) or raw.get("closed"):
            continue
        run = load_run(raw)
        level = escalate(run, now_ms, han_phut=han_phut)
        if level is None:
            continue
        khoa = f"{run_id}:{level}"
        if khoa in da_nhac:
            continue
        to = run.nv_id if level == "nhac_nhan_vien" else _chu_quan_nv_id()
        template = NHAC_TEXT if level == "nhac_nhan_vien" else BAO_TEXT
        text = template.format(mau=run.mau, id=run_id)
        res = port.send(to, text)
        log.info("worker %s -> %s (%s): ok=%s", khoa, to, res.backend, res.ok)
        da_nhac[khoa] = clock.now_iso()
        gui += 1

    if gui:

        def mut(cur: dict[str, str]) -> dict[str, str]:
            cur.update(da_nhac)
            return cur

        kv_mutate("worker_da_nhac", mut, {})
    return gui


def main() -> None:
    han_phut = int(os.environ.get("WORKER_HAN_PHUT", "30"))
    chu_ky_s = int(os.environ.get("WORKER_INTERVAL_S", "30"))
    port = get_port(None)
    log.info(
        "worker nhắc việc chạy (backend=%s, han=%s phút, chu kỳ=%s giây)",
        port.name,
        han_phut,
        chu_ky_s,
    )
    while True:
        try:
            n = _quet(Clock(), port, han_phut=han_phut)
            if n:
                log.info("đã gửi %s tin nhắc", n)
        except Exception:  # noqa: BLE001 — worker phải sống sót qua một lượt hỏng
            log.exception("luot quet that bai — thu lai o chu ky tiep")
        time.sleep(chu_ky_s)


if __name__ == "__main__":
    main()
