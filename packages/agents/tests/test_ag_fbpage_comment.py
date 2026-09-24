# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit tests for AG-FBPAGE Public Comment System Prompt & Action Classifier."""

from __future__ import annotations

import pytest
from ca_agents.ag_fbpage import classify_comment_action
from ca_agents.facebook_page import hide_comment
from ca_agents.prompts.ag_fbpage.system_prompt import (
    build_fb_comment_system_prompt,
)


def test_comment_system_prompt_structure() -> None:
    prompt = build_fb_comment_system_prompt("Menu: Cà phê đen 25k")
    # Kiểm tra đầy đủ 9 phần của bản đặc tả bình luận công khai
    assert "## 1. VAI TRÒ" in prompt
    assert "BÌNH LUẬN CÔNG KHAI" in prompt
    assert "HIỂN THỊ CÔNG KHAI" in prompt
    assert "## 2. DỮ LIỆU ĐƯỢC PHÉP DÙNG" in prompt
    assert "## 3. PHÂN LOẠI & PHẠM VI TOÀN QUYỀN XỬ LÝ" in prompt
    assert "ẨN COMMENT + CHUYỂN SANG DM" in prompt
    assert "## 4. DANH SÁCH BẤT KHẢ KHÁNG" in prompt
    assert "6 trường hợp" in prompt or "Mục 4" in prompt
    assert "Tố cáo an toàn thực phẩm công khai" in prompt
    assert "## 5. KHI KHÔNG CHẮC CHẮN" in prompt
    assert "## 6. QUY TẮC KỸ THUẬT RIÊNG CHO COMMENT" in prompt
    assert "Không đàm phán số tiền bồi thường" in prompt
    assert "## 7. GIỚI HẠN TUYỆT ĐỐI" in prompt
    assert "## 8. TONE & NGÔN NGỮ" in prompt
    assert "NGẮN GỌN HƠN DM" in prompt
    assert "## 9. REVIEW ĐỊNH KỲ" in prompt
    assert "Menu: Cà phê đen 25k" in prompt


@pytest.mark.parametrize(
    "text",
    [
        "Cho mình 2 ly bạc xỉu ship về số 0912345678 nhé",
        "Giao qua địa chỉ 123 Lê Lợi, SĐT: 0388999888",
        "+84909112233 mình muốn đặt hàng",
    ],
)
def test_comment_with_phone_triggers_hide_and_dm(text: str) -> None:
    """Mục 3b: Chứa SĐT / địa chỉ -> tự động ẩn ngay + trả lời công khai chuyển DM."""
    res = classify_comment_action(text)
    assert res["category"] == "hide_and_dm"
    assert res["should_hide"] is True
    assert "nhắn tin riêng" in res["reply_public"]


def test_comment_with_complaint_triggers_dm_without_public_negotiation() -> None:
    """Mục 3b: Phàn nàn thông thường -> xin lỗi ngắn 1 câu + chuyển DM (không đàm phán tiền công khai)."""
    res = classify_comment_action("Hôm qua quán phục vụ rất chậm và nước uống bị chua!")
    assert res["category"] == "complaint_to_dm"
    assert res["should_hide"] is False
    assert "xin lỗi" in res["reply_public"].lower()
    assert "tin nhắn riêng" in res["reply_public"].lower()
    assert "200.000" not in res["reply_public"]  # Không đàm phán số tiền bồi thường công khai


def test_comment_with_booking_intent_moves_to_dm() -> None:
    """Mục 3b: Đặt bàn / đặt tiệc riêng -> chuyển sang DM để tư vấn chi tiết."""
    res = classify_comment_action("Tối nay mình muốn đặt bàn nhóm 10 người lúc 19h")
    assert res["category"] == "booking_to_dm"
    assert res["should_hide"] is False
    assert "tin nhắn riêng" in res["reply_public"].lower()


def test_comment_standard_public_inquiry() -> None:
    """Mục 3a: Câu hỏi thông thường -> trả lời công khai."""
    res = classify_comment_action("Quán mấy giờ đóng cửa vậy ạ?")
    assert res["category"] == "public_reply"
    assert res["should_hide"] is False
    assert res["reply_public"] is None


def test_hide_comment_api_raises_when_missing_id() -> None:
    with pytest.raises(RuntimeError, match="thieu_comment_id"):
        hide_comment("")
