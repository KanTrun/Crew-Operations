"""AG-COPILOT tool: đề xuất luật phải trung thực khi de_xuat trả None.

Hồi quy: de_xuat đổi hợp đồng sang `dict | None` (không bịa khi thiếu tín
hiệu); tool từng gọi `best.get` trên phần tử None → crash.
"""

from __future__ import annotations

from typing import Any

import pytest
from ca_agents.ag_copilot import tool_registry as tr
from ca_agents.ag_copilot.tool_registry import (
    configure_data_sources,
    tool_propose_rule_from_recent_edits,
)


@pytest.fixture
def _restore_sources() -> Any:
    saved = dict(tr._SOURCES)
    yield
    configure_data_sources(**saved)


def _mau_lap_lai() -> list[dict[str, Any]]:
    return [{"mau": "nha_ca", "loai_luat": "nhu_cau_ca", "n": 3, "bang_chung": ["0", "1", "2"]}]


def test_propose_rule_bao_thieu_tin_hieu_khi_de_xuat_none(_restore_sources: None) -> None:
    configure_data_sources(
        list_sua=lambda **kw: [{"loai": "nha_ca"}] * 3,
        tim_mau=lambda sua: _mau_lap_lai(),
        de_xuat=lambda mau: None,
    )
    res = tool_propose_rule_from_recent_edits()
    assert res.success is True
    assert res.data["co_de_xuat"] is False
    assert res.data["so_mau"] == 1
    assert "tín hiệu" in res.summary.lower() or "chưa" in res.summary.lower()
    assert res.requires_confirmation is False


def test_propose_rule_tra_de_xuat_khi_co_du_lieu(_restore_sources: None) -> None:
    luat = {"id": "luat_nha_ca", "cau": "Thứ năm cần ít nhất 1 người.", "loai": "nhu_cau_ca"}
    configure_data_sources(
        list_sua=lambda **kw: [{"loai": "nha_ca"}] * 3,
        tim_mau=lambda sua: _mau_lap_lai(),
        de_xuat=lambda mau: dict(luat),
    )
    res = tool_propose_rule_from_recent_edits()
    assert res.success is True
    assert res.data["co_de_xuat"] is True
    assert res.data["de_xuat"]["cau"] == luat["cau"]
    assert res.requires_confirmation is True
