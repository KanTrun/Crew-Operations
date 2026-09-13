"""Truy nguyên 221 dòng `fb_eval%` trong `fb_review_queue` — chỉ đọc.

Mục đích: xác định rác này sinh ra TRƯỚC hay TRONG cửa sổ kiểm thử V3
(2026-09-13 13:26 trở đi), để không đổ oan cho đợt test và không xoá nhầm
dữ liệu của phiên làm việc song song.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Log kiểm thử thường bị redirect ra file với codec cp1252 trên Windows →
# ép UTF-8 để dấu tiếng Việt không làm crash script giữa chừng.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "quan.db"

MOC_KIEM_THU = "2026-09-13T13:26"


def main() -> int:
    cx = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        cols = [r[1] for r in cx.execute("PRAGMA table_info(fb_review_queue)")]
        print(f"cot_fb_review_queue={cols}")
        col_ts = next(
            (c for c in ("created_at", "timestamp", "received_at", "updated_at") if c in cols),
            None,
        )
        if not col_ts:
            print("KHONG_CO_COT_THOI_GIAN — không truy nguyên được")
            return 1
        print(f"=== phan bo theo {col_ts} (fb_eval%) ===")
        for row in cx.execute(
            f"SELECT substr({col_ts},1,13) AS gio, COUNT(*) FROM fb_review_queue "
            f"WHERE external_thread_id LIKE 'fb_eval%' GROUP BY gio ORDER BY gio"
        ):
            print(f"  {row[0]}  n={row[1]}")
        mn, mx = cx.execute(
            f"SELECT MIN({col_ts}), MAX({col_ts}) FROM fb_review_queue "
            f"WHERE external_thread_id LIKE 'fb_eval%'"
        ).fetchone()
        print(f"min={mn} max={mx}")
        print(f"moc_cua_so_kiem_thu_V3={MOC_KIEM_THU} (GĐ1 smoke)")
        if mn is None:
            # Đã dọn ở GĐ10 — ghi lại kết luận của lần truy nguyên TRƯỚC khi reset.
            print("DA_DON_SACH: 0 dong fb_eval con lai.")
            print(
                "Ket luan cua lan truy nguyen TRUOC reset (2026-09-13 15:1x): "
                "n=221, min=2026-09-03T17:40:13Z max=2026-09-03T18:50:44Z "
                "=> TRUOC_KIEM_THU 10 ngay, khong phai do dot test V3."
            )
        elif str(mx) < MOC_KIEM_THU:
            print("KET_LUAN=TRUOC_KIEM_THU (không phải do đợt test này)")
        else:
            print("KET_LUAN=TRONG_KIEM_THU (cần dọn)")
    finally:
        cx.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
