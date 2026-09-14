"""Rename staff display names in DB (drop role suffixes) and reschedule 1 week.

Chạy: python scripts/rename_and_reschedule.py
- Bước 1: UPDATE users.display_name bỏ phần chức vụ (giữ nguyên username/role/nv_id).
- Bước 2: Chạy solver CP-SAT xếp lại lịch 1 tuần với TOÀN BỘ nhân viên (users thật).
- Bước 3: In ra vị trí database để xem trực tiếp.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (
    ROOT / "apps" / "api" / "src",
    ROOT / "packages" / "solver" / "src",
    ROOT / "packages" / "gates" / "src",
):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Tên mới: chỉ tên riêng, không chức vụ
NEW_NAMES: dict[str, str] = {
    "nv_01": "Lan Nguyễn",
    "nv_02": "Hùng Trần",
    "nv_12": "Nam Lý",
    "nv_03": "Minh Phạm",
    "nv_06": "Chi Vũ",
    "nv_07": "Dũng Đặng",
    "nv_04": "An Lê",
    "nv_05": "Bảo Hoàng",
    "nv_10": "Yến Kiều",
    "nv_08": "Thảo Dương",
    "nv_09": "Quân Lương",
    "nv_11": "Linh Ngô",
    "nv_13": "Mỹ Tạ",
    "nv_14": "Khoa Đỗ",
    "nv_15": "Oanh Phan",
    "nv_16": "Phúc Trịnh",
    "nv_17": "Sơn Hà",
    "nv_18": "Rosa Võ",
    "nv_19": "Uyên Cao",
}


def rename_users() -> int:
    from ca_api.persist import _conn, init_db

    init_db()
    n = 0
    with _conn() as cx:
        for nv_id, ten in NEW_NAMES.items():
            cur = cx.execute(
                "UPDATE users SET display_name=? WHERE nv_id=?", (ten, nv_id)
            )
            n += cur.rowcount
    return n


def reschedule_week() -> dict:
    from ca_api.interfaces.http.sprint45 import _run_solver

    return _run_solver()


def main() -> int:
    print("=" * 60)
    print("1) Đổi tên nhân viên (bỏ chức vụ trong tên)")
    n = rename_users()
    print(f"   Đã cập nhật {n}/{len(NEW_NAMES)} display_name")

    print("=" * 60)
    print("2) Xếp lại lịch 1 tuần với toàn bộ nhân viên (solver CP-SAT)")
    res = reschedule_week()
    print(f"   status={res.get('status')} ok={res.get('ok')} violations={res.get('violations')}")
    for x in res.get("danh_sach_xung_dot", []):
        print(f"   - {x}")

    print("=" * 60)
    print("3) Vị trí database (xem trực tiếp):")
    from ca_api.persist import db_path

    print(f"   {db_path().resolve()}")
    return 0


if __name__ == "__main__":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
