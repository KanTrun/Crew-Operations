"""Unit tests cho vision_menu_extractor.py (Phase 2 rewrite).

Test coverage:
- Parse JSON response từ Vision AI
- Retry logic khi schema validation fail
- NEEDS_REVIEW queue cho món không đọc được giá
- Backward-compat wrapper extract_dishes_from_menu_image
- Validation giá (min/max bounds)
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from ca_agents.ag_pricing.vision_menu_extractor import (
    _parse_vision_response,
    _validate_price,
    extract_dishes_from_menu_image,
    extract_menu_from_image,
)
from ca_contracts.catchment_survey_v2 import ChannelMode, MenuItemPrice


class TestValidatePrice:
    """Test _validate_price() helper."""

    def test_valid_price(self) -> None:
        assert _validate_price(35000) == 35000
        assert _validate_price("42000") == 42000

    def test_price_below_min(self) -> None:
        assert _validate_price(1000) is None
        assert _validate_price(4999) is None

    def test_price_above_max(self) -> None:
        assert _validate_price(6_000_000) is None
        assert _validate_price(10_000_000) is None

    def test_invalid_input(self) -> None:
        assert _validate_price(None) is None
        assert _validate_price("abc") is None
        assert _validate_price([]) is None


class TestParseVisionResponse:
    """Test _parse_vision_response() JSON parsing."""

    def test_valid_menu_with_prices(self) -> None:
        json_text = """
        {
            "dishes": [
                {
                    "name": "Cơm tấm sườn bì chả",
                    "original_price_vnd": 45000,
                    "effective_price_vnd": 36000,
                    "is_promotional": true,
                    "confidence": "high"
                },
                {
                    "name": "Phở bò tái",
                    "original_price_vnd": 55000,
                    "effective_price_vnd": 55000,
                    "is_promotional": false,
                    "confidence": "medium"
                }
            ],
            "is_valid_menu": true,
            "overall_confidence": 0.92
        }
        """
        items, review, is_valid = _parse_vision_response(
            json_text, source_channel=ChannelMode.DINE_IN_VISION
        )
        assert is_valid is True
        assert len(items) == 2
        assert len(review) == 0

        item1 = items[0]
        assert item1.item_name_raw == "Cơm tấm sườn bì chả"
        assert item1.original_price_vnd == 45000
        assert item1.effective_price_vnd == 36000
        assert item1.is_promotional is True
        assert item1.confidence == "high"

        item2 = items[1]
        assert item2.item_name_raw == "Phở bò tái"
        assert item2.original_price_vnd == 55000
        assert item2.effective_price_vnd == 55000
        assert item2.is_promotional is False

    def test_unreadable_price_goes_to_review(self) -> None:
        json_text = """
        {
            "dishes": [
                {
                    "name": "Cơm tấm",
                    "original_price_vnd": null,
                    "effective_price_vnd": null,
                    "confidence": "low",
                    "raw_text": "Cơm tấm (giá mờ)"
                }
            ],
            "is_valid_menu": true
        }
        """
        items, review, is_valid = _parse_vision_response(
            json_text, source_channel=ChannelMode.DINE_IN_VISION
        )
        assert is_valid is True
        assert len(items) == 0
        assert len(review) == 1
        assert review[0]["name"] == "Cơm tấm"
        assert review[0]["reason"] == "price_unreadable"

    def test_not_a_menu_image(self) -> None:
        json_text = """
        {
            "dishes": [],
            "is_valid_menu": false
        }
        """
        items, review, is_valid = _parse_vision_response(
            json_text, source_channel=ChannelMode.DINE_IN_VISION
        )
        assert is_valid is False
        assert len(items) == 0
        assert len(review) == 0

    def test_fallback_single_price(self) -> None:
        json_text = """
        {
            "dishes": [
                {
                    "name": "Bún riêu",
                    "original_price_vnd": 40000,
                    "effective_price_vnd": null
                }
            ],
            "is_valid_menu": true
        }
        """
        items, review, is_valid = _parse_vision_response(
            json_text, source_channel=ChannelMode.DINE_IN_VISION
        )
        assert is_valid is True
        assert len(items) == 1
        item = items[0]
        assert item.original_price_vnd == 40000
        assert item.effective_price_vnd == 40000

    def test_combo_detection(self) -> None:
        json_text = """
        {
            "dishes": [
                {
                    "name": "Combo trà sữa + topping",
                    "original_price_vnd": 60000,
                    "effective_price_vnd": 50000,
                    "is_combo": true
                }
            ],
            "is_valid_menu": true
        }
        """
        items, review, is_valid = _parse_vision_response(
            json_text, source_channel=ChannelMode.DINE_IN_VISION
        )
        assert is_valid is True
        assert len(items) == 1
        assert items[0].is_combo is True

    def test_invalid_json(self) -> None:
        items, review, is_valid = _parse_vision_response(
            "not json", source_channel=ChannelMode.DINE_IN_VISION
        )
        assert is_valid is False
        assert len(items) == 0

    def test_price_out_of_bounds_filtered(self) -> None:
        json_text = """
        {
            "dishes": [
                {
                    "name": "Món rẻ",
                    "original_price_vnd": 1000,
                    "effective_price_vnd": 1000
                },
                {
                    "name": "Món đắt",
                    "original_price_vnd": 10000000,
                    "effective_price_vnd": 10000000
                },
                {
                    "name": "Món hợp lệ",
                    "original_price_vnd": 50000,
                    "effective_price_vnd": 50000
                }
            ],
            "is_valid_menu": true
        }
        """
        items, review, is_valid = _parse_vision_response(
            json_text, source_channel=ChannelMode.DINE_IN_VISION
        )
        assert is_valid is True
        assert len(items) == 1
        assert items[0].item_name_raw == "Món hợp lệ"


class TestExtractMenuFromImage:
    """Test extract_menu_from_image() with mocked LLM."""

    def test_empty_image_bytes(self) -> None:
        result = extract_menu_from_image(
            b"", store_id="test_store", core_keyword="com_tam"
        )
        assert result.ok is False
        assert result.error == "image_too_small_or_empty"

    def test_successful_extraction(self) -> None:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = """
        {
            "dishes": [
                {
                    "name": "Cơm tấm sườn",
                    "original_price_vnd": 45000,
                    "effective_price_vnd": 45000,
                    "confidence": "high"
                }
            ],
            "is_valid_menu": true
        }
        """
        mock_response.provider = "gemini"

        with patch("ca_agents.ag_pricing.vision_menu_extractor.complete", return_value=mock_response):
            result = extract_menu_from_image(
                b"fake_image_bytes" * 100,
                store_id="store_001",
                image_url="https://example.com/menu.jpg",
                core_keyword="com_tam",
                photo_source="menu_tab",
                photo_taken_recency_days=5,
            )

        assert result.ok is True
        assert result.snapshot is not None
        assert result.snapshot.store_id == "store_001"
        assert result.snapshot.image_url == "https://example.com/menu.jpg"
        assert result.snapshot.photo_source == "menu_tab"
        assert result.snapshot.photo_taken_recency_days == 5
        assert len(result.snapshot.extracted_items) == 1
        assert result.retries_used == 0

    def test_retry_on_parse_failure(self) -> None:
        # First attempt: invalid JSON
        mock_response_1 = Mock()
        mock_response_1.ok = True
        mock_response_1.text = "invalid json"
        mock_response_1.provider = "gemini"

        # Second attempt: valid JSON
        mock_response_2 = Mock()
        mock_response_2.ok = True
        mock_response_2.text = """
        {
            "dishes": [
                {
                    "name": "Phở bò",
                    "original_price_vnd": 55000,
                    "effective_price_vnd": 55000
                }
            ],
            "is_valid_menu": true
        }
        """
        mock_response_2.provider = "gemini"

        with patch(
            "ca_agents.ag_pricing.vision_menu_extractor.complete",
            side_effect=[mock_response_1, mock_response_2],
        ):
            result = extract_menu_from_image(
                b"fake_image_bytes" * 100,
                store_id="store_002",
                core_keyword="pho",
            )

        assert result.ok is True
        assert result.snapshot is not None
        assert len(result.snapshot.extracted_items) == 1
        assert result.retries_used == 1

    def test_max_retries_exhausted(self) -> None:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = "invalid json"
        mock_response.provider = "gemini"

        with patch(
            "ca_agents.ag_pricing.vision_menu_extractor.complete",
            return_value=mock_response,
        ):
            result = extract_menu_from_image(
                b"fake_image_bytes" * 100,
                store_id="store_003",
                core_keyword="bun",
            )

        assert result.ok is False
        assert result.error == "parse_failed_or_not_menu"
        assert result.retries_used == 2  # _MAX_RETRIES = 2

    def test_llm_call_error(self) -> None:
        mock_response = Mock()
        mock_response.ok = False
        mock_response.text = ""
        mock_response.provider = "gemini"
        mock_response.reason = "quota_exceeded"

        with patch(
            "ca_agents.ag_pricing.vision_menu_extractor.complete",
            return_value=mock_response,
        ):
            result = extract_menu_from_image(
                b"fake_image_bytes" * 100,
                store_id="store_004",
                core_keyword="ca_phe",
            )

        assert result.ok is False
        assert "llm_not_ok" in result.error

    def test_needs_review_queue_populated(self) -> None:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = """
        {
            "dishes": [
                {
                    "name": "Cơm tấm",
                    "original_price_vnd": 45000,
                    "effective_price_vnd": 45000
                },
                {
                    "name": "Canh chua",
                    "original_price_vnd": null,
                    "effective_price_vnd": null,
                    "raw_text": "Canh chua (giá mờ)"
                }
            ],
            "is_valid_menu": true
        }
        """
        mock_response.provider = "gemini"

        with patch(
            "ca_agents.ag_pricing.vision_menu_extractor.complete",
            return_value=mock_response,
        ):
            result = extract_menu_from_image(
                b"fake_image_bytes" * 100,
                store_id="store_005",
                core_keyword="com_tam",
            )

        assert result.ok is True
        assert result.snapshot is not None
        assert len(result.snapshot.extracted_items) == 1
        assert len(result.needs_review) == 1
        assert result.needs_review[0]["name"] == "Canh chua"
        assert result.needs_review[0]["reason"] == "price_unreadable"


class TestBackwardCompatWrapper:
    """Test extract_dishes_from_menu_image() backward-compat wrapper."""

    def test_returns_list_of_menu_item_price(self) -> None:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = """
        {
            "dishes": [
                {
                    "name": "Bún bò Huế",
                    "original_price_vnd": 50000,
                    "effective_price_vnd": 50000
                }
            ],
            "is_valid_menu": true
        }
        """
        mock_response.provider = "gemini"

        with patch(
            "ca_agents.ag_pricing.vision_menu_extractor.complete",
            return_value=mock_response,
        ):
            items = extract_dishes_from_menu_image(
                b"fake_image_bytes" * 100,
                core_keyword="bun_bo",
            )

        assert len(items) == 1
        assert isinstance(items[0], MenuItemPrice)
        assert items[0].item_name_raw == "Bún bò Huế"
        assert items[0].original_price_vnd == 50000

    def test_returns_empty_list_on_failure(self) -> None:
        mock_response = Mock()
        mock_response.ok = False
        mock_response.text = ""
        mock_response.provider = "gemini"
        mock_response.reason = "error"

        with patch(
            "ca_agents.ag_pricing.vision_menu_extractor.complete",
            return_value=mock_response,
        ):
            items = extract_dishes_from_menu_image(
                b"fake_image_bytes" * 100,
                core_keyword="test",
            )

        assert items == []
