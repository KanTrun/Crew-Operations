"""Worker nền NHỊP QUÁN — bộ chạy việc định kỳ với cổng thời gian tiêm được.

Việc định kỳ (mỗi job ghi mốc kv `worker_viec`, mỗi khoá một lần/ngày-tuần):

- ``brief_sang``    06:00 — sinh bản tin sáng (ca hôm nay, treo, tồn cảnh báo)
                    vào kv ``brief_hom_nay`` cho /hom-nay và /copilot đọc.
- ``solver_tuan``   22:00 Chủ nhật — chạy CP-SAT cho tuần sau, kết quả vào kv
                    ``worker_de_xuat_lich`` dạng đề xuất chờ quản lý duyệt
                    (worker KHÔNG tự công bố — đúng nguyên tắc người quyết).
- ``tong_ket_ngay`` 23:00 — gom tiêu thụ/hao phí trong ngày vào kv
                    ``tong_ket_ngay`` cho /hom-nay hiển thị cuối ngày.

Nhắc phiếu quá hạn (hai cấp) chạy mỗi chu kỳ như trước. Lõi không đụng
``time`` — test tất định bằng đồng hồ giả; ``main()`` chỉ thêm nhịp ngủ thật.
Mỗi cặp (phiếu, cấp) chỉ nhắn một lần — kv ``worker_da_nhac``, atomic.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from ca_agents.messaging import MessagePort, get_port
from ca_ops import escalate, load_run

from ca_api.orchestration import Clock
from ca_api.persist import kv_get, kv_mutate, kv_set, list_users

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

# ── Việc định kỳ — mỗi job một khoá mốc, chạy đúng một lần mỗi ngày/tuần ──────


def _da_chay(khoa: str, moc: str) -> bool:
    """Job đã chạy cho mốc (ngày YYYY-MM-DD hoặc tuần ISO) này chưa."""
    done = kv_get("worker_viec", {})
    return isinstance(done, dict) and done.get(khoa) == moc


def _danh_dau(khoa: str, moc: str) -> None:
    def mut(cur: dict[str, str]) -> dict[str, str]:
        cur[khoa] = moc
        return cur

    kv_mutate("worker_viec", mut, {})


def _sinh_brief_sang() -> str:
    """Brief sáng: ca hôm nay (từ phan_cong), treo chưa xong, tồn dưới ngưỡng."""
    phan_cong = kv_get("phan_cong", {}) or {}
    treo = [t for t in kv_get("treo", []) if isinstance(t, dict) and t.get("trang_thai") != "xong"]
    ton = [x for x in kv_get("tieu_thu", []) if isinstance(x, dict) and x.get("duoi_nguong")]
    brief = {
        "ngay": datetime.now(timezone.utc).date().isoformat(),
        "so_ca": len(phan_cong),
        "so_treo_mo": len(treo),
        "ton_canh_bao": [x.get("hang") for x in ton],
        "treo_dau": [str(t.get("noi_dung") or "")[:80] for t in treo[:3]],
    }
    kv_set("brief_hom_nay", brief)
    return f"ca={brief['so_ca']} treo={brief['so_treo_mo']} canh_bao={len(brief['ton_canh_bao'])}"


def _chay_solver_tuan() -> str:
    """Chạy solver cho tuần sau → đề xuất chờ duyệt. KHÔNG tự công bố."""
    from ca_solver import build_lich_input, solve_cpsat

    from ca_api.nhan_vien import list_nhan_vien_ops

    inp = build_lich_input(nhan_vien_ngoai=list_nhan_vien_ops())
    res = solve_cpsat(inp)
    de_xuat = {
        "ngay": datetime.now(timezone.utc).date().isoformat(),
        "status": res.status,
        "ok": res.ok,
        "phan_cong": res.phan_cong or {},
        "tong_so_luot": sum(len(v) for v in (res.phan_cong or {}).values()),
        "trang_thai": "cho_duyet",
        "ghi": "Worker xếp sẵn lịch tuần sau — quản lý xem rồi duyệt ở /roster hoặc /copilot.",
    }
    kv_set("worker_de_xuat_lich", de_xuat)
    return f"ok={res.ok} status={res.status} phan_cong={de_xuat['tong_so_luot']}"


def _tong_ket_ngay() -> str:
    """Gom số liệu tiêu thụ + hao phí đã ghi trong ngày."""
    hom_nay = datetime.now(timezone.utc).date().isoformat()
    ton = [x for x in kv_get("tieu_thu", []) if isinstance(x, dict) and str(x.get("ngay") or x.get("at") or "").startswith(hom_nay)]
    hp = [x for x in kv_get("waste_notes", []) if isinstance(x, dict) and str(x.get("ngay") or x.get("at") or "").startswith(hom_nay)]
    tong = {
        "ngay": hom_nay,
        "so_lan_kiem_ke": len(ton),
        "so_ghi_hao_phi": len(hp),
        "hang_kiem_ke": [x.get("hang") for x in ton],
    }
    kv_set("tong_ket_ngay", tong)
    return f"kiem_ke={tong['so_lan_kiem_ke']} hao_phi={tong['so_ghi_hao_phi']}"


def _quet_dinh_ky() -> list[str]:
    """Điều phối 3 job theo giờ máy thật. Trả danh sách kết quả để test."""
    now = datetime.now(timezone.utc)
    ngay = now.date().isoformat()
    ket_qua: list[str] = []

    if now.hour >= 6 and not _da_chay("brief_sang", ngay):
        ket_qua.append(f"brief_sang: {_sinh_brief_sang()}")
        _danh_dau("brief_sang", ngay)

    # Chủ nhật (weekday 6) sau 22h — xếp lịch tuần sau
    if now.weekday() == 6 and now.hour >= 22 and not _da_chay("solver_tuan", ngay):
        ket_qua.append(f"solver_tuan: {_chay_solver_tuan()}")
        _danh_dau("solver_tuan", ngay)

    if now.hour >= 23 and not _da_chay("tong_ket_ngay", ngay):
        ket_qua.append(f"tong_ket_ngay: {_tong_ket_ngay()}")
        _danh_dau("tong_ket_ngay", ngay)
    return ket_qua


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
        try:
            for dong in _quet_dinh_ky():
                log.info("dinh ky: %s", dong)
        except Exception:  # noqa: BLE001
            log.exception("viec dinh ky that bai — thu lai o chu ky tiep")
        time.sleep(chu_ky_s)


if __name__ == "__main__":
    main()
