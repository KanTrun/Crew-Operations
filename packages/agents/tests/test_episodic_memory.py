# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit test cho Episodic Memory & Reflection (plan 260918 mục 4).

ADR-002: suy ngẫm tất định, từ dữ liệu thật, không LLM.
"""

from __future__ import annotations

from ca_agents.ag_explain import answer_reflection, build_episodes, reflect_on_episodes
from ca_contracts.episodic_memory import EpisodeType


def _rows() -> list[dict]:
    return [
        {
            "id": "ep_1", "loai": "phan_nan", "thoi_gian": "2026-09-15",
            "mo_ta": "Khách chờ 12 phút", "nhan_vien": "Minh", "ca": "T6_toi",
            "chi_tiet": {"ly_do": "Minh bận pha 3 ly"},
        },
        {
            "id": "ep_2", "loai": "phan_nan", "thoi_gian": "2026-09-16",
            "mo_ta": "Khách chờ 15 phút", "nhan_vien": "Minh", "ca": "T6_toi",
            "chi_tiet": {"ly_do": "Minh bận pha 3 ly"},
        },
        {
            "id": "ep_3", "loai": "doanh_thu_cao", "thoi_gian": "2026-09-17",
            "mo_ta": "Doanh thu cao", "nhan_vien": "", "ca": "T7_toi",
            "chi_tiet": {"mon": "matcha"},
        },
    ]


def test_build_episodes() -> None:
    episodes = build_episodes(_rows())
    assert len(episodes) == 3
    assert episodes[0].loai == EpisodeType.PHAN_NAN


def test_reflect_on_episodes_finds_root_cause() -> None:
    episodes = build_episodes(_rows())
    reflections = reflect_on_episodes(episodes, min_episodes=2)
    # Nhóm phàn nàn (Minh, T6_toi) có 2 episode → tạo reflection
    assert len(reflections) >= 1
    assert "Minh" in reflections[0].nguyen_nhan_goc
    assert "T6_toi" in reflections[0].nguyen_nhan_goc


def test_answer_reflection_empty() -> None:
    result = answer_reflection("Tuần này có gì bất thường?", [])
    assert result.ket_luan != ""
    assert result.reflections == []


def test_answer_reflection_with_data() -> None:
    result = answer_reflection("Tuần này có gì bất thường?", _rows())
    assert len(result.episodes) == 3
    assert len(result.reflections) >= 1
    assert "Phát hiện" in result.ket_luan