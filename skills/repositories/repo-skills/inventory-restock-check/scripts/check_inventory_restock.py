#!/usr/bin/env python3
"""Script kiểm tra tồn kho và cảnh báo các mặt hàng chạm điểm đặt hàng lại (ROP).

Dùng cho AG-COPILOT và bộ phận quản lý kho của quán.
"""

from __future__ import annotations

import json
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Định mức mặc định
DEFAULT_THRESHOLDS: dict[str, dict[str, Any]] = {
    "cafe_hat_kg": {"min_safe": 5.0, "daily_burn": 2.0, "lead_days": 2},
    "sua_tuoi_hop": {"min_safe": 12.0, "daily_burn": 10.0, "lead_days": 1},
    "siro_dao_chai": {"min_safe": 2.0, "daily_burn": 0.5, "lead_days": 2},
}


def check_restock_needed(
    current_inventory: dict[str, float],
    thresholds: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Kiểm tra danh sách tồn kho so với điểm đặt hàng lại."""
    rules = thresholds or DEFAULT_THRESHOLDS
    items_to_restock: list[dict[str, Any]] = []

    for item, current_qty in current_inventory.items():
        rule = rules.get(item)
        if not rule:
            continue

        min_safe = rule.get("min_safe", 0.0)
        daily_burn = rule.get("daily_burn", 1.0)
        lead_days = rule.get("lead_days", 1)

        reorder_point = (daily_burn * lead_days) + min_safe
        days_left = round(current_qty / max(daily_burn, 0.1), 1)

        if current_qty <= reorder_point:
            items_to_restock.append({
                "item": item,
                "current_quantity": current_qty,
                "reorder_point": reorder_point,
                "estimated_days_left": days_left,
                "urgency": "CRITICAL" if current_qty <= min_safe else "WARNING",
            })

    return {
        "restock_needed": len(items_to_restock) > 0,
        "total_alerts": len(items_to_restock),
        "alerts": items_to_restock,
    }


def main() -> int:
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        inv = data.get("current_inventory", {})
        res = check_restock_needed(inv)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if not res["restock_needed"] else 0  # Tool chạy thành công

    # Dữ liệu self-test
    # Cà phê còn 3kg (< ROP 9kg), Sữa tươi còn 25 hộp (> ROP 22 hộp)
    test_inv = {"cafe_hat_kg": 3.0, "sua_tuoi_hop": 25.0}
    res = check_restock_needed(test_inv)

    if res["restock_needed"] is True and len(res["alerts"]) == 1:
        print(json.dumps({"smoke_test": "PASSED", "alerts": res["alerts"]}, ensure_ascii=False, indent=2))
        return 0
    else:
        print(json.dumps({"smoke_test": "FAILED"}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
