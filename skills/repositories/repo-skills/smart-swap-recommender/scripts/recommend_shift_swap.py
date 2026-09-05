#!/usr/bin/env python3
"""Script đề xuất người thế ca tối ưu khi có nhân viên vắng mặt.

Dựa trên thuật toán smart_swap của hệ thống NHỊP QUÁN.
"""

from __future__ import annotations

import json
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def recommend_swap_candidates(
    shift_info: dict[str, Any],
    all_staff: list[dict[str, Any]],
) -> dict[str, Any]:
    """Tìm và xếp hạng ứng viên thế ca phù hợp nhất."""
    req_skill = shift_info.get("required_skill", "phuc_vu")
    shift_hours = shift_info.get("duration_hours", 4.0)
    absent_staff = shift_info.get("absent_staff", "")

    candidates: list[dict[str, Any]] = []

    for staff in all_staff:
        name = staff.get("name", "")
        if name == absent_staff:
            continue

        # 1. Kiểm tra lịch bận
        if staff.get("is_busy", False):
            continue

        # 2. Kiểm tra trần giờ tuần (C05)
        worked_hours = staff.get("worked_hours", 0.0)
        max_weekly_hours = staff.get("max_weekly_hours", 40.0)
        if worked_hours + shift_hours > max_weekly_hours:
            continue

        # 3. Tính điểm phù hợp
        score = 0
        reasons: list[str] = []

        skills = staff.get("skills", [])
        if req_skill in skills:
            score += 40
            reasons.append(f"Có kỹ năng {req_skill}")
        else:
            reasons.append(f"Chưa có kỹ năng chuyên sâu {req_skill}")

        # Ưu tiên người làm ít giờ hơn trong tuần để cân bằng thu nhập
        hour_ratio = max(0.0, 1.0 - (worked_hours / max(max_weekly_hours, 1.0)))
        fairness_score = int(hour_ratio * 30)
        score += fairness_score
        reasons.append(f"Điểm cân bằng giờ làm: +{fairness_score} (Đã làm {worked_hours}h)")

        # Điểm sẵn sàng nhận ca
        if staff.get("preferred_shift") == shift_info.get("shift_type"):
            score += 30
            reasons.append("Trùng ca mong muốn")

        candidates.append({
            "name": name,
            "score": score,
            "skills": skills,
            "worked_hours": worked_hours,
            "reasons": reasons,
        })

    # Xếp hạng giảm dần theo điểm số
    candidates.sort(key=lambda x: x["score"], reverse=True)

    return {
        "success": len(candidates) > 0,
        "shift_info": shift_info,
        "total_candidates_found": len(candidates),
        "best_candidate": candidates[0] if candidates else None,
        "all_ranked_candidates": candidates,
    }


def main() -> int:
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        shift = data.get("shift_info", {})
        staff_list = data.get("all_staff", [])
        res = recommend_swap_candidates(shift, staff_list)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["success"] else 1

    # Dữ liệu self-test
    shift = {"shift_type": "ca_sang", "required_skill": "barista", "duration_hours": 4.0, "absent_staff": "hung"}
    staff_list = [
        {"name": "hung", "skills": ["barista"], "worked_hours": 20.0, "is_busy": True},
        {"name": "lan", "skills": ["barista", "thu_ngan"], "worked_hours": 12.0, "is_busy": False, "preferred_shift": "ca_sang"},
        {"name": "minh", "skills": ["phuc_vu"], "worked_hours": 8.0, "is_busy": False},
    ]

    res = recommend_swap_candidates(shift, staff_list)
    if res["success"] and res["best_candidate"]["name"] == "lan":
        print(json.dumps({"smoke_test": "PASSED", "top_candidate": res["best_candidate"]}, ensure_ascii=False, indent=2))
        return 0
    else:
        print(json.dumps({"smoke_test": "FAILED"}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
