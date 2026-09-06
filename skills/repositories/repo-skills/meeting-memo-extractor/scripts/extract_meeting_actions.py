#!/usr/bin/env python3
"""Script bóc tách biên bản họp ca thành danh sách việc cần làm (Action Items).

Dùng cho AG-MEETING và AG-COPILOT.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def extract_action_items(meeting_raw_text: str) -> dict[str, Any]:
    """Phân tích đoạn văn bản họp và trích xuất các việc được giao."""
    lines = meeting_raw_text.splitlines()
    action_items: list[dict[str, Any]] = []

    for line in lines:
        line_str = line.strip()
        # Tìm các mẫu gạch đầu dòng hoặc có từ khóa phân công / công việc
        if line_str.startswith(("-", "*", "•")) or re.search(r"(giao|phụ trách|hạn chót|trách nhiệm|trước|deadline|kiểm tra)", line_str, re.IGNORECASE):
            parts = line_str.lstrip("-*•0123456789. ").split(":")
            if len(parts) >= 2:
                assignee = parts[0].strip()
                task = parts[1].strip()
            else:
                assignee = "Chưa chỉ định"
                task = parts[0].strip()

            if task:
                action_items.append({
                    "task": task,
                    "assignee": assignee,
                    "raw_line": line_str,
                    "priority": "HIGH" if any(w in line_str.lower() for w in ("khẩn", "ngay", "hôm nay")) else "NORMAL",
                })


    return {
        "success": True,
        "total_actions": len(action_items),
        "actions": action_items,
    }


def main() -> int:
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        txt = data.get("meeting_text", "")
        res = extract_action_items(txt)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    # Dữ liệu self-test
    sample = """Biên bản họp tuần 35:
- Hùng: Kiểm tra vệ sinh máy xay cà phê trước 18h
- Lan: Phụ trách kiểm kê siro đào và sữa tươi khẩn cấp
- Quán cần đẩy mạnh bán trà vải trong tuần này"""

    res = extract_action_items(sample)
    if res["success"] is True and res["total_actions"] >= 2:
        print(json.dumps({"smoke_test": "PASSED", "extracted": res["actions"]}, ensure_ascii=False, indent=2))
        return 0
    else:
        print(json.dumps({"smoke_test": "FAILED"}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
