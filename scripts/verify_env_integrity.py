"""GĐ10 — xác minh `.env` thật chưa từng bị thay đổi trong suốt đợt kiểm thử.

In ra TRẠNG THÁI (có/không, độ dài) chứ không in giá trị, để không lộ secret
vào log kiểm thử. Tiêu chí: các cờ live thật vẫn nguyên, và các cờ an toàn
của harness e2e (CA_AGENT_MODE=replay...) KHÔNG bị ghi ngược vào `.env`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"

# Khoá live thật — phải còn nguyên (không rỗng) sau kiểm thử.
KHOA_LIVE = (
    "NHIPQUAN_FB_PAGE_TOKEN",
    "NHIPQUAN_FB_APP_SECRET",
    "NHIPQUAN_ZALO_ACCESS_TOKEN",
    "NHIPQUAN_TELEGRAM_BOT_TOKEN",
)
# Cờ chế độ — phải giữ giá trị live như trước kiểm thử.
CO_CHE_DO = {
    "CA_AGENT_MODE": "live",
    "NHIPQUAN_PAGE_MODE": "live",
    "NHIPQUAN_FB_AUTO_SEND": "1",
}
# Dấu vết harness e2e — KHÔNG được phép xuất hiện trong `.env` thật.
DAU_VET_E2E = ("NHIPQUAN_MSG_BACKEND", "NHIPQUAN_ALLOW_MSG_REPLAY", "NHIPQUAN_PBKDF2_VONG")


def _parse(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> int:
    if not ENV.is_file():
        print("ENV_MISSING")
        return 1
    env = _parse(ENV.read_text(encoding="utf-8", errors="replace"))

    lo = []

    # Tiêu chí chính: `.env` phải KHÔNG bị ghi trong cửa sổ kiểm thử.
    # Cột mốc bắt đầu đợt kiểm thử toàn diện V3 (GĐ1 smoke trên Docker).
    moc_kiem_thu = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
    mtime = datetime.fromtimestamp(ENV.stat().st_mtime, tz=timezone.utc)
    khong_bi_ghi = mtime < moc_kiem_thu
    print(f"mtime_env={mtime.isoformat()} moc_kiem_thu={moc_kiem_thu.isoformat()}")
    print(f"ENV_KHONG_BI_GHI={'OK' if khong_bi_ghi else 'DA_BI_GHI_TRONG_KIEM_THU'}")
    if not khong_bi_ghi:
        lo.append("mtime")

    # Khoá live: chỉ báo động khi khoá CÓ trong `.env` mà bị làm rỗng.
    # Khoá không tồn tại = chưa từng cấu hình, không phải dấu vết kiểm thử.
    for k in KHOA_LIVE:
        if k not in env:
            print(f"live_key {k}: khong_cau_hinh (bo qua)")
            continue
        v = env[k]
        trang_thai = f"CO_GIA_TRI(len={len(v)})" if v else "BI_LAM_RONG"
        print(f"live_key {k}: {trang_thai}")
        if not v:
            lo.append(k)

    for k, mong_muon in CO_CHE_DO.items():
        v = env.get(k, "")
        ok = v == mong_muon
        print(f"mode_flag {k}: {v!r} mong_muon={mong_muon!r} {'OK' if ok else 'LECH'}")
        if not ok:
            lo.append(k)

    # Harness e2e dùng `.env.e2e` riêng; nếu cờ của nó lọt vào `.env` thật
    # nghĩa là đã ghi nhầm — nguy cơ làm quán chạy chế độ replay.
    for k in DAU_VET_E2E:
        if k in env:
            print(f"DAU_VET_E2E {k}: XUAT_HIEN (harness da ghi nguoc vao .env!)")
            lo.append(k)
        else:
            print(f"DAU_VET_E2E {k}: khong co (dung)")

    print(f"so_dong_env={len(env)}")
    if lo:
        print(f"ENV_INTEGRITY=FAIL ({len(lo)} muc: {', '.join(lo)})")
        return 1
    print("ENV_INTEGRITY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
