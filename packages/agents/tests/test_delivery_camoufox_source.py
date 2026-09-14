"""Kiểm thử cho delivery_camoufox_source: parser giá, trích xuất dữ liệu, cache."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from ca_agents.clients.camoufox_client import CamoufoxUnavailable
from ca_agents.sources.delivery_camoufox_source import (
    _cache_get,
    _cache_key,
    _cache_put,
    _reset_cache,
    extract_delivery_stores_from_json,
    parse_price,
    scrape_delivery_stores_camoufox,
)
from ca_contracts.catchment_survey import StoreCandidate

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "delivery_stores_sample.json"


def test_parse_price_various_formats() -> None:
    assert parse_price("32.000đ") == 32000
    assert parse_price("35k") == 35000
    assert parse_price("29.5k") == 29500
    assert parse_price(45000) == 45000
    assert parse_price("45,000") == 45000
    assert parse_price("55k") == 55000
    assert parse_price("0") == 0
    assert parse_price("") == 0
    assert parse_price(None) == 0


def test_extract_delivery_stores_from_fixture() -> None:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    stores = extract_delivery_stores_from_json(raw)

    assert len(stores) == 6
    s1 = stores[0]
    assert s1.id == "res_001"
    assert "Chú Long" in s1.name
    assert s1.rating == 4.8
    assert s1.review_count == 2150
    assert s1.is_favorite is True
    assert len(s1.dishes) == 3

    best_seller = next(d for d in s1.dishes if d.is_bestseller)
    assert best_seller.price == 32000
    assert "đặc biệt" in best_seller.name.lower()


def test_delivery_cache_lifecycle() -> None:
    _reset_cache()
    key = _cache_key(10.78, 106.69, "cà phê", 5.0)

    assert _cache_get(key) is None

    sample_stores = [
        StoreCandidate(
            id="s1",
            name="Test",
            distance_km=1.0,
            rating=4.5,
            review_count=100,
        )
    ]
    _cache_put(key, sample_stores)

    hit = _cache_get(key)
    assert hit is not None
    assert len(hit) == 1
    assert hit[0].id == "s1"

    _reset_cache()
    assert _cache_get(key) is None


def test_scrape_delivery_stores_camoufox_unavailable() -> None:
    _reset_cache()
    with patch(
        "ca_agents.sources.delivery_camoufox_source.scrape_page",
        side_effect=CamoufoxUnavailable("Chưa cài đặt"),
    ):
        with pytest.raises(CamoufoxUnavailable):
            scrape_delivery_stores_camoufox(10.78, 106.69, "cà phê", 5.0)
