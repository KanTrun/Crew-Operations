"""Unit tests cho ShopeeFood SerpApi Source."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from ca_agents.clients.serpapi_client import SerpApiQuotaExceededError
from ca_agents.sources.shopeefood_serpapi_source import (
    _is_shopeefood_related,
    fetch_shopeefood_competitors_serpapi,
    fetch_shopeefood_menu_serpapi,
    haversine_distance_km,
    parse_shopeefood_serpapi_results,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_serpapi_payload() -> dict[str, Any]:
    """Sample SerpApi Google Maps response with ShopeeFood-related results."""
    return {
        "local_results": [
            {
                "position": 1,
                "title": "Cơm Tấm Sài Gòn - ShopeeFood",
                "rating": 4.5,
                "reviews": 1200,
                "address": "123 Nguyễn Huệ, Quận 1",
                "gps_coordinates": {
                    "latitude": 10.7769,
                    "longitude": 106.7009,
                },
                "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                "type": "Restaurant",
                "description": "Quán cơm tấm ngon, giao hàng ShopeeFood",
                "extensions": ["Delivery", "ShopeeFood Partner"],
                "thumbnail": "https://example.com/thumb1.jpg",
            },
            {
                "position": 2,
                "title": "Phở Hà Nội",
                "rating": 4.2,
                "reviews": 800,
                "address": "456 Lê Lợi, Quận 1",
                "gps_coordinates": {
                    "latitude": 10.7731,
                    "longitude": 106.7031,
                },
                "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY5",
                "type": "Restaurant",
                "description": "Phở bò truyền thống",
                "extensions": ["Delivery"],
            },
            {
                "position": 3,
                "title": "Coffee House",
                "rating": 4.0,
                "reviews": 500,
                "address": "789 Đồng Khởi, Quận 1",
                "gps_coordinates": {
                    "latitude": 10.7791,
                    "longitude": 106.7031,
                },
                "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY6",
                "type": "Coffee shop",
                "description": "Quán cà phê yên tĩnh",
                "extensions": [],
            },
        ]
    }


@pytest.fixture
def sample_shopeefood_only_payload() -> dict[str, Any]:
    """Sample payload with only ShopeeFood-related results."""
    return {
        "local_results": [
            {
                "position": 1,
                "title": "ShopeeFood Partner - Bún Bò Huế",
                "rating": 4.3,
                "reviews": 600,
                "address": "111 Hai Bà Trưng, Quận 1",
                "gps_coordinates": {
                    "latitude": 10.7769,
                    "longitude": 106.7009,
                },
                "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY7",
                "type": "Food delivery",
                "description": "Bún bò Huế chính gốc",
                "extensions": ["ShopeeFood", "Delivery"],
            },
        ]
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestHaversineDistance:
    """Test haversine distance calculation."""

    def test_same_point_returns_zero(self) -> None:
        assert haversine_distance_km(10.7769, 106.7009, 10.7769, 106.7009) == 0.0

    def test_known_distance(self) -> None:
        # Khoảng cách giữa 2 điểm ở TP.HCM
        dist = haversine_distance_km(10.7769, 106.7009, 10.7731, 106.7031)
        assert 0.4 < dist < 0.6  # ~0.5km

    def test_symmetry(self) -> None:
        d1 = haversine_distance_km(10.7769, 106.7009, 10.7731, 106.7031)
        d2 = haversine_distance_km(10.7731, 106.7031, 10.7769, 106.7009)
        assert d1 == d2


class TestIsShopeefoodRelated:
    """Test ShopeeFood detection logic."""

    def test_shopeefood_in_name(self) -> None:
        item = {"title": "Cơm Tấm - ShopeeFood"}
        assert _is_shopeefood_related(item) is True

    def test_shopee_food_in_name(self) -> None:
        item = {"title": "Quán Phở Shopee Food"}
        assert _is_shopeefood_related(item) is True

    def test_shopeefood_in_description(self) -> None:
        item = {"title": "Quán Ăn", "description": "Giao hàng ShopeeFood"}
        assert _is_shopeefood_related(item) is True

    def test_delivery_in_type(self) -> None:
        item = {"title": "Quán Ăn", "type": "Food delivery"}
        assert _is_shopeefood_related(item) is True

    def test_delivery_in_extensions(self) -> None:
        item = {"title": "Quán Ăn", "extensions": ["Delivery", "Fast food"]}
        assert _is_shopeefood_related(item) is True

    def test_shopeefood_in_extensions(self) -> None:
        item = {"title": "Quán Ăn", "extensions": ["ShopeeFood Partner"]}
        assert _is_shopeefood_related(item) is True

    def test_not_shopeefood_related(self) -> None:
        item = {"title": "Coffee House", "type": "Coffee shop", "extensions": []}
        assert _is_shopeefood_related(item) is False

    def test_empty_item(self) -> None:
        assert _is_shopeefood_related({}) is False


class TestParseShopeefoodSerpapiResults:
    """Test parsing SerpApi results to StoreCandidate."""

    def test_parse_filters_shopeefood_only(
        self, sample_serpapi_payload: dict[str, Any]
    ) -> None:
        """Chỉ lấy các quán liên quan đến ShopeeFood."""
        results = parse_shopeefood_serpapi_results(
            sample_serpapi_payload,
            origin_lat=10.7769,
            origin_lng=106.7009,
            radius_km=5.0,
        )
        # Chỉ có 2 quán liên quan đến ShopeeFood (quán 1 và 2)
        assert len(results) == 2
        names = {r.name for r in results}
        assert "Cơm Tấm Sài Gòn - ShopeeFood" in names
        assert "Phở Hà Nội" in names
        assert "Coffee House" not in names

    def test_parse_respects_radius(
        self, sample_serpapi_payload: dict[str, Any]
    ) -> None:
        """Lọc theo bán kính."""
        results = parse_shopeefood_serpapi_results(
            sample_serpapi_payload,
            origin_lat=10.7769,
            origin_lng=106.7009,
            radius_km=0.1,  # Bán kính rất nhỏ
        )
        # Chỉ quán ở cùng tọa độ mới nằm trong bán kính
        assert len(results) <= 2

    def test_parse_extracts_rating_and_reviews(
        self, sample_serpapi_payload: dict[str, Any]
    ) -> None:
        """Trích xuất đúng rating và review count."""
        results = parse_shopeefood_serpapi_results(
            sample_serpapi_payload,
            origin_lat=10.7769,
            origin_lng=106.7009,
            radius_km=5.0,
        )
        # Tìm quán "Cơm Tấm Sài Gòn - ShopeeFood"
        com_tam = next(r for r in results if "Cơm Tấm" in r.name)
        assert com_tam.rating == 4.5
        assert com_tam.review_count == 1200

    def test_parse_extracts_metadata(
        self, sample_serpapi_payload: dict[str, Any]
    ) -> None:
        """Trích xuất thông tin ShopeeFood vào sold_count_text."""
        results = parse_shopeefood_serpapi_results(
            sample_serpapi_payload,
            origin_lat=10.7769,
            origin_lng=106.7009,
            radius_km=5.0,
        )
        com_tam = next(r for r in results if "Cơm Tấm" in r.name)
        assert "shopeefood" in com_tam.sold_count_text
        assert "delivery" in com_tam.sold_count_text

    def test_parse_empty_payload(self) -> None:
        """Xử lý payload rỗng."""
        results = parse_shopeefood_serpapi_results(
            {},
            origin_lat=10.7769,
            origin_lng=106.7009,
        )
        assert results == []

    def test_parse_invalid_payload(self) -> None:
        """Xử lý payload không hợp lệ."""
        results = parse_shopeefood_serpapi_results(
            {"local_results": "invalid"},
            origin_lat=10.7769,
            origin_lng=106.7009,
        )
        assert results == []


class TestFetchShopeefoodCompetitorsSerpapi:
    """Test fetching ShopeeFood competitors via SerpApi."""

    @patch("ca_agents.sources.shopeefood_serpapi_source.search_serpapi")
    def test_fetch_success(self, mock_search: MagicMock) -> None:
        """Thành công khi gọi SerpApi."""
        mock_search.return_value = {
            "local_results": [
                {
                    "title": "ShopeeFood Restaurant",
                    "rating": 4.5,
                    "reviews": 100,
                    "address": "123 Test",
                    "gps_coordinates": {"latitude": 10.7769, "longitude": 106.7009},
                    "place_id": "test123",
                    "type": "Restaurant",
                    "extensions": ["ShopeeFood"],
                }
            ]
        }
        
        results = fetch_shopeefood_competitors_serpapi(
            latitude=10.7769,
            longitude=106.7009,
            keyword="cơm tấm",
            radius_km=5.0,
        )
        
        assert len(results) == 1
        assert results[0].name == "ShopeeFood Restaurant"
        assert mock_search.call_count == 3  # 3 queries

    @patch("ca_agents.sources.shopeefood_serpapi_source.search_serpapi")
    def test_fetch_deduplicates_results(self, mock_search: MagicMock) -> None:
        """Loại trùng kết quả từ nhiều query."""
        mock_search.return_value = {
            "local_results": [
                {
                    "title": "ShopeeFood Restaurant",
                    "rating": 4.5,
                    "reviews": 100,
                    "address": "123 Test",
                    "gps_coordinates": {"latitude": 10.7769, "longitude": 106.7009},
                    "place_id": "test123",
                    "type": "Restaurant",
                    "extensions": ["ShopeeFood"],
                }
            ]
        }
        
        results = fetch_shopeefood_competitors_serpapi(
            latitude=10.7769,
            longitude=106.7009,
            keyword="cơm tấm",
            radius_km=5.0,
        )
        
        # Chỉ có 1 kết quả vì cả 3 query trả về cùng 1 quán
        assert len(results) == 1

    @patch("ca_agents.sources.shopeefood_serpapi_source.search_serpapi")
    def test_fetch_quota_exceeded(self, mock_search: MagicMock) -> None:
        """Ném exception khi hết quota."""
        mock_search.side_effect = SerpApiQuotaExceededError("Quota exceeded")
        
        with pytest.raises(SerpApiQuotaExceededError):
            fetch_shopeefood_competitors_serpapi(
                latitude=10.7769,
                longitude=106.7009,
                keyword="cơm tấm",
            )

    @patch("ca_agents.sources.shopeefood_serpapi_source.search_serpapi")
    def test_fetch_api_error_returns_empty(self, mock_search: MagicMock) -> None:
        """Trả về danh sách rỗng khi có lỗi API chung."""
        mock_search.side_effect = Exception("API Error")
        
        results = fetch_shopeefood_competitors_serpapi(
            latitude=10.7769,
            longitude=106.7009,
            keyword="cơm tấm",
        )
        
        # Hàm catch Exception và continue, nên trả về danh sách rỗng
        assert results == []


class TestFetchShopeefoodMenuSerpapi:
    """Test fetching ShopeeFood menu photos via SerpApi."""

    @patch("ca_agents.sources.shopeefood_serpapi_source.search_serpapi")
    def test_fetch_menu_photos_success(self, mock_search: MagicMock) -> None:
        """Thành công khi lấy ảnh menu."""
        mock_search.return_value = {
            "photos": [
                {
                    "title": "Menu chính",
                    "image": "https://example.com/menu1.jpg",
                    "thumbnail": "https://example.com/thumb1.jpg",
                },
                {
                    "title": "Ảnh quán",
                    "image": "https://example.com/photo1.jpg",
                },
            ]
        }
        
        results = fetch_shopeefood_menu_serpapi(place_id="test123")
        
        assert len(results) == 1
        assert results[0] == "https://example.com/menu1.jpg"

    @patch("ca_agents.sources.shopeefood_serpapi_source.search_serpapi")
    def test_fetch_menu_photos_no_menu(self, mock_search: MagicMock) -> None:
        """Trả về ảnh đầu tiên nếu không tìm thấy ảnh menu."""
        mock_search.return_value = {
            "photos": [
                {
                    "title": "Ảnh quán",
                    "image": "https://example.com/photo1.jpg",
                },
            ]
        }
        
        results = fetch_shopeefood_menu_serpapi(place_id="test123")
        
        assert len(results) == 1
        assert results[0] == "https://example.com/photo1.jpg"

    @patch("ca_agents.sources.shopeefood_serpapi_source.search_serpapi")
    def test_fetch_menu_photos_empty(self, mock_search: MagicMock) -> None:
        """Trả về danh sách rỗng khi không có ảnh."""
        mock_search.return_value = {"photos": []}
        
        results = fetch_shopeefood_menu_serpapi(place_id="test123")
        
        assert results == []

    @patch("ca_agents.sources.shopeefood_serpapi_source.search_serpapi")
    def test_fetch_menu_photos_quota_exceeded(self, mock_search: MagicMock) -> None:
        """Ném exception khi hết quota."""
        mock_search.side_effect = SerpApiQuotaExceededError("Quota exceeded")
        
        with pytest.raises(SerpApiQuotaExceededError):
            fetch_shopeefood_menu_serpapi(place_id="test123")