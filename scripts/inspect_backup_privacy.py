"""Kiểm tra `data/backups/quan-pre-gd10-260913.db` có chứa dữ liệu khách THẬT không.

Chỉ đếm và phân loại nguồn, KHÔNG in nội dung tin nhắn. Quyết định: backup này
có được commit hay phải giữ ở local.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "backups" / "quan-pre-gd10-260913.db"


def main() -> int:
    if not DB.is_file():
        print(f"DB_MISSING {DB}")
        return 1
    cx = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        bang = [r[0] for r in cx.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        print(f"so_bang={len(bang)}")
        for t in ("fb_review_queue", "fb_processed_events", "inbox_msg", "users", "don_quay"):
            if t not in bang:
                continue
            n = cx.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {n}")
        if "fb_review_queue" in bang:
            print("=== fb_review_queue phan loai theo source ===")
            for row in cx.execute(
                "SELECT COALESCE(source,'(null)') AS s, COUNT(*) FROM fb_review_queue "
                "GROUP BY s ORDER BY 2 DESC"
            ):
                print(f"  source={row[0]!r} n={row[1]}")
            print("=== external_thread_id: chi dem theo loai tien to ===")
            for row in cx.execute(
                "SELECT CASE WHEN external_thread_id LIKE 'fb_eval%' THEN 'fb_eval(mo_phong)' "
                "WHEN external_thread_id LIKE 'mo_phong%' THEN 'mo_phong' "
                "ELSE 'khac(CAN_XEM)' END AS loai, COUNT(*) "
                "FROM fb_review_queue GROUP BY loai"
            ):
                print(f"  {row[0]}: {row[1]}")
        if "users" in bang:
            print("=== users: chi ten dang nhap + vai tro ===")
            for row in cx.execute("SELECT username, role FROM users ORDER BY username"):
                print(f"  {row[0]} / {row[1]}")
    finally:
        cx.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
