#!/usr/bin/env python3
"""Script đối soát tiền két và các khoản thu chi ca làm việc.

Dùng cho AG-HANDOVER và AG-COPILOT để bàn giao ca minh bạch, không sai sót.
"""

from __future__ import annotations

import json
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def reconcile_cash(
    opening_cash: int,
    pos_cash_sales: int,
    paid_outs: int,
    actual_cash_counted: int,
) -> dict[str, Any]:
    """Tính toán và so khớp tiền két thực tế vs sổ sách."""
    expected_cash = opening_cash + pos_cash_sales - paid_outs
    diff = actual_cash_counted - expected_cash

    if diff == 0:
        status = "MATCHED"
    elif diff < 0:
        status = "SHORTAGE"
    else:
        status = "SURPLUS"

    return {
        "matched": diff == 0,
        "status": status,
        "opening_cash": opening_cash,
        "pos_cash_sales": pos_cash_sales,
        "paid_outs": paid_outs,
        "expected_cash": expected_cash,
        "actual_cash_counted": actual_cash_counted,
        "discrepancy_amount": diff,
    }


def main() -> int:
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        res = reconcile_cash(
            opening_cash=int(data.get("opening_cash", 0)),
            pos_cash_sales=int(data.get("pos_cash_sales", 0)),
            paid_outs=int(data.get("paid_outs", 0)),
            actual_cash_counted=int(data.get("actual_cash_counted", 0)),
        )
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["matched"] else 1

    # Dữ liệu self-test
    # Đầu ca 1.000.000, bán tiền mặt 2.500.000, chi mua đá 100.000 -> Kỳ vọng: 3.400.000
    res = reconcile_cash(1000000, 2500000, 100000, 3400000)
    if res["matched"] is True and res["expected_cash"] == 3400000:
        print(json.dumps({"smoke_test": "PASSED", "result": res}, ensure_ascii=False, indent=2))
        return 0
    else:
        print(json.dumps({"smoke_test": "FAILED"}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
