"""Test validation cho TrendItem contract và StoreCandidate contract mở rộng (ADR-003)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from ca_contracts.catchment_survey import StoreCandidate
from ca_contracts.trend_item import TrendItem
from pydantic import ValidationError


def test_trend_item_valid() -> None:
    now = datetime.now(timezone.utc)
    item = TrendItem(
        keyword="cà phê muối",
        interest_score=95,
        vong_doi="dang_dinh",
        is_breakout=True,
        window="now 7-d",
        fetched_at=now,
    )
    assert item.keyword == "cà phê muối"
    assert item.interest_score == 95
    assert item.nguon_goc == "google_vn"
    assert item.danh_muc == "am_thuc_fnb"
    assert item.vong_doi == "dang_dinh"
    assert item.is_breakout is True
    assert item.window == "now 7-d"
    assert item.fetched_at == now


def test_trend_item_validation_error() -> None:
    now = datetime.now(timezone.utc)
    # interest_score > 100
    with pytest.raises(ValidationError):
        TrendItem(
            keyword="trà ô long",
            interest_score=105,
            vong_doi="moi_nhu",
            fetched_at=now,
        )

    # Invalid vong_doi
    with pytest.raises(ValidationError):
        TrendItem(
            keyword="trà sữa",
            interest_score=50,
            vong_doi="invalid_phase",  # type: ignore
            fetched_at=now,
        )


def test_store_candidate_backward_compat() -> None:
    # Khởi tạo theo cách cũ không có các trường mới
    old_style = StoreCandidate(
        id="store_001",
        name="Cà phê vỉa hè",
        distance_km=1.2,
        rating=4.5,
        review_count=100,
    )
    assert old_style.id == "store_001"
    assert old_style.place_id == "store_001"
    assert old_style.data_source == "camoufox"
    assert old_style.lat == 0.0
    assert old_style.lng == 0.0
    assert old_style.fetched_at is None


def test_store_candidate_serpapi_fields() -> None:
    # Khởi tạo với place_id và data_source mới
    candidate = StoreCandidate(
        place_id="ChIJ_test123",
        name="The Coffee House",
        address="123 Lê Lợi, Q1",
        lat=10.7769,
        lng=106.7009,
        distance_km=0.5,
        rating=4.6,
        review_count=850,
        data_source="serpapi",
        fetched_at="2026-09-13T20:45:00Z",
    )
    assert candidate.id == "ChIJ_test123"
    assert candidate.place_id == "ChIJ_test123"
    assert candidate.data_source == "serpapi"
    assert candidate.lat == 10.7769
    assert candidate.lng == 106.7009
    assert candidate.rating == 4.6
    assert candidate.review_count == 850
