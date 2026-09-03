"""Unit tests for Smart Shift Swap & Emergency Leave Matching Engine (smart_swap.py)."""

from __future__ import annotations

from ca_agents.ag_msg.extract import classify
from ca_agents.smart_swap import (
    find_emergency_cover_candidates,
    find_swap_candidates,
    format_swap_recommendation,
)


def _fixture_staff() -> list[dict]:
    return [
        {"id": "nv_lan", "ten": "Lan Nguyễn", "ky_nang": ["pha_che", "thu_ngan"]},
        {"id": "nv_hung", "ten": "Hùng Trần", "ky_nang": ["thu_ngan"]},
        {"id": "nv_minh", "ten": "Minh Phạm", "ky_nang": ["pha_che"]},
        {"id": "nv_an", "ten": "An Lê", "ky_nang": ["pha_che", "phuc_vu"]},
    ]


def _fixture_ca() -> list[dict]:
    return [
        {"id": "ca_t5_sang", "thu": "T5", "khung": "sang", "vi_tri": "pha_che"},
        {"id": "ca_t5_chieu", "thu": "T5", "khung": "chieu", "vi_tri": "pha_che"},
        {"id": "ca_t5_toi", "thu": "T5", "khung": "toi", "vi_tri": "pha_che"},
        {"id": "ca_t6_chieu", "thu": "T6", "khung": "chieu", "vi_tri": "thu_ngan"},
    ]


def test_swap_skill_and_availability_filtering() -> None:
    staff = _fixture_staff()
    ca = _fixture_ca()
    # Giả lập: Minh đang bận ca chiều T5, Hùng không có kỹ năng pha chế
    assignments = {
        "ca_t5_chieu": ["nv_minh"],
        "ca_t5_sang": ["nv_an"],
    }

    cands = find_swap_candidates(
        requester_id="nv_tuan",
        ca_id="ca_t5_chieu",
        staff_list=staff,
        ca_list=ca,
        phan_cong=assignments,
    )

    # 1. Hùng không có kỹ năng pha chế -> score = 0
    hung = next(c for c in cands if c.nv_id == "nv_hung")
    assert not hung.is_qualified
    assert hung.score == 0

    # 2. Minh đang bận đúng ca chiều T5 -> score = 0
    minh = next(c for c in cands if c.nv_id == "nv_minh")
    assert not minh.is_available
    assert minh.score == 0

    # 3. Lan rảnh và đúng kỹ năng pha chế, chưa có ca nào trong tuần -> Top 1
    assert cands[0].nv_id == "nv_lan"
    assert cands[0].is_qualified
    assert cands[0].is_available
    assert cands[0].score >= 80


def test_consecutive_shift_warning_and_penalty() -> None:
    staff = _fixture_staff()
    ca = _fixture_ca()
    # Giả lập: Lan đã làm ca sáng T5 VÀ ca tối T5. Nếu nhận thêm ca chiều T5 sẽ là 3 ca liên tiếp
    assignments = {
        "ca_t5_sang": ["nv_lan"],
        "ca_t5_toi": ["nv_lan"],
    }

    cands = find_swap_candidates(
        requester_id="nv_tuan",
        ca_id="ca_t5_chieu",
        staff_list=staff,
        ca_list=ca,
        phan_cong=assignments,
        max_ca_lien_tuc=2,
    )

    lan = next(c for c in cands if c.nv_id == "nv_lan")
    assert lan.consecutive_shifts_today >= 3
    assert any("Vượt giới hạn Cẩm nang" in w for w in lan.warnings)
    assert lan.score < 50


def test_emergency_cover_candidates_and_formatting() -> None:
    staff = _fixture_staff()
    ca = _fixture_ca()
    assignments = {"ca_t5_sang": ["nv_lan"]}

    emergency_cands = find_emergency_cover_candidates(
        absent_staff_id="nv_lan",
        ca_id="ca_t5_sang",
        staff_list=staff,
        ca_list=ca,
        phan_cong=assignments,
    )

    assert len(emergency_cands) > 0
    top = emergency_cands[0]
    assert top.is_qualified and top.is_available

    text = format_swap_recommendation(
        requester_name="Lan",
        target_ca_label="Sáng Thứ 5 (Pha chế)",
        candidates=emergency_cands,
        is_emergency=True,
    )
    assert "🚨 YÊU CẦU BÙ CA KHẨN CẤP" in text
    assert top.ten in text


def test_classify_detects_emergency_intent() -> None:
    msg_normal = "anh ơi em bận thi muốn đổi ca với bạn"
    res_normal = classify(msg_normal)
    assert not res_normal.rang_buoc.get("khan_cap")

    msg_urgent = "Em bị sốt cao đột xuất không đi ca tối nay được, xin nghỉ gấp ạ"
    res_urgent = classify(msg_urgent)
    assert res_urgent.intent == "xin_nghi"
    assert res_urgent.rang_buoc.get("khan_cap") is True
