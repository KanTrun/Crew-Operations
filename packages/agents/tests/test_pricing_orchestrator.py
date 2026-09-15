"""Kiểm thử cho orchestrator của AG-PRICING (Catchment Price Radar)."""

from __future__ import annotations

import json
from pathlib import Path

from ca_agents.ag_pricing.orchestrator import run_catchment_price_survey
from ca_agents.sources.delivery_camoufox_source import extract_delivery_stores_from_json
from ca_contracts.catchment_survey import CatchmentSurveyRequest, StoreCandidate

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "delivery_stores_sample.json"


def test_orchestrator_end_to_end_with_fixture() -> None:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    stores = extract_delivery_stores_from_json(raw)

    def mock_fetcher(lat: float, lng: float, kw: str, r: float) -> list[StoreCandidate]:
        return stores

    req = CatchmentSurveyRequest(
        latitude=10.782,
        longitude=106.698,
        address="Đa Kao, Quận 1",
        radius_km=3.0,
        category_keyword="cà phê",
        min_reviews=50,
        min_rating=4.2,
        only_bestsellers=True,
    )

    resp = run_catchment_price_survey(req, store_fetcher=mock_fetcher)

    assert resp.total_scanned_stores == 6
    assert resp.validated_stores_count == 3
    assert resp.disqualified_stores_count == 3
    assert len(resp.validated_stores) == 3

    # Phổ giá
    dist = resp.price_distribution
    assert dist.sample_size > 0
    assert dist.min_price >= 20000
    assert dist.max_price <= 100000
    assert dist.sweet_spot_range[0] <= dist.sweet_spot_range[1]
    assert dist.median_price >= dist.p25_price

    # Top signature món của đối thủ
    assert len(resp.top_competitor_signatures) == 3

    # Market Insight
    assert "Báo cáo định vị giá" in resp.market_insight
    assert "Sweet Spot" in resp.market_insight
    assert "Khuyến nghị chiến lược cho quán" in resp.market_insight


def test_orchestrator_handles_empty_or_no_stores() -> None:
    def empty_fetcher(lat: float, lng: float, kw: str, r: float) -> list[StoreCandidate]:
        return []

    req = CatchmentSurveyRequest(
        latitude=10.0,
        longitude=105.0,
        category_keyword="món hiếm",
    )

    resp = run_catchment_price_survey(req, store_fetcher=empty_fetcher)

    assert resp.total_scanned_stores == 0
    assert resp.validated_stores_count == 0
    assert resp.price_distribution.sample_size == 0
    assert "Chưa đủ dữ liệu khảo sát" in resp.market_insight


def test_orchestrator_dine_in_serpapi_primary() -> None:
    from unittest.mock import patch

    from ca_contracts.catchment_survey import DishItem, StoreCandidate

    mock_candidates = [
        StoreCandidate(
            id="gmap_01",
            name="Cộng Cà Phê",
            distance_km=0.5,
            rating=4.6,
            review_count=120,
            menu_image_urls=["https://lh5.google.com/menu.jpg"],
            dishes=[
                DishItem(name="Cà phê cốt dừa", price=45000, is_bestseller=True, category="Cà phê", source_type="dine_in_ocr"),
            ],
        )
    ]

    with patch(
        "ca_agents.ag_pricing.orchestrator.fetch_gmaps_competitors_serpapi",
        return_value=mock_candidates,
    ) as mock_serp:
        req = CatchmentSurveyRequest(
            latitude=10.776,
            longitude=106.700,
            channel_mode="dine_in_vision",
            category_keyword="cà phê",
            min_reviews=50,
            min_rating=4.0,
        )
        resp = run_catchment_price_survey(req)
        mock_serp.assert_called_once()
        assert resp.total_scanned_stores == 1
        assert resp.validated_stores_count == 1
        assert "Tại Quán (Dine-in)" in resp.market_insight


def test_orchestrator_dine_in_serpapi_fallback_to_camoufox() -> None:
    from unittest.mock import patch

    from ca_agents.clients.serpapi_client import SerpApiQuotaExceededError
    from ca_contracts.catchment_survey import DishItem, StoreCandidate

    mock_camoufox = [
        StoreCandidate(
            id="camou_01",
            name="The Coffee House",
            distance_km=0.8,
            rating=4.5,
            review_count=90,
            dishes=[DishItem(name="Trà đào cam sả", price=40000, category="Trà")],
        )
    ]

    with patch(
        "ca_agents.ag_pricing.orchestrator.fetch_gmaps_competitors_serpapi",
        side_effect=SerpApiQuotaExceededError("Hết quota"),
    ), patch(
        "ca_agents.ag_pricing.orchestrator.scrape_gmaps_menu_images_camoufox",
        return_value=mock_camoufox,
    ) as mock_camou:
        req = CatchmentSurveyRequest(
            latitude=10.776,
            longitude=106.700,
            channel_mode="dine_in_vision",
            category_keyword="cà phê",
            min_reviews=50,
            min_rating=4.0,
        )
        resp = run_catchment_price_survey(req)
        mock_camou.assert_called_once()
        assert resp.total_scanned_stores == 1
