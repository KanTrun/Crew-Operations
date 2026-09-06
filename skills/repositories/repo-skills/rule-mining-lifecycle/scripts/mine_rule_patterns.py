#!/usr/bin/env python3
"""Script phân tích lịch sử chỉnh sửa và tìm các mẫu lặp lại >= 3 lần để tự sinh luật cẩm nang.

Dựa trên packages/playbook (sua.py, vong_doi.py) và AG-RULE.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PATTERN_THRESHOLD = 3  # Tối thiểu 3 lần lặp lại


def mine_edit_patterns(edit_logs: list[dict[str, Any]]) -> dict[str, Any]:
    """Gom cụm các lý do sửa lịch và phát hiện mẫu lặp."""
    pattern_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for entry in edit_logs:
        target = entry.get("target_staff", "")
        reason_code = entry.get("reason_code", "other")
        day = entry.get("day", "")
        key = f"{target}:{reason_code}:{day}"
        pattern_groups[key].append(entry)

    mined_rules: list[dict[str, Any]] = []

    for key, occurrences in pattern_groups.items():
        count = len(occurrences)
        if count >= PATTERN_THRESHOLD:
            target, reason_code, day = key.split(":")
            mined_rules.append({
                "pattern_key": key,
                "occurrences_count": count,
                "target_staff": target,
                "reason_code": reason_code,
                "day": day,
                "proposed_rule": f"Không xếp nhân viên '{target}' vào ca ngày '{day}' do lý do '{reason_code}' (đã lặp lại {count} lần).",
                "status": "ready_for_trial",
            })

    return {
        "success": True,
        "total_edits_analyzed": len(edit_logs),
        "mined_rules_count": len(mined_rules),
        "rules_proposed": mined_rules,
    }


def main() -> int:
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        logs = data.get("edit_logs", [])
        res = mine_edit_patterns(logs)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    # Dữ liệu self-test
    # Lan xin đổi ca sáng T4 đúng 3 lần
    sample_logs = [
        {"target_staff": "lan", "reason_code": "trung_lich_hoc", "day": "T4"},
        {"target_staff": "lan", "reason_code": "trung_lich_hoc", "day": "T4"},
        {"target_staff": "lan", "reason_code": "trung_lich_hoc", "day": "T4"},
        {"target_staff": "hung", "reason_code": "ban_viec_rieng", "day": "T2"},
    ]

    res = mine_edit_patterns(sample_logs)
    if res["success"] is True and res["mined_rules_count"] == 1:
        print(json.dumps({"smoke_test": "PASSED", "mined_rule": res["rules_proposed"][0]}, ensure_ascii=False, indent=2))
        return 0
    else:
        print(json.dumps({"smoke_test": "FAILED"}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
