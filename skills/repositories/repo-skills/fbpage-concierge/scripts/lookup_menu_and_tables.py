#!/usr/bin/env python3
"""Script tra cứu giá menu và kiểm tra tình trạng bàn trống cho khách.

Dùng cho AG-FBPAGE và AG-CONCIERGE.
"""

from __future__ import annotations

import json
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MENU_ITEMS: dict[str, dict[str, Any]] = {
    "ca_phe_den": {"name": "Cà phê đen đá", "price": 25000, "category": "coffee"},
    "ca_phe_sua": {"name": "Cà phê sữa đá", "price": 29000, "category": "coffee"},
    "latte": {"name": "Latte nóng/đá", "price": 45000, "category": "coffee"},
    "tra_dao": {"name": "Trà đào cam sả", "price": 39000, "category": "tea"},
    "croissant": {"name": "Bánh sừng bò bơ Pháp", "price": 35000, "category": "bakery"},
}

AVAILABLE_TABLES: list[dict[str, Any]] = [
    {"table_id": "T01", "capacity": 2, "is_booked": False},
    {"table_id": "T02", "capacity": 4, "is_booked": False},
    {"table_id": "T03", "capacity": 8, "is_booked": True},
]


def lookup_info(query_type: str, keyword: str = "", party_size: int = 2) -> dict[str, Any]:
    """Tra cứu món hoặc tìm bàn trống."""
    if query_type == "menu":
        matched = []
        kw_lower = keyword.lower()
        for k, v in MENU_ITEMS.items():
            if kw_lower in k or kw_lower in v["name"].lower():
                matched.append(v)
        return {"type": "menu", "matches": matched if matched else list(MENU_ITEMS.values())}

    elif query_type == "tables":
        suitable = [t for t in AVAILABLE_TABLES if not t["is_booked"] and t["capacity"] >= party_size]
        return {
            "type": "tables",
            "requested_party_size": party_size,
            "available_count": len(suitable),
            "suitable_tables": suitable,
        }

    return {"error": f"Loại truy vấn '{query_type}' không hỗ trợ"}


def main() -> int:
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        q_type = data.get("query_type", "menu")
        kw = data.get("keyword", "")
        size = data.get("party_size", 2)
        res = lookup_info(q_type, kw, size)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    # Dữ liệu self-test
    res_menu = lookup_info("menu", "trà đào")
    res_table = lookup_info("tables", party_size=4)

    if len(res_menu.get("matches", [])) == 1 and res_table.get("available_count", 0) >= 1:
        print(json.dumps({"smoke_test": "PASSED", "sample": res_menu}, ensure_ascii=False, indent=2))
        return 0
    else:
        print(json.dumps({"smoke_test": "FAILED"}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
