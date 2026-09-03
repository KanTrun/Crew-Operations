"""Unit tests for Self-Improving CSKH Agent:

1. Golden Memory Feedback Loop (Sửa là Học)
2. Customer Profile & VIP Regulars
3. Nightly Reflection & Playbook Proposals
"""

from __future__ import annotations

from ca_agents.ag_fbpage import FBMessageInput, build_human_response, process_fb_message
from ca_agents.ag_fbpage_memory import (
    extract_cskh_golden_pair,
    format_golden_cskh_prompt,
)
from ca_agents.ag_supervisor import run_nightly_cskh_reflection
from ca_agents.customer_memory import (
    extract_customer_preferences,
    format_customer_greeting_context,
    merge_customer_profile,
)


def test_extract_cskh_golden_pair() -> None:
    cust = "Quán có chỗ đậu ô tô không bạn?"
    ai_draft = "Dạ quán có chỗ để xe máy ạ."
    mgr_reply = "Dạ em chào anh, quán có bãi đỗ ô tô cách quán 50m tại số 12 đường ABC, có bảo vệ trông coi chu đáo ạ!"

    pair = extract_cskh_golden_pair(cust, ai_draft, mgr_reply, intent="hoi_gio_dia_chi", customer_name="Anh Tuấn")
    assert pair is not None
    assert pair["customer_msg"] == cust
    assert pair["manager_reply"] == mgr_reply
    assert "xung_ho_than_mat" in pair["improvement_highlights"]

    prompt_str = format_golden_cskh_prompt([pair])
    assert "CÁC CÂU TRẢ LỜI MẪU CHUẨN MỰC TỪ QUẢN LÝ" in prompt_str
    assert "bãi đỗ ô tô" in prompt_str.lower()


def test_customer_preferences_extraction_and_merge() -> None:
    msgs = [
        "Chào quán, mình tên Tuấn nhé.",
        "Cho mình một bạc xỉu ít ngọt và một trà đào ít đá nha.",
        "Lưu ý mình bị dị ứng sữa bò ạ.",
    ]
    extracted = extract_customer_preferences(msgs)
    assert extracted["ten_khach"] == "Tuấn"
    assert "Bạc Xỉu" in extracted["favorite_drinks"]
    assert "Trà Đào" in extracted["favorite_drinks"]
    assert "Ít Ngọt" in extracted["special_notes"]
    assert "Dị Ứng Sữa" in extracted["special_notes"]

    profile = merge_customer_profile(None, extracted)
    assert profile["ten_khach"] == "Tuấn"
    assert profile["visit_count"] == 1
    assert not profile["is_vip_or_regular"]

    # Giả lập khách quay lại 2 lần nữa
    profile = merge_customer_profile(profile, {"favorite_drinks": ["Cà Phê Muối"]})
    profile = merge_customer_profile(profile, {})
    assert profile["visit_count"] == 3
    assert profile["is_vip_or_regular"] is True

    greeting_ctx = format_customer_greeting_context(profile)
    assert "Tuấn" in greeting_ctx
    assert "Bạc Xỉu" in greeting_ctx


def test_fbpage_personalized_greeting_and_golden_reply() -> None:
    vip_profile = {
        "ten_khach": "Tuấn",
        "visit_count": 4,
        "is_vip_or_regular": True,
        "favorite_drinks": ["Bạc xỉu"],
    }
    reply, req_app, agent = build_human_response(
        intent="chao_hoi",
        emotion="friendly",
        text="Alo quán ơi",
        customer_profile=vip_profile,
    )
    assert "Tuấn" in reply
    assert "Bạc xỉu" in reply
    assert not req_app

    # Test golden example adoption
    golden = [{
        "intent": "hoi_gio_dia_chi",
        "manager_reply": "Dạ quán mở cửa 6h30 đến 23h, bãi xe ô tô miễn phí ngay trước quán ạ!",
    }]
    reply_gold, _, _ = build_human_response(
        intent="hoi_gio_dia_chi",
        emotion="inquiring",
        text="Quán mở mấy giờ",
        golden_examples=golden,
    )
    assert "6h30 đến 23h" in reply_gold


def test_process_fb_message_with_customer_profile() -> None:
    import asyncio

    inp = FBMessageInput(
        psid="psid_123",
        text="Quán ơi",
        message_id="mid_001",
        timestamp=1000.0,
    )
    profile = {"ten_khach": "Lan", "visit_count": 1, "is_vip_or_regular": False}
    out = asyncio.run(process_fb_message(inp, customer_profile=profile))
    assert "Lan" in out.response


def test_nightly_cskh_reflection() -> None:
    threads = [
        {
            "id": "t1",
            "intent": "khieu_nai_gop_y",
            "messages": [{"from_customer": True, "text": "Cà phê hôm nay nguội ngắt và quá ngọt, thất vọng ghê!"}],
            "suggested_reply": "Dạ em thành thật xin lỗi anh/chị. Anh/chị cho em xin số điện thoại để Quản lý gọi lại hỗ trợ ngay nhé ạ!",
            "pending_approval": True,
        },
        {
            "id": "t2",
            "intent": "khac",
            "messages": [{"from_customer": True, "text": "Quán có bán hạt cà phê Robusta đóng gói mang về không?"}],
            "suggested_reply": "Dạ em chưa có thông tin này, để em kiểm tra lại ạ.",
            "pending_approval": True,
        },
        {
            "id": "t3",
            "intent": "hoi_menu_gia",
            "messages": [{"from_customer": True, "text": "Cho mình xem menu nha, cảm ơn quán!"}],
            "suggested_reply": "Dạ em gửi menu ạ.",
            "pending_approval": False,
        },
    ]

    report = run_nightly_cskh_reflection(threads, store_id="quan_01")
    assert report["total_conversations"] == 3
    assert report["csat_score"] > 5.0
    assert report["hear_compliance_rate"] == 100.0  # t1 has xin lỗi, số điện thoại, quản lý

    # Kiểm tra phát hiện câu hỏi chưa biết (bán hạt cà phê)
    unresolved = report["unresolved_inquiries"]
    assert len(unresolved) == 1
    assert unresolved[0]["slug"] == "ban_hat_cafe"

    # Kiểm tra sinh đề xuất cẩm nang
    proposals = report["playbook_rule_proposals"]
    assert len(proposals) == 1
    assert "Bán hạt cà phê" in proposals[0]["title"]
