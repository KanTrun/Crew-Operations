"""GĐ10 clean check — đếm rác do e2e để lại trong `data/quan.db` (chỉ đọc).

Theo `docs/runbook-demo-sach.md`: kỳ vọng `e2e users: 0 · eval rows: 0`.
Script này KHÔNG ghi gì, để chạy an toàn kể cả khi phiên khác đang làm việc.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "quan.db"


def _dem(cx: sqlite3.Connection, sql: str) -> int:
    try:
        return int(cx.execute(sql).fetchone()[0])
    except sqlite3.OperationalError:
        return 0  # bảng chưa tồn tại = không có rác


def main() -> int:
    if not DB.is_file():
        print(f"DB_MISSING {DB}")
        return 1
    cx = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        e2e = _dem(cx, "SELECT COUNT(*) FROM users WHERE username LIKE 'e2e_%'")
        evals = _dem(
            cx,
            "SELECT COUNT(*) FROM fb_review_queue WHERE external_thread_id LIKE 'fb_eval%'",
        )
        # Bản ghi mồ côi: session trỏ tới user không tồn tại.
        mo_coi = _dem(
            cx,
            "SELECT COUNT(*) FROM sessions s WHERE NOT EXISTS "
            "(SELECT 1 FROM users u WHERE u.username=s.username)",
        )
        print(f"e2e users: {e2e} · eval rows: {evals}")
        print(f"session mo coi: {mo_coi}")
        print(f"db_mtime={DB.stat().st_mtime_ns} db_size={DB.stat().st_size}")
    finally:
        cx.close()

    if e2e == 0 and evals == 0 and mo_coi == 0:
        print("CLEAN_CHECK=PASS (0 · 0)")
        return 0
    print("CLEAN_CHECK=FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
