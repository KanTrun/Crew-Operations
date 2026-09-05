#!/usr/bin/env python3
"""Script kiểm tra định lượng công thức pha chế và tính toán hao hụt nguyên liệu.

Dùng cho AG-BARISTA và AG-WASTE để đối soát nguyên vật liệu ca làm việc.
"""

from __future__ import annotations

import json
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Định mức chuẩn cho từng món
RECIPES: dict[str, dict[str, float]] = {
    "espresso": {"coffee_gram": 18.0},
    "latte": {"coffee_gram": 18.0, "milk_ml": 150.0},
    "tra_dao": {"tea_gram": 10.0, "syrup_ml": 20.0},
}

THRESHOLD_MAX_PERCENT = 5.0  # Tối đa 5% hao hụt cho phép


def audit_waste(sold_items: dict[str, int], actual_used: dict[str, float]) -> dict[str, Any]:
    """Tính lượng nguyên liệu lý thuyết và so khớp với thực tế tiêu hao."""
    theoretical: dict[str, float] = {}

    for item, qty in sold_items.items():
        recipe = RECIPES.get(item, {})
        for ingredient, amount in recipe.items():
            theoretical[ingredient] = theoretical.get(ingredient, 0.0) + (amount * qty)

    flagged_items: list[dict[str, Any]] = []
    total_waste_rate = 0.0
    checked_count = 0

    for ing, theo_amt in theoretical.items():
        act_amt = actual_used.get(ing, theo_amt)
        diff = act_amt - theo_amt
        rate = round((diff / theo_amt) * 100.0, 2) if theo_amt > 0 else 0.0
        total_waste_rate += max(0.0, rate)
        checked_count += 1

        is_exceeded = rate > THRESHOLD_MAX_PERCENT
        if is_exceeded:
            flagged_items.append({
                "ingredient": ing,
                "theoretical": theo_amt,
                "actual": act_amt,
                "waste_rate_percent": rate,
                "threshold_percent": THRESHOLD_MAX_PERCENT,
            })

    avg_waste = round(total_waste_rate / max(1, checked_count), 2)

    return {
        "compliant": len(flagged_items) == 0,
        "average_waste_percent": avg_waste,
        "flagged_ingredients": flagged_items,
        "theoretical_usage": theoretical,
    }


def main() -> int:
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        sold = data.get("sold_items", {})
        actual = data.get("actual_used", {})
        res = audit_waste(sold, actual)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["compliant"] else 1

    # Dữ liệu self-test
    sold = {"latte": 10, "espresso": 20}  # Lý thuyết: 540g cafe, 1500ml sữa
    actual_normal = {"coffee_gram": 550.0, "milk_ml": 1520.0}  # ~1.8% hao hụt -> Đạt
    res = audit_waste(sold, actual_normal)

    if res["compliant"] is True and res["average_waste_percent"] < 5.0:
        print(json.dumps({"smoke_test": "PASSED", "details": res}, ensure_ascii=False, indent=2))
        return 0
    else:
        print(json.dumps({"smoke_test": "FAILED"}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
