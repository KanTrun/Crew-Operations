"""
AG-FBPAGE: Frontdesk Orchestrator for Customer Service Squad.

Orchestrates the Specialized Agent Squad:
- AG-FRONTDESK: Welcome, triage, operating hours, address, wifi.
- AG-BARISTA: Beverage consultation, taste profiling, natural pairings.
- AG-CONCIERGE: Complaint de-escalation (HEAR) and table reservations.
- AG-SUPERVISOR: Pre-flight safety gate against hallucinated promises and data leaks.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from ca_agents.ag_barista import consult_beverage
from ca_agents.ag_concierge import handle_complaint, handle_reservation
from ca_agents.ag_fbpage_memory import format_golden_cskh_prompt
from ca_agents.ag_supervisor import supervise_outgoing_response
from ca_agents.customer_memory import format_customer_greeting_context
from ca_agents.guardrails import check_input_guardrail
from ca_agents.llm import agent_mode, complete
from ca_agents.prompts.ag_fbpage.system_prompt import build_fb_system_prompt

CONFIDENCE_THRESHOLD_DEFAULT = 0.82

CUSTOMER_INTENTS = (
    "hoi_menu_gia",
    "hoi_gio_dia_chi",
    "hoi_khuyen_mai",
    "dat_ban",
    "khieu_nai_gop_y",
    "chao_hoi",
    "khac",
)

_COMPLAINT_WORDS = (
    "thất vọng",
    "that vong",
    "dở",
    "do ",
    "nguội",
    "nguoi",
    "chậm",
    "cham",
    "thái độ",
    "thai do",
    "phản ánh",
    "phan anh",
    "góp ý",
    "gop y",
    "khiếu nại",
    "khieu nai",
    "tệ",
    "te ",
    "đau bụng",
    "dau bung",
    "bực",
    "buc",
    "tẩy chay",
)

_BOOKING_WORDS = (
    "đặt bàn",
    "dat ban",
    "giữ chỗ",
    "giu cho",
    "bàn 10 người",
    "bàn mấy người",
    "reserve",
    "booking",
    "đặt trước",
    "dat truoc",
    "ghép bàn",
    "tiệc",
    "tiec",
)

_PROMO_WORDS = (
    "khuyến mãi",
    "khuyen mai",
    "ưu đãi",
    "uu dai",
    "giảm giá",
    "giam gia",
    "voucher",
    "combo",
    "discount",
    "sale",
    "chương trình",
    "chuong trinh",
)

_INFO_WORDS = (
    "mở cửa",
    "mo cua",
    "mấy giờ",
    "may gio",
    "đóng cửa",
    "dong cua",
    "ở đâu",
    "o dau",
    "địa chỉ",
    "dia chi",
    "vị trí",
    "vi tri",
    "tìm đường",
    "tim duong",
    "quán ở",
    "quan o",
    "wifi",
    "pass wifi",
)

_CONSULT_WORDS = (
    "tư vấn",
    "tu van",
    "món gì ngon",
    "mon gi ngon",
    "chưa biết chọn gì",
    "không uống được",
    "khong uong duoc",
    "say cà phê",
    "say ca phe",
    "ít ngọt",
    "it ngọt",
    "bán chạy",
    "signature",
    "gợi ý",
    "goi y",
)

_MENU_WORDS = (
    "menu",
    "thực đơn",
    "thuc don",
    "giá",
    "gia",
    "bao nhiêu",
    "bao nhieu",
    "món gì",
    "mon gi",
    "uống gì",
    "uong gi",
    "cà phê",
    "ca phe",
    "cafe",
    "bạc xỉu",
    "bac xiu",
    "trà đào",
    "tra dao",
    "sinh tố",
    "nước ép",
)

_GREETING_WORDS = (
    "chào",
    "chao",
    "hi",
    "hello",
    "alo",
    "quán ơi",
    "quan oi",
    "ad ơi",
    "ad oi",
    "shop ơi",
)


@dataclass(frozen=True)
class FBMessageInput:
    """Standardized Facebook message input."""

    psid: str
    text: str
    message_id: str
    timestamp: float
    sender_name: str | None = None


@dataclass(frozen=True)
class FBMessageOutput:
    """Result of processing a Facebook message."""

    action: str
    response: str | None
    intent: str
    confidence: float
    emotion: str = "neutral"
    suggested_reply: str | None = None
    delegated_agent: str = "AG-FRONTDESK"
    reason: str | None = None
    error: str | None = None


def _norm(text: str) -> str:
    return text.lower().strip()


def detect_customer_psychology(text: str) -> tuple[str, str, float]:
    """
    Analyze customer emotion and intent.
    Returns (emotion, intent, confidence).
    """
    t = _norm(text)

    # 1. Complaint (AG-CONCIERGE)
    if any(k in t for k in _COMPLAINT_WORDS):
        return "complaining", "khieu_nai_gop_y", 0.95

    # 2. Table Booking (AG-CONCIERGE)
    if any(k in t for k in _BOOKING_WORDS):
        return "booking", "dat_ban", 0.92

    # 3. Beverage Consultation (AG-BARISTA)
    if any(k in t for k in _CONSULT_WORDS):
        return "hesitant", "hoi_menu_gia", 0.90

    # 4. Promotions (AG-FRONTDESK)
    if any(k in t for k in _PROMO_WORDS):
        return "inquiring", "hoi_khuyen_mai", 0.88

    # 5. Operating Hours & Address (AG-FRONTDESK)
    if any(k in t for k in _INFO_WORDS):
        return "rushed" if len(t) < 25 else "inquiring", "hoi_gio_dia_chi", 0.90

    # 6. Menu & Pricing (AG-FRONTDESK / BARISTA)
    if any(k in t for k in _MENU_WORDS):
        return "inquiring", "hoi_menu_gia", 0.88

    # 7. Greeting (AG-FRONTDESK)
    if any(k in t for k in _GREETING_WORDS):
        return "friendly", "chao_hoi", 0.85

    return "neutral", "khac", 0.50


def build_human_response(
    intent: str,
    emotion: str,
    text: str,
    context: dict[str, Any] | None = None,
    customer_profile: dict[str, Any] | None = None,
    golden_examples: list[dict[str, Any]] | None = None,
) -> tuple[str, bool, str]:
    """
    Route task to specialized agent squad and generate response.
    Returns (reply_text, requires_human_approval, agent_name).
    """
    ctx = context or {}
    profile = ctx.get(
        "profile",
        {
            "ten_quan": "Nhịp Quán",
            "dia_chi": "123 Đường Cà Phê, P.5, Q.3, TP.HCM",
            "hotline": "0901234567",
            "gio_mo_cua": "07:00 - 22:30 hàng ngày",
            "wifi_ssid": "NhipQuan_Guest",
            "wifi_pass": "nhipquan2026",
        },
    )
    menu = ctx.get(
        "menu",
        [
            {"ten": "Cà phê đen", "gia_formatted": "25,000đ"},
            {"ten": "Cà phê sữa", "gia_formatted": "30,000đ"},
            {"ten": "Bạc xỉu", "gia_formatted": "32,000đ"},
            {"ten": "Trà đào", "gia_formatted": "35,000đ"},
        ],
    )
    promos = ctx.get(
        "promotions",
        [
            {
                "tieu_de": "Combo Sáng Tỉnh Táo",
                "chi_tiet": "Giảm 10% khi mua Cà phê sữa + Bánh mì trước 09:00",
            }
        ],
    )

    # Ưu tiên áp dụng bài học mẫu Quản lý đã dạy nếu trùng ý định
    if golden_examples and intent in ("hoi_gio_dia_chi", "hoi_khuyen_mai", "hoi_menu_gia"):
        for g in golden_examples:
            if g.get("intent") == intent and g.get("manager_reply"):
                return g["manager_reply"], False, "AG-FRONTDESK"

    # Case A: AG-CONCIERGE (Complaint)
    if intent == "khieu_nai_gop_y" or emotion == "complaining":
        ticket = handle_complaint(text)
        return ticket.suggested_reply, True, "AG-CONCIERGE"

    # Case B: AG-CONCIERGE (Booking)
    if intent == "dat_ban" or emotion == "booking":
        ticket = handle_reservation(text, profile.get("ten_quan", "Nhịp Quán"))
        return ticket.suggested_reply, True, "AG-CONCIERGE"

    # Case C: AG-BARISTA (Taste consultation)
    if emotion == "hesitant" or any(
        k in _norm(text) for k in ("tư vấn", "không uống được", "say cà phê", "ít ngọt")
    ):
        reply, _ = consult_beverage(text, menu)
        return reply, False, "AG-BARISTA"

    # Case D: AG-FRONTDESK (Greeting, Info, Menu list, Promo)
    if intent == "chao_hoi":
        cust_name = (customer_profile or {}).get("ten_khach")
        favs = (customer_profile or {}).get("favorite_drinks", [])
        if cust_name and (customer_profile or {}).get("is_vip_or_regular") and favs:
            return (
                f"Dạ Nhịp Quán chào anh/chị {cust_name} ạ! Hôm nay mình vẫn dùng món quen {favs[0]} đúng không ạ?",
                False,
                "AG-FRONTDESK",
            )
        if cust_name:
            return (
                f"Dạ Nhịp Quán chào anh/chị {cust_name} ạ! Em có thể gửi mình xem menu hoặc tư vấn đồ uống hôm nay nha!",
                False,
                "AG-FRONTDESK",
            )
        return (
            "Dạ Nhịp Quán xin chào mình ạ! Em có thể gửi mình xem menu hoặc tư vấn đồ uống hôm nay nha!",
            False,
            "AG-FRONTDESK",
        )

    if intent == "hoi_gio_dia_chi":
        # Chỉ ghép field có dữ liệu — không bao giờ để "None" lọt vào tin nhắn
        # khách (lỗ hổng văn bản khi profile thiếu field, review 2026-09-04).
        lines = [f"Dạ {profile.get('ten_quan') or 'quán'} mở cửa từ "
                 f"{profile.get('gio_mo_cua') or '07:00 - 22:30'} ạ."]
        if profile.get("dia_chi"):
            lines.append(f"📍 Địa chỉ: {profile['dia_chi']}")
        if profile.get("hotline"):
            lines.append(f"📞 Hotline: {profile['hotline']}")
        if profile.get("wifi_ssid"):
            wifi_line = f"📶 Wifi: {profile['wifi_ssid']}"
            if profile.get("wifi_pass"):
                wifi_line += f" (Mật khẩu: {profile['wifi_pass']})"
            lines.append(wifi_line)
        lines.append("Mời mình ghé quán trải nghiệm không gian và thưởng thức cà phê nhé ạ!")
        reply = "\n".join(lines)
        return reply, False, "AG-FRONTDESK"

    if intent == "hoi_menu_gia":
        items_str = "\n".join(
            [
                f"• {m['ten']}: {m.get('gia_formatted', str(m.get('gia', '')) + 'đ')}"
                for m in menu[:6]
            ]
        )
        reply = (
            f"Dạ em gửi mình menu nổi bật của quán nha:\n{items_str}\n\n"
            "Quán có đầy đủ cà phê truyền thống, trà trái cây và bánh ngọt. "
            "Mình muốn thử món nào cứ nhắn em tư vấn kỹ hơn nha!"
        )
        return reply, False, "AG-FRONTDESK"

    if intent == "hoi_khuyen_mai":
        if promos:
            promos_str = "\n".join([f"🎉 {p['tieu_de']}: {p['chi_tiet']}" for p in promos])
            reply = f"Dạ hôm nay quán đang có chương trình ưu đãi nè mình ơi:\n{promos_str}\n\nMời mình ghé quán nhận ưu đãi nha!"
        else:
            reply = "Dạ hiện tại quán đang phục vụ menu tiêu chuẩn với giá cực kỳ yêu thương mỗi ngày. Mời mình ghé quán thưởng thức nhé ạ!"
        return reply, False, "AG-FRONTDESK"

    reply = "Dạ em đã nhận được tin nhắn của mình rồi ạ. Mình đợi em một xíu em kiểm tra và phản hồi ngay nhé!"
    return reply, True, "AG-FRONTDESK"


async def process_fb_message(
    input_msg: FBMessageInput,
    *,
    confidence_threshold: float = CONFIDENCE_THRESHOLD_DEFAULT,
    auto_respond_enabled: bool = True,
    public_context: dict[str, Any] | None = None,
    customer_profile: dict[str, Any] | None = None,
    golden_examples: list[dict[str, Any]] | None = None,
) -> FBMessageOutput:
    """
    Process a customer message through the 4-Agent Squad Architecture.
    """
    # 1. Guardrail filter
    guard = check_input_guardrail(input_msg.text)
    if not guard.is_safe:
        return FBMessageOutput(
            action="auto_respond" if auto_respond_enabled else "queue_to_inbox",
            response="Dạ em không thể hỗ trợ yêu cầu này được ạ. Mình cần em tư vấn thêm món gì trong menu không ạ?",
            intent="blocked_injection",
            confidence=1.0,
            emotion="suspicious",
            delegated_agent="AG-SUPERVISOR",
            reason=f"Guardrail triggered: {guard.reason}",
        )

    # 2. Emotion & Intent Detection
    emotion, intent, confidence = detect_customer_psychology(guard.sanitized_text)

    # 3. Squad Routing (Frontdesk, Barista, Concierge)
    reply_text, requires_approval, agent_name = build_human_response(
        intent,
        emotion,
        guard.sanitized_text,
        public_context,
        customer_profile=customer_profile,
        golden_examples=golden_examples,
    )

    # 4. Live LLM execution if enabled
    if agent_mode() == "live" and not requires_approval and auto_respond_enabled:
        try:
            profile = (public_context or {}).get("profile", {})
            menu = (public_context or {}).get("menu", [])
            promos = (public_context or {}).get("promotions", [])
            ctx_summary = (
                f"Quán: {profile.get('ten_quan', 'Nhịp Quán')}, Địa chỉ: {profile.get('dia_chi', '')}, "
                f"Giờ mở cửa: {profile.get('gio_mo_cua', '')}, Hotline: {profile.get('hotline', '')}\n"
                f"Menu: {', '.join([m.get('ten', '') for m in menu])}\n"
                f"Khuyến mãi: {', '.join([p.get('tieu_de', '') for p in promos])}"
            )
            sys_prompt = build_fb_system_prompt(ctx_summary)

            extra_instructions = []
            if customer_profile:
                cust_ctx = format_customer_greeting_context(customer_profile)
                if cust_ctx:
                    extra_instructions.append(cust_ctx)
            if golden_examples:
                gold_ctx = format_golden_cskh_prompt(golden_examples)
                if gold_ctx:
                    extra_instructions.append(gold_ctx)

            if extra_instructions:
                sys_prompt += "\n\n" + "\n\n".join(extra_instructions)

            llm_res = await asyncio.wait_for(
                asyncio.to_thread(
                    complete,
                    system=sys_prompt,
                    user=guard.sanitized_text,
                    task="text",
                    json_mode=False,
                    timeout_s=3.0,
                ),
                timeout=3.5,
            )
            if llm_res.ok and llm_res.text.strip():
                reply_text = llm_res.text.strip()
        except Exception:
            pass

    # 5. AG-SUPERVISOR Pre-flight Safety Gate
    sup_check = supervise_outgoing_response(guard.sanitized_text, reply_text)
    if not sup_check.is_approved:
        reply_text = sup_check.sanitized_response
        requires_approval = True

    # 6. Action decision
    if not requires_approval and confidence >= confidence_threshold and auto_respond_enabled:
        return FBMessageOutput(
            action="auto_respond",
            response=reply_text,
            intent=intent,
            confidence=confidence,
            emotion=emotion,
            delegated_agent=agent_name,
            suggested_reply=reply_text,
            reason=f"Approved by AG-SUPERVISOR ({agent_name})",
        )
    else:
        return FBMessageOutput(
            action="queue_to_inbox",
            response=None,
            intent=intent,
            confidence=confidence,
            emotion=emotion,
            delegated_agent=agent_name,
            suggested_reply=reply_text,
            reason="Queued for manager approval",
        )


def parse_fb_webhook_message(entry: dict[str, Any]) -> FBMessageInput | None:
    """Parse incoming Facebook webhook entry to FBMessageInput."""
    try:
        messaging_list = entry.get("messaging") or []
        if not messaging_list:
            return None
        messaging = messaging_list[0]
        message = messaging.get("message", {})
        sender_id = (messaging.get("sender") or {}).get("id")

        if not sender_id or not message.get("text"):
            return None

        return FBMessageInput(
            psid=str(sender_id),
            text=str(message["text"]).strip(),
            message_id=str(message.get("mid", "")),
            timestamp=float(messaging.get("timestamp", 0)),
            sender_name=None,
        )
    except (KeyError, TypeError, IndexError, ValueError):
        return None


def classify_customer_intent(text: str) -> tuple[str, float]:
    """Helper alias for intent classification."""
    _, intent, conf = detect_customer_psychology(text)
    return intent, conf


def build_response_for_intent(
    intent: str, text: str, context: dict[str, Any] | None = None
) -> tuple[str, bool]:
    """Helper alias for response generation."""
    reply, req, _ = build_human_response(intent, "neutral", text, context)
    return reply, req


__all__ = [
    "FBMessageInput",
    "FBMessageOutput",
    "process_fb_message",
    "parse_fb_webhook_message",
    "detect_customer_psychology",
    "classify_customer_intent",
    "build_human_response",
    "build_response_for_intent",
    "CONFIDENCE_THRESHOLD_DEFAULT",
    "CUSTOMER_INTENTS",
]
