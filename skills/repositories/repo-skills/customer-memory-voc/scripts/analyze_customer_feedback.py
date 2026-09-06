#!/usr/bin/env python3
"""Script phân tích cảm xúc phản hồi của khách hàng và trích xuất thói quen khách quen.

Dùng cho AG-VOC và customer_memory.
"""

from __future__ import annotations

import json
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

POSITIVE_WORDS = {"ngon", "tuyệt", "thích", "nhanh", "dễ thương", "nhiệt tình", "sạch sẽ", "chill"}
NEGATIVE_WORDS = {"chán", "dở", "chậm", "lâu", "thái độ", "bẩn", "nhạt", "chua", "đắt", "ồn"}


def analyze_feedback(feedback_text: str, customer_phone: str = "") -> dict[str, Any]:
    """Phân tích nội dung đánh giá và trích xuất sở thích nếu có."""
    text_lower = feedback_text.lower()

    pos_score = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg_score = sum(1 for w in NEGATIVE_WORDS if w in text_lower)

    if neg_score > pos_score:
        sentiment = "NEGATIVE"
        urgent = neg_score >= 2
    elif pos_score > neg_score:
        sentiment = "POSITIVE"
        urgent = False
    else:
        sentiment = "NEUTRAL"
        urgent = False

    # Trích xuất sở thích đồ uống (nếu phát hiện)
    preferences: list[str] = []
    if "ít đường" in text_lower or "không đường" in text_lower:
        preferences.append("it_duong")
    if "ít đá" in text_lower or "không đá" in text_lower:
        preferences.append("it_da")
    if "sữa yến mạch" in text_lower or "oat" in text_lower:
        preferences.append("sua_yen_mach")

    return {
        "success": True,
        "customer_phone": customer_phone,
        "sentiment": sentiment,
        "pos_count": pos_score,
        "neg_count": neg_score,
        "urgent_attention_needed": urgent,
        "extracted_preferences": preferences,
    }


def main() -> int:
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        txt = data.get("feedback_text", "")
        phone = data.get("customer_phone", "")
        res = analyze_feedback(txt, phone)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    # Dữ liệu self-test
    res = analyze_feedback("Cà phê rất ngon và nhân viên dễ thương, lần sau nhớ làm ít đường nhé", "0901234567")
    if res["success"] is True and res["sentiment"] == "POSITIVE" and "it_duong" in res["extracted_preferences"]:
        print(json.dumps({"smoke_test": "PASSED", "result": res}, ensure_ascii=False, indent=2))
        return 0
    else:
        print(json.dumps({"smoke_test": "FAILED"}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
