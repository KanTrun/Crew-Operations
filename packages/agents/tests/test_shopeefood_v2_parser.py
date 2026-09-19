# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit test cho ShopeeFood v2 parser — tách original/effective price.

Test coverage:
- Tách giá gốc và giá khuyến mãi từ JSON
- Suy ngược giá gốc từ discount percentage
- Xử lý trường hợp chỉ có 1 giá (không khuyến mãi)
- Log warning khi không tách được giá
- Chuẩn hoá tên món
- Phát hiện combo
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from ca_agents.sources.shopeefood_v2_parser import (
    extract_menu_items_v2,
    extract_stores_menu_items_v2,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "shopeefood" / "shopeefood_sample_v2.json"


class TestExtractMenuItemsV2:
    """Test suite cho extract_menu_items_v2()."""

    def test_separate_original_and_effective_price(self) -> None:
        """Tách đúng giá gốc và giá khuyến mãi."""
        payload = {
            "dishes": [
                {
                    "name": "Cơm tấm sườn bì chả",
                    "original_price": 45000,
                    "sale_price": 36000,
                    "discount_pct": "20%",
                }
            ]
        }
        items = extract_menu_items_v2(payload)
        assert len(items) == 1
        item = items[0]
        assert item.original_price_vnd == 45000
        assert item.effective_price_vnd == 36000
        assert item.is_promotional is True
        assert item.confidence == "high"

    def test_single_price_no_promotion(self) -> None:
        """Chỉ có 1 giá → original = effective, không khuyến mãi."""
        payload = {
            "dishes": [
                {
                    "name": "Phở bò tái",
                    "price": 55000,
                }
            ]
        }
        items = extract_menu_items_v2(payload)
        assert len(items) == 1
        item = items[0]
        assert item.original_price_vnd == 55000
        assert item.effective_price_vnd == 55000
        assert item.is_promotional is False
        assert item.confidence == "medium"

    def test_derive_original_from_discount_pct(self) -> None:
        """Suy ngược giá gốc từ effective + discount_pct."""
        payload = {
            "dishes": [
                {
                    "name": "Bạc xỉu đá",
                    "price": 32300,
                    "discount_pct": "15%",
                }
            ]
        }
        items = extract_menu_items_v2(payload)
        assert len(items) == 1
        item = items[0]
        # 32300 / (1 - 0.15) = 38000
        assert item.original_price_vnd == 38000
        assert item.effective_price_vnd == 32300
        assert item.is_promotional is True
        assert item.is_fallback_derived is True

    def test_string_price_formats(self) -> None:
        """Xử lý đúng các định dạng giá dạng string."""
        payload = {
            "dishes": [
                {
                    "name": "Cơm tấm bì",
                    "list_price": "35.000đ",
                    "discount_price": "28.000đ",
                }
            ]
        }
        items = extract_menu_items_v2(payload)
        assert len(items) == 1
        item = items[0]
        assert item.original_price_vnd == 35000
        assert item.effective_price_vnd == 28000
        assert item.is_promotional is True

    def test_detect_combo(self) -> None:
        """Phát hiện đúng combo/set món."""
        payload = {
            "dishes": [
                {
                    "name": "Combo trà sữa + topping",
                    "price": 50000,
                    "is_combo": True,
                }
            ]
        }
        items = extract_menu_items_v2(payload)
        assert len(items) == 1
        assert items[0].is_combo is True

    def test_detect_combo_from_name(self) -> None:
        """Phát hiện combo từ tên món (chứa 'combo' hoặc 'set')."""
        payload = {
            "dishes": [
                {
                    "name": "Set cơm trưa văn phòng",
                    "price": 60000,
                }
            ]
        }
        items = extract_menu_items_v2(payload)
        assert len(items) == 1
        assert items[0].is_combo is True

    def test_normalize_dish_name(self) -> None:
        """Chuẩn hoá tên món đúng."""
        payload = {
            "dishes": [
                {
                    "name": "Cơm tấm sườn nướng bì chả",
                    "price": 45000,
                }
            ]
        }
        items = extract_menu_items_v2(payload)
        assert len(items) == 1
        item = items[0]
        assert item.item_name_raw == "Cơm tấm sườn nướng bì chả"
        # "nướng" bị loại, "tấm" bị loại
        assert "nuong" not in item.item_name_normalized
        assert "tam" not in item.item_name_normalized
        assert "com" in item.item_name_normalized
        assert "suon" in item.item_name_normalized

    def test_portion_note(self) -> None:
        """Ghi nhận portion/size note."""
        payload = {
            "dishes": [
                {
                    "name": "Trà sữa truyền thống",
                    "price": 45000,
                    "size": "M",
                }
            ]
        }
        items = extract_menu_items_v2(payload)
        assert len(items) == 1
        assert items[0].portion_note == "M"

    def test_empty_payload(self) -> None:
        """Payload rỗng trả về list rỗng."""
        assert extract_menu_items_v2({}) == []
        assert extract_menu_items_v2({"dishes": []}) == []

    def test_invalid_dish_data(self) -> None:
        """Bỏ qua dish data không hợp lệ."""
        payload = {
            "dishes": [
                {"name": "", "price": 30000},  # tên rỗng
                {"name": "Phở bò", "price": 0},  # giá = 0
                {"name": "Bún riêu", "price": 40000},  # hợp lệ
            ]
        }
        items = extract_menu_items_v2(payload)
        assert len(items) == 1
        assert items[0].item_name_raw == "Bún riêu"

    def test_from_fixture_file(self) -> None:
        """Parse đúng từ fixture file."""
        if not FIXTURE_PATH.exists():
            pytest.skip(f"Fixture not found: {FIXTURE_PATH}")

        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        items = extract_menu_items_v2(payload["reply"]["restaurants"][0])

        # Quán đầu tiên có 3 món
        assert len(items) == 3

        # Món 1: có khuyến mãi 20%
        item1 = items[0]
        assert item1.item_name_raw == "Cơm tấm sườn bì chả"
        assert item1.original_price_vnd == 45000
        assert item1.effective_price_vnd == 36000
        assert item1.is_promotional is True

        # Món 2: không khuyến mãi
        item2 = items[1]
        assert item2.item_name_raw == "Cơm tấm sườn nướng"
        assert item2.original_price_vnd == 40000
        assert item2.effective_price_vnd == 40000
        assert item2.is_promotional is False

        # Món 3: có khuyến mãi với giá string
        item3 = items[2]
        assert item3.item_name_raw == "Cơm tấm bì"
        assert item3.original_price_vnd == 35000
        assert item3.effective_price_vnd == 28000
        assert item3.is_promotional is True


class TestExtractStoresMenuItemsV2:
    """Test suite cho extract_stores_menu_items_v2()."""

    def test_extract_by_store_id(self) -> None:
        """Trích xuất menu items theo từng quán."""
        payload = {
            "restaurants": [
                {
                    "id": "store_001",
                    "name": "Quán A",
                    "dishes": [
                        {"name": "Cơm sườn", "price": 40000},
                        {"name": "Cơm gà", "price": 45000},
                    ],
                },
                {
                    "id": "store_002",
                    "name": "Quán B",
                    "dishes": [
                        {"name": "Phở bò", "price": 55000},
                    ],
                },
            ]
        }
        result = extract_stores_menu_items_v2(payload)
        assert len(result) == 2
        assert "store_001" in result
        assert "store_002" in result
        assert len(result["store_001"]) == 2
        assert len(result["store_002"]) == 1

    def test_skip_stores_without_dishes(self) -> None:
        """Bỏ qua quán không có món."""
        payload = {
            "restaurants": [
                {
                    "id": "store_001",
                    "name": "Quán A",
                    "dishes": [],
                },
                {
                    "id": "store_002",
                    "name": "Quán B",
                    "dishes": [{"name": "Phở bò", "price": 55000}],
                },
            ]
        }
        result = extract_stores_menu_items_v2(payload)
        assert len(result) == 1
        assert "store_002" in result

    def test_from_fixture_file(self) -> None:
        """Parse đúng từ fixture file."""
        if not FIXTURE_PATH.exists():
            pytest.skip(f"Fixture not found: {FIXTURE_PATH}")

        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        result = extract_stores_menu_items_v2(payload)

        # Fixture có 5 quán
        assert len(result) == 5

        # Kiểm tra quán đầu tiên
        store_001_items = result["shopeefood_store_001"]
        assert len(store_001_items) == 3
        assert store_001_items[0].item_name_raw == "Cơm tấm sườn bì chả"
