"""Unit tests for Chat AI Scheduler Agent."""

from __future__ import annotations

import asyncio
from ca_api.persist import (
    chat_conversation_get,
    chat_message_create,
    chat_messages_list,
    init_db,
    register,
)
from ca_api.services.chat_scheduler_agent import (
    build_schedule_plan,
    handle_scheduling_request,
    parse_availability_text,
)


def test_parse_availability_natural_language() -> None:
    # Test câu văn 1
    t1 = "Tuần tới em rảnh sáng T2, T4, T6 và sáng CN nhé ạ!"
    res1 = parse_availability_text(t1)
    assert "T2" in res1 and "Sáng" in res1["T2"]
    assert "T4" in res1 and "Sáng" in res1["T4"]
    assert "T6" in res1 and "Sáng" in res1["T6"]
    assert "CN" in res1 and "Sáng" in res1["CN"]

    # Test câu văn 2
    t2 = "Em Tuấn rảnh tối T2, T3, T5, T7, CN ạ"
    res2 = parse_availability_text(t2)
    assert "T2" in res2 and "Tối" in res2["T2"]
    assert "T7" in res2 and "Tối" in res2["T7"]

    # Test câu văn 3
    t3 = "Em Minh đăng ký rảnh chiều T3, T4, T5, T6 và sáng T7 ạ"
    res3 = parse_availability_text(t3)
    assert "T3" in res3 and "Chiều" in res3["T3"]
    assert "T7" in res3 and "Sáng" in res3["T7"]


def test_build_schedule_plan_fairness() -> None:
    availabilities = {
        "Hoa Barista": {"T2": ["Sáng"], "T4": ["Sáng"], "T6": ["Sáng"]},
        "Tuấn Phục Vụ": {"T2": ["Tối"], "T3": ["Tối"], "T5": ["Tối"]},
    }
    schedule, counts = build_schedule_plan(availabilities)
    assert "Hoa Barista" in schedule["T2"]["Sáng"]
    assert "Tuấn Phục Vụ" in schedule["T2"]["Tối"]
    assert counts["Hoa Barista"] >= 1
    assert counts["Tuấn Phục Vụ"] >= 1


def test_scheduler_agent_end_to_end() -> None:
    init_db()
    conv_id = "conv_general_quan_01"

    # Tạo nhân viên test
    reg = register("test_nv_sched", "password123", "Nhân Viên Sched")
    nv_id = reg["nv_id"]

    # Gửi tin nhắn rảnh
    chat_message_create(
        conv_id=conv_id,
        sender_id=nv_id,
        content="Em rảnh sáng T2, T4, T6 tuần sau nhé!",
    )

    # Trigger agent
    bot_msg = asyncio.run(
        handle_scheduling_request(
            conv_id=conv_id,
            trigger_msg="@agent_lich xếp lịch",
            user_sess={"nv_id": nv_id, "role": "nhan_vien", "store_id": "quan_01"},
        )
    )
    assert bot_msg is not None
    assert bot_msg["sender_id"] == "ai_scheduler"
    assert bot_msg["type"] == "ops_card"
    assert "BẢNG XẾP LỊCH CA" in bot_msg["content"]
    assert "proposal" in bot_msg["metadata"]
