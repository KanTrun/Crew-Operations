"""Unit tests for chat lifecycle: auto-join onboarding and offboarding archive."""

from __future__ import annotations

import pytest
from ca_api.persist import (
    chat_conversation_get,
    chat_conversation_list_for_user,
    chat_message_create,
    chat_messages_list,
    chat_participant_deactivate,
    register,
    session,
    user_deactivate,
    user_is_active,
)


def test_onboarding_auto_join_general_chat() -> None:
    # 1. Đăng ký nhân viên mới
    reg = register("hoa_barista", "password123", "Hoa Barista")
    nv_id = reg["nv_id"]
    token = reg["token"]

    # 2. Kiểm tra trạng thái tài khoản
    assert user_is_active(nv_id) is True

    # 3. Kiểm tra tự động tham gia nhóm chung toàn quán
    conv = chat_conversation_get("conv_general_quan_01", nv_id)
    assert conv is not None
    assert conv["is_locked"] is True
    assert "Hội Quán Chung" in conv["display_name"]

    # Thành viên có trong danh sách và status = 'active'
    part = next((p for p in conv["participants"] if p["nv_id"] == nv_id), None)
    assert part is not None
    assert part["status"] == "active"
    assert part["role"] == "member"

    # Tin nhắn chào mừng đã xuất hiện trong phòng
    msgs = chat_messages_list("conv_general_quan_01")
    assert any("Hoa Barista" in m["content"] for m in msgs)

    # 4. Kiểm tra hộp thư của Hoa
    box = chat_conversation_list_for_user(nv_id)
    assert len(box) >= 1
    assert any(c["id"] == "conv_general_quan_01" for c in box)


def test_offboarding_deactivate_and_archive() -> None:
    # 1. Tạo nhân viên và cho gửi tin nhắn vào nhóm
    reg = register("tuan_phucvu", "password123", "Tuấn Phục Vụ")
    nv_id = reg["nv_id"]
    token = reg["token"]

    # Gửi tin nhắn hợp lệ
    msg = chat_message_create(
        conv_id="conv_general_quan_01",
        sender_id=nv_id,
        content="Em chào cả quán ạ!",
    )
    msg_id = msg["id"]
    assert msg["content"] == "Em chào cả quán ạ!"

    # Token đang hợp lệ
    assert session(f"Bearer {token}") is not None

    # 2. Thực hiện Offboarding (Vô hiệu hóa tài khoản)
    success = user_deactivate(nv_id)
    assert success is True

    # 3. Xác minh tài khoản không còn active
    assert user_is_active(nv_id) is False

    # Token phiên làm việc bị hủy lập tức (force logout)
    assert session(f"Bearer {token}") is None

    # 4. Xác minh trạng thái trong chat_participants chuyển thành 'archived'
    conv = chat_conversation_get("conv_general_quan_01")
    part = next((p for p in conv["participants"] if p["nv_id"] == nv_id), None)
    assert part is not None
    assert part["status"] == "archived"
    assert part["archived_at"] != ""

    # 5. Nhân viên đã nghỉ KHÔNG thể gửi thêm tin nhắn mới
    with pytest.raises(ValueError, match="tai_khoan_da_vo_hieu_hoa"):
        chat_message_create(
            conv_id="conv_general_quan_01",
            sender_id=nv_id,
            content="Tin nhắn cố gửi khi đã nghỉ việc",
        )

    # 6. Lịch sử tin nhắn cũ của nhân viên VẪN được bảo tồn cho người khác xem
    msgs_after = chat_messages_list("conv_general_quan_01")
    old_msg = next((m for m in msgs_after if m["id"] == msg_id), None)
    assert old_msg is not None
    assert old_msg["content"] == "Em chào cả quán ạ!"

    # 7. Danh sách hộp thư của nhân viên nghỉ việc trở về rỗng
    box_after = chat_conversation_list_for_user(nv_id)
    assert len(box_after) == 0
