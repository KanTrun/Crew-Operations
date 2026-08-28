"""Tests for AG-TKB extract in replay mode."""

from __future__ import annotations

import pytest
from ca_agents.ag_tkb import extract_tkb


def test_extract_known_fixture_has_spans() -> None:
    result = extract_tkb("tkb_01")
    assert result["spans"], "tkb_01 should have spans"
    assert result["confidence"] >= 0.7
    assert result["blur"] is False


def test_extract_blur_fixture_low_confidence() -> None:
    # Blur detection via filename
    result = extract_tkb("tkb_01_blur")
    assert result["blur"] is True
    assert result["confidence"] < 0.7


def test_extract_returns_required_keys() -> None:
    result = extract_tkb("tkb_02")
    for key in ("rows", "confidence", "spans", "blur"):
        assert key in result, f"missing key: {key}"


def test_extract_unknown_id_returns_empty_spans() -> None:
    result = extract_tkb("tkb_unknown_xyz")
    assert result["rows"] == []
    assert result["spans"] == []
    assert result["confidence"] < 0.7


def test_extract_live_mode_raises() -> None:
    with pytest.raises(NotImplementedError):
        extract_tkb("tkb_01", mode="live")
