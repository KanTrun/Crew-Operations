"""Unit tests for Chat AI Scheduler Agent."""

from __future__ import annotations

import asyncio
from datetime import date

from ca_api.persist import (
    chat_message_create,
    init_db,
    register,
)
from ca_api.services.chat_scheduler_agent import (
    build_schedule_plan,
    handle_scheduling_request,
    parse_availability_details,
    parse_availability_text,
    submit_availability_confirmation,
    update_availability_confirmation,
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


def test_parse_exact_and_relative_dates_deterministically() -> None:
    reference = date(2026, 9, 18)

    exact = parse_availability_details(
        "Em bận ngày 21/09 từ 8h-11h và 22/09/2026 13:30-15:00",
        reference_date=reference,
    )
    assert exact["busy_intervals"] == [
        {"date": "2026-09-21", "tuan_iso": "2026-W39", "thu": "T2", "start": "08:00", "end": "11:00"},
        {"date": "2026-09-22", "tuan_iso": "2026-W39", "thu": "T3", "start": "13:30", "end": "15:00"},
    ]

    relative = parse_availability_details(
        "Hôm nay bận 18h-20h, ngày mai bận 8h-9h",
        reference_date=reference,
    )
    assert [item["date"] for item in relative["busy_intervals"]] == ["2026-09-18", "2026-09-19"]


def test_parse_next_weekday_and_cross_week_mapping() -> None:
    parsed = parse_availability_details(
        "Thứ hai tuần sau bận 8h-11h",
        reference_date=date(2026, 9, 18),
    )
    assert parsed["busy_intervals"] == [
        {"date": "2026-09-21", "tuan_iso": "2026-W39", "thu": "T2", "start": "08:00", "end": "11:00"},
    ]

    cross_year = parse_availability_details(
        "Bận 02/01 từ 9h-10h",
        reference_date=date(2026, 12, 30),
    )
    assert cross_year["busy_intervals"][0]["date"] == "2027-01-02"
    assert cross_year["busy_intervals"][0]["tuan_iso"] == "2026-W53"


def test_parse_does_not_fabricate_availability_or_ambiguous_busy_time() -> None:
    reference = date(2026, 9, 18)
    assert parse_availability_text("Em rảnh T2") == {}
    assert parse_availability_details("Em bận 8h-11h", reference_date=reference)["busy_intervals"] == []
    assert parse_availability_details("Em bận T2", reference_date=reference)["busy_intervals"] == []


def test_parse_normalizes_overlaps_and_removes_conflicting_available_shift() -> None:
    parsed = parse_availability_details(
        "Em rảnh sáng thứ 2 nhưng bận thứ 2 từ 8h-10h và 9h30-11h",
        reference_date=date(2026, 9, 18),
    )
    assert parsed["busy_intervals"] == [
        {"date": "2026-09-14", "tuan_iso": "2026-W38", "thu": "T2", "start": "08:00", "end": "11:00"},
    ]
    assert parsed["availability"] == {}


def test_confirmation_contains_busy_intervals_and_vietnamese_summary() -> None:
    init_db()
    draft = submit_availability_confirmation(
        conv_id="conv_busy_confirmation",
        nv_id="nv_busy_confirmation",
        display_name="Nhân viên bận",
        text="Ngày mai em bận 8h-11h",
        reference_date=date(2026, 9, 18),
    )

    assert draft is not None
    assert draft["tuan_iso"] == "2026-W38"
    assert draft["availability"]["T7"] == ["Chiều", "Tối"]
    assert draft["availability"]["T2"] == ["Sáng", "Chiều", "Tối"]
    assert draft["busy_intervals"] == [
        {"date": "2026-09-19", "tuan_iso": "2026-W38", "thu": "T7", "start": "08:00", "end": "11:00"},
    ]
    assert draft["summary"] == "Bận Thứ Bảy (T7) 19/09/2026, 08:00-11:00. Không tự suy diễn ca rảnh."


def test_busy_only_correction_keeps_non_conflicting_shifts_available() -> None:
    init_db()
    draft = submit_availability_confirmation(
        conv_id="conv_busy_correction",
        nv_id="nv_busy_correction",
        display_name="Nhân viên sửa lịch",
        text="Em rảnh sáng thứ 2",
        tuan_iso="2026-W38",
        reference_date=date(2026, 9, 18),
    )
    assert draft is not None

    corrected = update_availability_confirmation(
        str(draft["id"]),
        nv_id="nv_busy_correction",
        status="cho_xac_nhan",
        correction="Ngày 19/09/2026 em bận 8h-11h",
    )

    assert corrected["availability"]["T7"] == ["Chiều", "Tối"]
    assert corrected["availability"]["T2"] == ["Sáng", "Chiều", "Tối"]


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

    # Bước 2: bot tạo card xác nhận; dữ liệu chưa xác nhận không được xếp.
    draft = submit_availability_confirmation(
        conv_id=conv_id,
        nv_id=nv_id,
        display_name="Nhân Viên Sched",
        text="Em rảnh sáng T2, T4, T6 tuần sau nhé!",
    )
    assert draft and draft["status"] == "cho_xac_nhan"
    confirmation_id = str(draft["id"])
    # Lấy đúng tuần mà availability được lưu (text "tuần sau" → tuần sau)
    draft_week = str(draft.get("tuan_iso") or "")
    update_availability_confirmation(confirmation_id, nv_id=nv_id, status="da_xac_nhan")

    # Bước 3: chỉ dữ liệu đã xác nhận mới được bot xếp.
    bot_msg = asyncio.run(
        handle_scheduling_request(
            conv_id=conv_id,
            trigger_msg="@agent_lich xếp lịch",
            user_sess={"nv_id": nv_id, "role": "nhan_vien", "store_id": "quan_01", "tuan_iso": draft_week},
        )
    )
    assert bot_msg is not None
    assert bot_msg["sender_id"] == "ai_scheduler"
    assert bot_msg["type"] == "ops_card"
    assert "BẢNG XẾP LỊCH CA" in bot_msg["content"]
    assert "proposal" in bot_msg["metadata"]
