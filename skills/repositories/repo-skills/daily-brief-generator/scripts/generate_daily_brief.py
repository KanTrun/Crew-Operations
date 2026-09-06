#!/usr/bin/env python3
"""Script tổng hợp và định dạng bản tin giao ban ca làm việc.

Dùng cho AG-BRIEF và AG-COPILOT để gửi bản tin tự động đầu ca.
"""

from __future__ import annotations

import json
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def generate_brief(
    date_str: str,
    shift_name: str,
    staff_roster: list[dict[str, str]],
    target_revenue: int,
    upsell_item: str,
    pending_notes: list[str],
) -> dict[str, Any]:
    """Tạo bản tin giao ban ca chuẩn."""
    staff_lines = [f"- {s.get('role', 'Nhân viên')}: {s.get('name', 'Chưa rõ')}" for s in staff_roster]
    notes_lines = [f"- {note}" for note in pending_notes] if pending_notes else ["- Không có việc tồn đọng."]

    formatted_text = f"""☀️ BẢN TIN ĐẦU CA — {date_str} — {shift_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 NHÂN SỰ TRỰC CA:
{chr(10).join(staff_lines)}

🎯 MỤC TIÊU CA:
- Doanh thu mục tiêu: {target_revenue:,} VNĐ
- Món trọng tâm: {upsell_item}

⚠️ LƯU Ý & VIỆC TREO:
{chr(10).join(notes_lines)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    return {
        "success": True,
        "date": date_str,
        "shift": shift_name,
        "formatted_text": formatted_text,
        "total_staff": len(staff_roster),
    }


def main() -> int:
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        res = generate_brief(
            date_str=data.get("date", "Hôm nay"),
            shift_name=data.get("shift", "Ca Sáng"),
            staff_roster=data.get("staff", []),
            target_revenue=data.get("target_revenue", 3000000),
            upsell_item=data.get("upsell_item", "Cà phê muối"),
            pending_notes=data.get("notes", []),
        )
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    # Dữ liệu self-test
    res = generate_brief(
        date_str="2026-09-06",
        shift_name="Ca Sáng (07:00 - 12:00)",
        staff_roster=[
            {"role": "Kíp trưởng", "name": "Hùng"},
            {"role": "Barista", "name": "Lan"},
        ],
        target_revenue=2500000,
        upsell_item="Trà Đào Cam Sả",
        pending_notes=["Tủ lạnh 2 hơi kêu nhẹ, ca sau kiểm tra"],
    )

    if res["success"] is True and "Hùng" in res["formatted_text"]:
        print(json.dumps({"smoke_test": "PASSED", "preview": res["formatted_text"]}, ensure_ascii=False, indent=2))
        return 0
    else:
        print(json.dumps({"smoke_test": "FAILED"}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
