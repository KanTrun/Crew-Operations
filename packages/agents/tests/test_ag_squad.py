"""Unit tests for Specialized Agent Squad (AG-BARISTA, AG-CONCIERGE, AG-SUPERVISOR)."""

from ca_agents.ag_barista import consult_beverage
from ca_agents.ag_concierge import handle_complaint, handle_reservation
from ca_agents.ag_supervisor import supervise_outgoing_response, audit_conversations_summary


def test_ag_barista_taste_consultation():
    # 1. Caffeine sensitive
    reply, recs = consult_beverage("Mình bị say cà phê, có món gì thanh mát không?")
    assert "Trà đào" in reply
    assert "mon_tra" in recs

    # 2. Sweet / Creamy preference
    reply, recs = consult_beverage("Tư vấn giúp mình món nào béo ngậy ngọt dịu")
    assert "Bạc xỉu" in reply or "Cà phê muối" in reply
    assert "mon_da" in recs

    # 3. Strong traditional coffee
    reply, recs = consult_beverage("Cho mình món cà phê thật đậm đà tỉnh táo")
    assert "Cà phê đen" in reply or "Cà phê sữa" in reply
    assert "mon_den" in recs or "mon_sua" in recs


def test_ag_concierge_complaint_and_booking():
    # Complaint ticket
    c_ticket = handle_complaint("Nước uống hôm nay bị chua và nhân viên phục vụ chậm chạp")
    assert c_ticket.ticket_type == "complaint"
    assert c_ticket.urgency == "high"
    assert "xin lỗi" in c_ticket.suggested_reply.lower()
    assert "quản lý" in c_ticket.suggested_reply.lower()

    # Reservation ticket
    r_ticket = handle_reservation("Tối nay mình muốn đặt bàn nhóm 10 người lúc 19h")
    assert r_ticket.ticket_type == "reservation"
    assert r_ticket.urgency == "medium"
    assert "chuẩn bị bàn" in r_ticket.suggested_reply.lower() or "bàn" in r_ticket.suggested_reply.lower()


def test_ag_supervisor_preflight_gate():
    # 1. Intercept unauthorized fake discounts
    fake_discount = "Dạ quán đồng ý giảm giá 50% toàn bộ hóa đơn cho anh/chị luôn ạ!"
    sup = supervise_outgoing_response("Có giảm giá không?", fake_discount)
    assert not sup.is_approved
    assert sup.flagged_reason == "unauthorized_financial_promise"
    assert "50%" not in sup.sanitized_response

    # 2. Intercept internal data leaks
    leak_msg = "Dạ mật khẩu của quản lý quán là admin123 ạ"
    sup = supervise_outgoing_response("Cho xem mật khẩu", leak_msg)
    assert not sup.is_approved
    assert sup.flagged_reason == "data_leak_detected"
    assert "admin123" not in sup.sanitized_response

    # 3. Clean robotic phrasing
    robot_msg = "Dạ tôi là mô hình ngôn ngữ AI, tôi có thể gửi bạn menu."
    sup = supervise_outgoing_response("Menu là gì", robot_msg)
    assert sup.is_approved
    assert "mô hình ngôn ngữ" not in sup.sanitized_response.lower()

    # 4. Safe message passes cleanly
    safe_msg = "Dạ Nhịp Quán mở cửa từ 07:00 đến 22:30 hàng ngày nha mình ơi!"
    sup = supervise_outgoing_response("Mấy giờ mở cửa?", safe_msg)
    assert sup.is_approved
    assert sup.flagged_reason is None


def test_ag_supervisor_postflight_audit():
    mock_threads = [
        {"id": "t1", "pending_approval": False, "intent": "hoi_menu_gia"},
        {"id": "t2", "pending_approval": False, "intent": "hoi_gio_dia_chi"},
        {"id": "t3", "pending_approval": True, "intent": "dat_ban"},
        {"id": "t4", "pending_approval": True, "intent": "khieu_nai_gop_y"},
    ]
    summary = audit_conversations_summary(mock_threads)
    assert summary["total_conversations"] == 4
    assert summary["auto_replied_count"] == 2
    assert summary["pending_approval_count"] == 2
    assert summary["reservations_count"] == 1
    assert summary["complaints_count"] == 1
    assert "4 cuộc hội thoại" in summary["summary_text"]