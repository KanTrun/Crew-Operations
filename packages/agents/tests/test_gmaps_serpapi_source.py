"""Unit tests cho Google Maps SerpApi Source."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from ca_agents.clients.serpapi_client import SerpApiQuotaExceededError
from ca_agents.sources.gmaps_serpapi_source import (
    fetch_gmaps_competitors_serpapi,
    fetch_gmaps_menu_photos_serpapi,
    haversine_distance_km,
    parse_gmaps_results_to_candidates,
)


@pytest.fixture
def sample_maps_fixture() -> dict[str, Any]:
    fixture_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "fixtures"
        / "serpapi"
        / "google_maps_coffee_hcm.json"
    )
    with open(fixture_path, encoding="utf-8") as f:
        payload: dict[str, Any] = json.load(f)
        return payload


def test_haversine_distance_km() -> None:
    # Khoảng cách giữa Nhà thờ Đức Bà (10.77978, 106.69902) và Chợ Bến Thành (10.77254, 106.69803) ~0.8km
    dist = haversine_distance_km(10.77978, 106.69902, 10.77254, 106.69803)
    assert 0.7 <= dist <= 0.9


def test_parse_gmaps_results_to_candidates(sample_maps_fixture: dict[str, Any]) -> None:
    origin_lat = 10.7769
    origin_lng = 106.7009

    candidates = parse_gmaps_results_to_candidates(
        payload=sample_maps_fixture,
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        radius_km=3.0,
    )

    assert len(candidates) == 3
    first = candidates[0]
    assert first.name == "Cộng Cà Phê - Lý Tự Trọng"
    assert first.rating == 4.6
    assert first.review_count == 1280
    assert first.distance_km < 1.0
    assert len(first.menu_image_urls) == 1
    assert first.menu_image_urls[0].startswith("https://lh5")


def test_parse_gmaps_results_radius_filter(sample_maps_fixture: dict[str, Any]) -> None:
    # Quán cách ~0.08km và ~0.5km. Nếu đặt bán kính cực nhỏ 0.05km thì sẽ bị lọc hết
    candidates = parse_gmaps_results_to_candidates(
        payload=sample_maps_fixture,
        origin_lat=10.7769,
        origin_lng=106.7009,
        radius_km=0.05,
    )
    assert len(candidates) == 0


def test_fetch_gmaps_competitors_success(sample_maps_fixture: dict[str, Any]) -> None:
    with patch(
        "ca_agents.sources.gmaps_serpapi_source.search_serpapi",
        return_value=sample_maps_fixture,
    ) as mock_search:
        res = fetch_gmaps_competitors_serpapi(
            latitude=10.7769,
            longitude=106.7009,
            keyword="cà phê specialty",
            radius_km=2.0,
        )
        assert len(res) == 3
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args[0][0] == "google_maps"
        assert call_args[0][1]["q"] == "cà phê specialty"
        assert "@10.7769,106.7009,15z" in call_args[0][1]["ll"]


def test_fetch_gmaps_competitors_quota_exceeded() -> None:
    with patch(
        "ca_agents.sources.gmaps_serpapi_source.search_serpapi",
        side_effect=SerpApiQuotaExceededError("Hết quota"),
    ):
        with pytest.raises(SerpApiQuotaExceededError):
            fetch_gmaps_competitors_serpapi(
                latitude=10.7769,
                longitude=106.7009,
                keyword="cà phê",
            )


def test_fetch_gmaps_menu_photos_serpapi() -> None:
    mock_photos_resp = {
        "photos": [
            {"image": "https://lh5.google.com/photo1.jpg"},
            {"image": "https://lh5.google.com/photo2.jpg"},
        ]
    }
    with patch(
        "ca_agents.sources.gmaps_serpapi_source.search_serpapi",
        return_value=mock_photos_resp,
    ):
        urls = fetch_gmaps_menu_photos_serpapi("place_123", max_images=2)
        assert urls == [
            "https://lh5.google.com/photo1.jpg",
            "https://lh5.google.com/photo2.jpg",
        ]


def test_fetch_gmaps_competitors_circuit_open() -> None:
    from ca_agents.clients.serpapi_client import SerpApiCircuitOpenError

    with patch(
        "ca_agents.sources.gmaps_serpapi_source.search_serpapi",
        side_effect=SerpApiCircuitOpenError("Circuit Breaker OPEN"),
    ):
        with pytest.raises(SerpApiCircuitOpenError):
            fetch_gmaps_competitors_serpapi(
                latitude=10.7769,
                longitude=106.7009,
                keyword="cà phê",
            )


def test_fetch_gmaps_reviews_anonymization() -> None:
    from ca_agents.sources.gmaps_serpapi_source import fetch_gmaps_reviews_serpapi

    mock_reviews_resp = {
        "reviews": [
            {
                "user": {"name": "Nguyễn Văn A", "thumbnail": "https://avatar.com/userA.jpg", "link": "https://..."},
                "rating": 5.0,
                "date": "1 ngày trước",
                "snippet": "Cà phê rất đậm đà, quán đẹp và phục vụ chu đáo.",
            },
            {
                "user": {"name": "Trần Thị B", "thumbnail": "https://avatar.com/userB.jpg"},
                "rating": 4.0,
                "date": "3 ngày trước",
                "snippet": "Không gian hơi ồn vào giờ cao điểm, thức uống ngon.",
            },
        ]
    }

    with patch(
        "ca_agents.sources.gmaps_serpapi_source.search_serpapi",
        return_value=mock_reviews_resp,
    ):
        reviews = fetch_gmaps_reviews_serpapi("place_test_456")
        assert len(reviews) == 2
        for r in reviews:
            assert r["anonymized"] is True
            # Tuyệt đối không chứa tên hoặc avatar của người đánh giá (Nghị định 13/2023/NĐ-CP)
            assert "name" not in r
            assert "thumbnail" not in r
            assert "user" not in r
            assert "snippet" in r
            assert "rating" in r


def test_candidate_fields_and_datasource(sample_maps_fixture: dict[str, Any]) -> None:
    candidates = parse_gmaps_results_to_candidates(
        payload=sample_maps_fixture,
        origin_lat=10.7769,
        origin_lng=106.7009,
        radius_km=3.0,
        data_source="serpapi",
    )
    assert len(candidates) > 0
    cand = candidates[0]
    assert cand.data_source == "serpapi"
    assert cand.lat > 0
    assert cand.lng > 0
    assert cand.fetched_at is not None
