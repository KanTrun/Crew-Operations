#!/usr/bin/env python3
"""Script kiểm tra việc hoàn thành checklist quy trình vận hành (SOP).

Dùng để xác minh nhân viên đã thực hiện đủ các bước mở ca/đóng ca hay xử lý sự cố chưa.
"""

from __future__ import annotations

import json
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def verify_checklist(required_steps: list[str], completed_steps: list[str]) -> dict[str, Any]:
    req_set = set(required_steps)
    comp_set = set(completed_steps)

    missing = [s for s in required_steps if s not in comp_set]
    extra = [s for s in completed_steps if s not in req_set]

    return {
        "completed": len(missing) == 0,
        "completion_rate": round(len(comp_set.intersection(req_set)) / max(len(required_steps), 1), 2),
        "missing_steps": missing,
        "completed_steps": [s for s in required_steps if s in comp_set],
        "extra_steps": extra,
    }


def main() -> int:
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        req = data.get("required_steps", [])
        comp = data.get("completed_steps", [])
        result = verify_checklist(req, comp)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["completed"] else 1

    # Dữ liệu self-test khi chạy không tham số
    req = ["b1_mo_cua", "b2_khoi_dong_may"]
    comp_full = ["b1_mo_cua", "b2_khoi_dong_may"]
    res_full = verify_checklist(req, comp_full)

    comp_partial = ["b1_mo_cua"]
    res_partial = verify_checklist(req, comp_partial)

    # Smoke test xác minh thuật toán hoạt động chính xác
    if res_full["completed"] is True and res_partial["completed"] is False:
        print(json.dumps({"smoke_test": "PASSED", "verified_samples": 2}, ensure_ascii=False, indent=2))
        return 0
    else:
        print(json.dumps({"smoke_test": "FAILED"}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())

