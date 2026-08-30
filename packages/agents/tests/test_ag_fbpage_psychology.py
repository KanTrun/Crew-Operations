"""Unit tests for AG-FBPAGE Human Persona and Psychological Profiling."""

import asyncio

from ca_agents.ag_fbpage import (
    FBMessageInput,
    build_human_response,
    detect_customer_psychology,
    process_fb_message,
)


def test_detect_customer_psychology_states():
    # 1. Complaining / Angry
    emotion, intent, conf = detect_customer_psychology(
        "Hôm nay nhân viên phục vụ thái độ tệ quá, nước thì dở"
    )
    assert emotion == "complaining"
    assert intent == "khieu_nai_gop_y"
    assert conf >= 0.90

    # 2. Hesitant / Needs consultation
    emotion, intent, conf = detect_customer_psychology(
        "Mình không uống được cà phê đậm, có món gì thanh mát ít ngọt không?"
    )
    assert emotion == "hesitant"
    assert intent == "hoi_menu_gia"

    # 3. Booking
    emotion, intent, conf = detect_customer_psychology(
        "Tối nay quán có bàn 10 người lúc 19h30 không?"
    )
    assert emotion == "booking"
    assert intent == "dat_ban"

    # 4. Rushed
    emotion, intent, conf = detect_customer_psychology("ở đâu")
    assert emotion == "rushed"
    assert intent == "hoi_gio_dia_chi"


def test_human_persona_anti_robot_rules():
    # Check responses for robotic terms vs natural Vietnamese service tone
    robotic_phrases = [
        "tôi là mô hình",
        "tôi là ai",
        "trợ lý ảo",
        "theo cơ sở dữ liệu",
        "tôi có thể giúp gì cho bạn hôm nay",
    ]

    test_queries = [
        ("hoi_gio_dia_chi", "neutral", "quán mở cửa tới mấy giờ?"),
        ("hoi_menu_gia", "hesitant", "tư vấn nước giúp mình"),
        ("khieu_nai_gop_y", "complaining", "nước dở quá thất vọng"),
        ("dat_ban", "booking", "mình muốn đặt bàn 6 người"),
        ("chao_hoi", "friendly", "chào quán nha"),
    ]

    for intent, emotion, text in test_queries:
        reply, requires_approval, agent_name = build_human_response(intent, emotion, text)
        reply_lower = reply.lower()

        # Must not contain robotic AI phrases
        for robot_term in robotic_phrases:
            assert robot_term not in reply_lower, (
                f"Robotic phrase found in response: '{robot_term}' in '{reply}'"
            )

        # Must sound natural and polite (contains 'dạ' or 'ạ')
        assert "dạ" in reply_lower or "ạ" in reply_lower, f"Polite particle missing in: '{reply}'"


def test_complaint_de_escalation_flow():
    msg = FBMessageInput(
        psid="cust_complaint_01",
        text="Trà đào hôm nay bị chua và nhân viên phục vụ rất chậm chạp!",
        message_id="m_comp_1",
        timestamp=1700000000,
    )
    out = asyncio.run(process_fb_message(msg))
    assert out.action == "queue_to_inbox"
    assert out.intent == "khieu_nai_gop_y"
    assert out.emotion == "complaining"
    # Sincere apology and asks for contact to resolve directly
    suggested = (out.suggested_reply or "").lower()
    assert "xin lỗi" in suggested
    assert "quản lý" in suggested


def test_beverage_consultation_flow():
    msg = FBMessageInput(
        psid="cust_hesitant_01",
        text="Mình bị say cà phê, quán có món gì ngon dễ uống không bạn?",
        message_id="m_cons_1",
        timestamp=1700000000,
    )
    out = asyncio.run(process_fb_message(msg, auto_respond_enabled=True))
    assert out.action == "auto_respond"
    assert out.intent == "hoi_menu_gia"
    resp = (out.response or "").lower()
    assert "trà đào" in resp or "bạc xỉu" in resp
