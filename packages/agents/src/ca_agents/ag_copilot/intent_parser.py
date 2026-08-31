"""Intent Parser & Prompt Injection Guard for AG-COPILOT.

Classifies natural language input into 7 whitelisted intents with confidence scoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Intent enum string constants
SCHEDULE_SOLVE = "SCHEDULE_SOLVE"
APPROVE_SHIFT_SWAP = "APPROVE_SHIFT_SWAP"
GENERATE_DAILY_BRIEF = "GENERATE_DAILY_BRIEF"
QUERY_SOP = "QUERY_SOP"
ANALYZE_WASTE = "ANALYZE_WASTE"
CREATE_RULE_PROPOSAL = "CREATE_RULE_PROPOSAL"
INVENTORY_RESTOCK_CHECK = "INVENTORY_RESTOCK_CHECK"
OUT_OF_SCOPE = "OUT_OF_SCOPE"

# Patterns detecting attempts to bypass two-phase approval
_BYPASS_PATTERNS = [
    r"bỏ\s*qua\s*(bước\s*)?duyệt",
    r"ghi\s*luôn\s*(không\s*cần\s*(hỏi|duyệt|xác\s*nhận))?",
    r"tự\s*động\s*duyệt\s*hộ",
    r"xóa\s*hết\s*lịch.*ghi\s*đè\s*luôn",
    r"override\s*(auth|permission|approval|security)",
    r"ignore\s*(all\s*)?(previous\s*)?(instructions|rules)",
    r"từ\s*giờ\s*bạn\s*là\s*(admin|root|system|developer)",
]
_BYPASS_REGEX = re.compile("|".join(_BYPASS_PATTERNS), re.IGNORECASE)

# Intent matching keywords
_INTENT_KEYWORDS: list[tuple[str, list[str], float]] = [
    (
        SCHEDULE_SOLVE,
        ["xếp lịch", "xep lich", "chia ca", "xếp ca", "lên lịch", "chạy solver", "phân công ca", "tạo lịch"],
        0.92,
    ),
    (
        APPROVE_SHIFT_SWAP,
        ["đổi ca", "doi ca", "nhường ca", "nhận ca", "chuyển ca", "duyệt đổi ca", "yêu cầu đổi ca"],
        0.90,
    ),
    (
        GENERATE_DAILY_BRIEF,
        ["bản tin", "ban tin", "tin sáng", "tóm tắt đầu ngày", "tình hình hôm nay", "tình hình ca sáng"],
        0.95,
    ),
    (
        QUERY_SOP,
        ["quy trình", "quy trinh", "cẩm nang", "hướng dẫn", "mở quán", "đóng quán", "vệ sinh", "cách làm", "sop"],
        0.90,
    ),
    (
        ANALYZE_WASTE,
        ["hao hụt", "hao hut", "hàng hủy", "lãng phí", "sữa hỏng", "đổ bọt", "báo cáo hủy"],
        0.91,
    ),
    (
        CREATE_RULE_PROPOSAL,
        ["đề xuất luật", "luật mới", "cẩm nang sống", "tạo luật", "học luật", "thêm quy tắc"],
        0.90,
    ),
    (
        INVENTORY_RESTOCK_CHECK,
        ["kiểm kho", "tồn kho", "sắp hết hàng", "hết sữa", "đặt hàng", "nhập hàng", "ngưỡng tồn", "restock"],
        0.90,
    ),
]


@dataclass
class IntentParseResult:
    intent: str
    confidence: float
    params: dict[str, Any]
    clarification_needed: bool = False
    clarification_question: str | None = None
    security_flag: str | None = None


def parse_intent(message: str, context: dict[str, Any] | None = None) -> IntentParseResult:
    """Parse intent from user message with confidence rules and injection checks."""
    text = (message or "").strip()
    if not text:
        return IntentParseResult(
            intent=OUT_OF_SCOPE,
            confidence=0.0,
            params={},
            clarification_needed=False,
            security_flag="empty_message",
        )

    # 1. Security Check: Prompt Injection / Bypass Approval
    if _BYPASS_REGEX.search(text):
        return IntentParseResult(
            intent=OUT_OF_SCOPE,
            confidence=0.99,
            params={},
            clarification_needed=False,
            security_flag="bypass_approval_rejected",
        )

    # 2. Check for vague / ambiguous input (e.g. "Xếp lịch đi", "Xem giúp chị")
    lower = text.lower()
    if lower in ("xếp lịch", "xep lich", "xếp lịch đi", "lên lịch đi"):
        return IntentParseResult(
            intent=SCHEDULE_SOLVE,
            confidence=0.60,
            params={},
            clarification_needed=True,
            clarification_question="Dạ anh/chị muốn em xếp lịch cho tuần này hay tuần sau ạ?",
        )

    # 3. Match against Whitelisted Intents
    matched_intent = OUT_OF_SCOPE
    matched_conf = 0.3
    params: dict[str, Any] = {}

    for intent_name, keywords, base_conf in _INTENT_KEYWORDS:
        for kw in keywords:
            if kw in lower:
                matched_intent = intent_name
                matched_conf = base_conf
                break
        if matched_intent != OUT_OF_SCOPE:
            break

    # Extract common parameters
    if matched_intent == SCHEDULE_SOLVE:
        # Week detection
        if "tuần sau" in lower or "tuan sau" in lower:
            params["tuan"] = "2026-W36"
        else:
            params["tuan"] = "2026-W35"
        # Preference detection
        lan_match = re.search(r"ưu\s*tiên\s*(\w+)\s*ca\s*(\w+)", lower)
        if lan_match:
            params["uu_tien_nhan_su"] = {lan_match.group(1).title(): f"ca_{lan_match.group(2)}"}

    elif matched_intent == QUERY_SOP:
        params["cau_hoi"] = text

    elif matched_intent == GENERATE_DAILY_BRIEF:
        params["ngay"] = "2026-09-01"

    elif matched_intent == ANALYZE_WASTE:
        params["khoang_ngay"] = "hom_nay"

    elif matched_intent == INVENTORY_RESTOCK_CHECK:
        params["nguong_canh_bao"] = 10.0

    # 4. Confidence thresholds:
    # >= 0.75: regular
    # 0.5 <= conf < 0.75: clarification
    # < 0.5: OUT_OF_SCOPE
    if matched_conf >= 0.75:
        return IntentParseResult(
            intent=matched_intent,
            confidence=matched_conf,
            params=params,
            clarification_needed=False,
        )
    elif 0.5 <= matched_conf < 0.75:
        return IntentParseResult(
            intent=matched_intent,
            confidence=matched_conf,
            params=params,
            clarification_needed=True,
            clarification_question="Dạ anh/chị có thể nói rõ hơn thao tác cần hỗ trợ không ạ?",
        )
    else:
        return IntentParseResult(
            intent=OUT_OF_SCOPE,
            confidence=matched_conf,
            params={},
            clarification_needed=False,
        )
