# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit tests cho Google Trends SerpApi Source."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from ca_agents.clients.serpapi_client import SerpApiQuotaExceededError
from ca_agents.sources.gtrends_serpapi_source import (
    fetch_fnb_trends_serpapi,
    parse_gtrends_to_trend_items,
)


@pytest.fixture
def sample_trends_fixture() -> dict[str, Any]:
    fixture_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "fixtures"
        / "serpapi"
        / "google_trends_fnb_vn.json"
    )
    with open(fixture_path, encoding="utf-8") as f:
        payload: dict[str, Any] = json.load(f)
        return payload


def test_parse_gtrends_to_trend_items(sample_trends_fixture: dict[str, Any]) -> None:
    items = parse_gtrends_to_trend_items(sample_trends_fixture, "cà phê muối")
    assert len(items) == 2

    # Item 1: rising +620% -> dang_dinh
    item1 = items[0]
    assert item1.cum_tu_khoa_viral == "cách làm cà phê muối kem béo"
    assert item1.nguon_goc == "google_vn"
    assert item1.danh_muc == "am_thuc_fnb"
    assert item1.toc_do_tang_truong_24h == 620.0
    assert item1.vong_doi == "dang_dinh"

    # Item 2: breakout -> moi_nhu, 5000.0
    item2 = items[1]
    assert item2.cum_tu_khoa_viral == "cà phê muối huế"
    assert item2.vong_doi == "moi_nhu"
    assert item2.toc_do_tang_truong_24h == 5000.0
    assert "Breakout" in item2.du_bao_thoi_gian


def test_fetch_fnb_trends_serpapi_success(sample_trends_fixture: dict[str, Any]) -> None:
    with patch(
        "ca_agents.sources.gtrends_serpapi_source.search_serpapi",
        return_value=sample_trends_fixture,
    ) as mock_search:
        items = fetch_fnb_trends_serpapi("cà phê muối", geo="VN")
        assert len(items) == 2
        mock_search.assert_called_once()
        args = mock_search.call_args[0]
        assert args[0] == "google_trends"
        assert args[1]["q"] == "cà phê muối"
        assert args[1]["geo"] == "VN"


def test_fetch_fnb_trends_serpapi_graceful_on_quota() -> None:
    with patch(
        "ca_agents.sources.gtrends_serpapi_source.search_serpapi",
        side_effect=SerpApiQuotaExceededError("Hết quota"),
    ):
        items = fetch_fnb_trends_serpapi("matcha")
        assert items == []


def test_extract_interest_timeline(sample_trends_fixture: dict[str, Any]) -> None:
    from ca_agents.sources.gtrends_serpapi_source import extract_interest_timeline

    timeline = extract_interest_timeline(sample_trends_fixture)
    assert len(timeline) == 2
    assert timeline[0]["date"] == "Sep 7, 2026"
    assert timeline[0]["value"] == 72
    assert timeline[1]["date"] == "Sep 13, 2026"
    assert timeline[1]["value"] == 96


def test_parse_gtrends_with_timeline(sample_trends_fixture: dict[str, Any]) -> None:
    items = parse_gtrends_to_trend_items(sample_trends_fixture, "cà phê muối", include_timeline=True)
    # 2 rising items + 1 main keyword timeline item
    assert len(items) == 3
    main_item = items[0]
    assert main_item.cum_tu_khoa_viral == "cà phê muối"
    assert main_item.diem_tiem_nang_viral == 96
    assert main_item.vong_doi == "dang_dinh"
