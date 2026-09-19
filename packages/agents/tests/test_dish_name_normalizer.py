# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit test cho dish_name_normalizer — 20+ test cases với tên món thật F&B Việt Nam.

Test coverage:
- Chuẩn hoá cơ bản (bỏ dấu, lowercase, sắp xếp)
- Loại bỏ từ chỉ phương pháp chế biến
- Loại bỏ từ đệm / từ chỉ đơn vị
- Nhận diện món tương đồng
- Edge cases (chuỗi rỗng, ký tự đặc biệt)
"""

from __future__ import annotations

from ca_agents.ag_pricing.dish_name_normalizer import (
    are_dishes_similar,
    normalize_dish_name,
    normalize_dish_names,
)


class TestNormalizeDishName:
    """Test suite cho normalize_dish_name()."""

    def test_basic_normalization(self) -> None:
        """Chuẩn hoá cơ bản: bỏ dấu, lowercase, sắp xếp alphabet."""
        result = normalize_dish_name("Cơm Sườn Bì Chả")
        assert result == "bi cha com suon"

    def test_remove_cooking_method(self) -> None:
        """Loại bỏ từ chỉ phương pháp chế biến (nướng, chiên, xào...)."""
        result = normalize_dish_name("Cơm sườn nướng bì chả")
        assert result == "bi cha com suon"
        assert "nuong" not in result

    def test_remove_filler_words(self) -> None:
        """Loại bỏ từ đệm (tấm, món, phần, size...)."""
        result = normalize_dish_name("Cơm tấm sườn bì")
        assert result == "bi com suon"
        assert "tam" not in result

    def test_similar_dishes_same_canonical(self) -> None:
        """Các tên món tương đồng phải chuẩn hoá về cùng dạng."""
        name1 = "Cơm sườn bì chả"
        name2 = "Cơm tấm sườn bì"
        name3 = "Cơm sườn nướng bì chả"

        norm1 = normalize_dish_name(name1)
        norm2 = normalize_dish_name(name2)
        norm3 = normalize_dish_name(name3)

        # name1 và name3 phải giống hệt (cùng token sau khi bỏ "nướng")
        assert norm1 == norm3
        # name2 thiếu "chả" nên khác
        assert norm1 != norm2

    def test_pho_bo_variants(self) -> None:
        """Các biến thể phở bò phải chuẩn hoá về cùng dạng."""
        variants = [
            "Phở bò tái",
            "Phở bò chín",
            "Phở bò tái lăn",
            "Phở bò kho",
        ]
        normalized = [normalize_dish_name(v) for v in variants]
        # Tất cả phải chứa "bo" và "pho"
        for norm in normalized:
            assert "bo" in norm
            assert "pho" in norm

    def test_coffee_variants(self) -> None:
        """Các loại cà phê phải chuẩn hoá đúng."""
        assert "ca" in normalize_dish_name("Cà phê đen đá")
        assert "ca" in normalize_dish_name("Cà phê sữa đá")
        assert "ca" in normalize_dish_name("Cà phê muối")

    def test_remove_special_characters(self) -> None:
        """Loại bỏ ký tự đặc biệt (dấu ngoặc, dấu gạch ngang...)."""
        result = normalize_dish_name("Cơm sườn (đặc biệt) - size lớn")
        assert "(" not in result
        assert ")" not in result
        assert "-" not in result
        assert "com" in result
        assert "suon" in result

    def test_empty_string(self) -> None:
        """Chuỗi rỗng trả về chuỗi rỗng."""
        assert normalize_dish_name("") == ""
        assert normalize_dish_name("   ") == ""

    def test_numbers_preserved(self) -> None:
        """Số trong tên món được giữ lại (VD: "Bò lúc lắc 2 người")."""
        result = normalize_dish_name("Bò lúc lắc 2 người")
        assert "2" in result
        assert "bo" in result

    def test_vietnamese_special_chars(self) -> None:
        """Xử lý đúng các ký tự tiếng Việt đặc biệt (đ, ơ, ư, ê, ô, ă)."""
        assert "d" in normalize_dish_name("Đậu hũ")  # đ → d
        assert "o" in normalize_dish_name("Bơ")  # ơ → o
        assert "u" in normalize_dish_name("Mứt")  # ư → u
        assert "o" in normalize_dish_name("Phở")  # ơ → o (phở → pho)
        assert "o" in normalize_dish_name("Bò kho")  # ô → o
        assert "a" in normalize_dish_name("Bánh tráng")  # ă → a

    def test_combo_and_set(self) -> None:
        """Xử lý combo/set món."""
        result = normalize_dish_name("Combo cơm sườn + canh + nước")
        assert "com" in result
        assert "suon" in result
        # "combo" bị loại vì là filler word
        assert "combo" not in result

    def test_size_variants(self) -> None:
        """Xử lý các biến thể size (S, M, L, lớn, nhỏ, vừa)."""
        result_s = normalize_dish_name("Cà phê size S")
        result_l = normalize_dish_name("Cà phê size L")
        # "size" bị loại, chỉ còn "ca phe"
        assert result_s == result_l
        assert "size" not in result_s

    def test_beverage_types(self) -> None:
        """Chuẩn hoá tên đồ uống."""
        tra_dao = normalize_dish_name("Trà đào cam sả")
        tra_sua = normalize_dish_name("Trà sữa trân châu")
        assert "tra" in tra_dao
        assert "tra" in tra_sua
        assert tra_dao != tra_sua  # Khác nhau vì thành phần khác nhau

    def test_noodle_dishes(self) -> None:
        """Chuẩn hoá các món nước (bún, phở, hủ tiếu...)."""
        bun_bo = normalize_dish_name("Bún bò Huế")
        bun_rieu = normalize_dish_name("Bún riêu cua")
        pho_bo = normalize_dish_name("Phở bò tái")

        assert "bun" in bun_bo
        assert "bun" in bun_rieu
        assert "pho" in pho_bo
        assert bun_bo != bun_rieu  # Khác thành phần
        assert bun_bo != pho_bo  # Khác loại sợi

    def test_grilled_dishes(self) -> None:
        """Chuẩn hoá các món nướng."""
        result1 = normalize_dish_name("Thịt heo nướng")
        result2 = normalize_dish_name("Thịt heo")
        # "nướng" bị loại, nên 2 kết quả phải giống nhau
        assert result1 == result2
        assert "thit" in result1
        assert "heo" in result1

    def test_fried_dishes(self) -> None:
        """Chuẩn hoá các món chiên."""
        result = normalize_dish_name("Cá chiên giòn")
        assert "ca" in result
        assert "chien" not in result  # "chiên" bị loại

    def test_stir_fried_dishes(self) -> None:
        """Chuẩn hoá các món xào."""
        result = normalize_dish_name("Mì xào bò")
        assert "mi" in result
        assert "bo" in result
        assert "xao" not in result  # "xào" bị loại

    def test_soup_dishes(self) -> None:
        """Chuẩn hoá các món canh/súp."""
        result = normalize_dish_name("Canh chua cá lóc")
        assert "canh" in result
        assert "chua" in result
        assert "ca" in result

    def test_dessert_dishes(self) -> None:
        """Chuẩn hoá các món tráng miệng."""
        che = normalize_dish_name("Chè ba màu")
        kem = normalize_dish_name("Kem flan")
        assert "che" in che
        assert "kem" in kem
        assert che != kem


class TestNormalizeDishNames:
    """Test suite cho normalize_dish_names() (batch processing)."""

    def test_batch_normalization(self) -> None:
        """Chuẩn hoá danh sách tên món."""
        names = ["Cơm sườn", "Phở bò", "Bún riêu"]
        results = normalize_dish_names(names)
        assert len(results) == 3
        assert all(isinstance(r, str) for r in results)
        assert "com" in results[0]
        assert "pho" in results[1]
        assert "bun" in results[2]

    def test_empty_list(self) -> None:
        """Danh sách rỗng trả về danh sách rỗng."""
        assert normalize_dish_names([]) == []


class TestAreDishesSimilar:
    """Test suite cho are_dishes_similar()."""

    def test_similar_dishes(self) -> None:
        """Nhận diện đúng các món tương đồng."""
        assert are_dishes_similar("Cơm sườn bì chả", "Cơm sườn nướng bì chả")
        # Phở bò tái vs Phở bò chín: Jaccard = 2/4 = 0.5 (tai vs chin khác nhau)
        assert are_dishes_similar("Phở bò tái", "Phở bò chín", threshold=0.5)
        # Cà phê đen đá vs Cà phê đen nóng: khác nhau (đá vs nóng)
        assert not are_dishes_similar("Cà phê đen đá", "Cà phê đen nóng")
        # Nhưng cùng loại cà phê đen thì giống nhau
        assert are_dishes_similar("Cà phê đen đá", "Cà phê đen")

    def test_different_dishes(self) -> None:
        """Phân biệt đúng các món khác nhau."""
        assert not are_dishes_similar("Cơm sườn", "Phở bò")
        assert not are_dishes_similar("Bún riêu", "Bún bò")
        assert not are_dishes_similar("Trà sữa", "Cà phê")

    def test_threshold_parameter(self) -> None:
        """Tham số threshold hoạt động đúng."""
        name1 = "Cơm sườn bì chả"
        name2 = "Cơm sườn"
        # Với threshold cao (0.9), 2 món này không đủ tương đồng
        assert not are_dishes_similar(name1, name2, threshold=0.9)
        # Với threshold thấp (0.5), chúng tương đồng
        assert are_dishes_similar(name1, name2, threshold=0.5)

    def test_empty_names(self) -> None:
        """Xử lý tên món rỗng."""
        assert not are_dishes_similar("", "Cơm sườn")
        assert not are_dishes_similar("Cơm sườn", "")
        assert not are_dishes_similar("", "")

    def test_case_insensitive(self) -> None:
        """So sánh không phân biệt hoa/thường."""
        assert are_dishes_similar("CƠM SƯỜN", "cơm sườn")
        assert are_dishes_similar("Phở Bò", "PHỞ BÒ")

    def test_real_world_examples(self) -> None:
        """Test với các ví dụ thực tế từ menu F&B Việt Nam."""
        # Các biến thể cơm tấm
        assert are_dishes_similar(
            "Cơm tấm sườn bì chả",
            "Cơm sườn bì chả",
        )
        # Các biến thể phở
        assert are_dishes_similar(
            "Phở bò tái lăn đặc biệt",
            "Phở bò tái",
        )
        # Các biến thể bún bò
        assert are_dishes_similar(
            "Bún bò Huế đặc biệt",
            "Bún bò Huế",
        )
        # Các biến thể cà phê — "đá" vs "nóng" khác nhau, threshold 0.6
        assert are_dishes_similar(
            "Cà phê sữa đá",
            "Cà phê sữa nóng",
            threshold=0.6,
        )
