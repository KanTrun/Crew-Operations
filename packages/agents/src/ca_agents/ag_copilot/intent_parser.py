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
SEND_MAIL = "SEND_MAIL"
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
    (
        SEND_MAIL,
        [
            "gửi mail",
            "gui mail",
            "gửi email",
            "gửi gmail",
            "email cho",
            "mail cho",
            "nhắn qua email",
            "gửi thông báo qua email",
            "soạn mail",
            "soan mail",
            "soạn email",
            "soan email",
            "soạn gmail",
            "soan gmail",
            "viết mail",
            "viet mail",
            "viết email",
            "viet email",
            "viết gmail",
            "viet gmail",
            "nhờ soạn mail",
            "nhờ viết mail",
        ],
        0.92,
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


def _iso_week(d: Any) -> str:
    """Trả về ISO week dạng 'YYYY-Wnn'. Không hardcode."""
    from datetime import date

    if not isinstance(d, date):
        d = date.today()
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _add_week(d: Any, n: int = 1) -> Any:
    """Cộng n tuần (giữ nguyên kiểu date)."""
    from datetime import date, timedelta

    if not isinstance(d, date):
        d = date.today()
    return d + timedelta(weeks=n)


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
        # Week detection (ISO week thực tế — không hardcode).
        from datetime import date

        tuan = _iso_week(date.today())
        if "tuần sau" in lower or "tuan sau" in lower:
            params["tuan"] = _iso_week(_add_week(date.today(), 1))
        elif "tuần này" in lower or "tuan nay" in lower:
            params["tuan"] = tuan
        else:
            # Mặc định tuần sau (nhu cầu lập lịch phổ biến).
            params["tuan"] = _iso_week(_add_week(date.today(), 1))
        # Preference detection
        lan_match = re.search(r"ưu\s*tiên\s*(\w+)\s*ca\s*(\w+)", lower)
        if lan_match:
            params["uu_tien_nhan_su"] = {lan_match.group(1).title(): f"ca_{lan_match.group(2)}"}

    elif matched_intent == QUERY_SOP:
        params["cau_hoi"] = text

    elif matched_intent == GENERATE_DAILY_BRIEF:
        from datetime import date

        params["ngay"] = date.today().isoformat()

    elif matched_intent == ANALYZE_WASTE:
        params["khoang_ngay"] = "hom_nay"

    elif matched_intent == INVENTORY_RESTOCK_CHECK:
        params["nguong_canh_bao"] = 10.0

    elif matched_intent == SEND_MAIL:
        t_low = text.lower()
        # Direct email extraction
        email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
        found_emails = email_pattern.findall(text)

        # Trích xuất tên nhân viên thường gặp
        staff_map = {
            "minh": "nv_03",
            "lan": "nv_01",
            "hùng": "nv_02",
            "hung": "nv_02",
        }
        to_nv_ids: list[str] = []
        recip_names: list[str] = []
        for name, nv_id in staff_map.items():
            if re.search(r"\b" + re.escape(name) + r"\b", t_low):
                if nv_id not in to_nv_ids:
                    to_nv_ids.append(nv_id)
                    recip_names.append(name.capitalize())

        # Trích xuất mã nv_XX nếu có
        for m in re.findall(r"\bnv_\d+\b", t_low):
            if m not in to_nv_ids:
                to_nv_ids.append(m)
                recip_names.append(m.upper())

        params["raw_request"] = text
        params["to_nv_ids"] = to_nv_ids
        params["direct_emails"] = found_emails
        params["recipient_names"] = recip_names
        params["subject"] = text if len(text) <= 120 else text[:120]
        params["body"] = text

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
