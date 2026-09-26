"""Test cho module dựng prompt sinh ảnh menu (ca_agents.menu_prompt).

Không gọi mạng, không gọi LLM: prompt được lắp từ dữ liệu có cấu trúc nên hoàn
toàn tất định — đó chính là tính chất được kiểm tra ở đây.
"""

from __future__ import annotations

from pathlib import Path

from ca_agents.ag_menu_image import generate_menu_prompt
from ca_agents.menu_prompt import build_menu_prompt, translate_mon_ten
from ca_agents.menu_style import default_styles, parse_style

# ── Dịch tên món ────────────────────────────────────────────────────────────


class TestTranslateMonTen:
    def test_longest_phrase_wins(self) -> None:
        """"trà đào cam sả" phải khớp CẢ CỤM, không bị cắt thành "trà đào" + phần lẻ."""
        assert translate_mon_ten("Trà đào cam sả") == "peach orange lemongrass tea"

    def test_plain_dish_names(self) -> None:
        assert translate_mon_ten("Cà phê sữa đá") == "iced milk coffee"
        assert translate_mon_ten("Trà sữa trân châu") == "milk tea with tapioca pearls"
        assert translate_mon_ten("Nước ép dưa hấu") == "watermelon juice"
        assert translate_mon_ten("Sinh tố bơ") == "avocado smoothie"

    def test_english_names_pass_through(self) -> None:
        assert translate_mon_ten("Matcha latte") == "matcha latte"

    def test_diacritics_and_case_insensitive(self) -> None:
        """Cùng món gõ khác kiểu hoa/thường vẫn ra một kết quả."""
        variants = ["trà đào", "Trà Đào", "TRÀ ĐÀO", "  trà đào  ", "trà đào!"]
        assert {translate_mon_ten(v) for v in variants} == {"peach tea"}

    def test_unknown_words_kept_not_dropped(self) -> None:
        """Từ lạ được GIỮ NGUYÊN — mất thông tin còn tệ hơn để model tự đoán."""
        out = translate_mon_ten("Món lạ hoắc xyz")
        assert "xyz" in out
        assert "lạ" in out

    def test_empty_input(self) -> None:
        assert translate_mon_ten("") == ""
        assert translate_mon_ten("   ") == ""

    def test_state_word_moved_to_front(self) -> None:
        """"iced" đứng trước để cụm ra tự nhiên ("iced milk coffee")."""
        assert translate_mon_ten("sữa đá").startswith("iced")


# ── Dựng prompt ─────────────────────────────────────────────────────────────


class TestBuildMenuPrompt:
    def test_contains_translated_subject(self) -> None:
        prompt = build_menu_prompt("Trà đào cam sả")
        assert "peach orange lemongrass tea" in prompt
        assert prompt.startswith("professional food photography")

    def test_no_drink_negation(self) -> None:
        """Prompt ảnh HOÀN CHỈNH không được chứa điều khoản cấm đồ uống.

        ``menu_style._NEGATION`` có "no drink, no beverage" (dành cho ảnh NỀN
        trống). Dùng nhầm vào đây sẽ xoá luôn món khỏi ảnh.
        """
        prompt = build_menu_prompt("Cà phê sữa đá")
        assert "no drink" not in prompt
        assert "no beverage" not in prompt
        assert "no glass" not in prompt
        # Nhưng vẫn phải chặn chữ và người — model hay vẽ biển hiệu và bàn tay.
        assert "no text" in prompt
        assert "no people" in prompt

    def test_deterministic(self) -> None:
        """Cùng món + cùng phong cách → chuỗi y hệt (điều kiện để menu đồng bộ)."""
        a = build_menu_prompt("Trà đào", aspect_ratio="4:5")
        b = build_menu_prompt("Trà đào", aspect_ratio="4:5")
        assert a == b

    def test_aspect_ratio_changes_composition_only(self) -> None:
        square = build_menu_prompt("Trà đào", aspect_ratio="1:1")
        tall = build_menu_prompt("Trà đào", aspect_ratio="9:16")
        assert "centered square composition" in square
        assert "tall vertical composition" in tall
        # Không được để lộ tỷ lệ thô vào prompt (provider từ chối "aspect_ratio").
        assert "1:1" not in square
        assert "9:16" not in tall

    def test_style_fields_appear_in_prompt(self) -> None:
        style = parse_style(
            {
                "slug": "test_style",
                "ten": "Thử",
                "mo_ta": "",
                "scene": "marble_bar",
                "lighting": "moody_low_key",
                "palette": "deep_emerald",
                "lens": "macro_detail",
            }
        )
        assert style is not None
        prompt = build_menu_prompt("Trà đào", style=style)
        assert "marble countertop" in prompt
        assert "moody low-key" in prompt
        assert "emerald" in prompt
        assert "macro" in prompt

    def test_falls_back_to_default_style(self) -> None:
        """Không truyền phong cách vẫn ra prompt hợp lệ (preset đầu tiên)."""
        prompt = build_menu_prompt("Trà đào", style=None)
        first = default_styles()[0]
        assert first.ten  # preset tồn tại
        assert "wooden cafe table" in prompt

    def test_extra_description_is_translated(self) -> None:
        """Mô tả tiếng Việt phải thành tiếng Anh — model hiểu tiếng Anh tốt hơn."""
        prompt = build_menu_prompt("Trà đào", mo_ta="thêm đá và bạc hà")
        assert "mint" in prompt
        assert " bạc hà" not in prompt

    def test_extra_description_truncated(self) -> None:
        prompt = build_menu_prompt("Trà đào", mo_ta="x" * 5000)
        # Không để mô tả nuốt hết prompt (model bỏ qua phần mô tả món).
        assert len(prompt) < 1500

    def test_empty_name_returns_empty_string(self) -> None:
        """Tên món rỗng → chuỗi rỗng để endpoint từ chối, KHÔNG sinh ảnh vô nghĩa."""
        assert build_menu_prompt("") == ""
        assert build_menu_prompt("   ") == ""
        assert build_menu_prompt("!!!") == ""


class TestGenerateMenuPrompt:
    def test_ok_result_shape(self) -> None:
        res = generate_menu_prompt("Trà đào cam sả", aspect_ratio="1:1")
        assert res.ok is True
        assert res.provider == "local-template"
        assert "peach orange lemongrass tea" in res.prompt_en
        assert "Trà đào cam sả" in res.prompt_vi

    def test_empty_name_fails_closed(self) -> None:
        res = generate_menu_prompt("   ")
        assert res.ok is False
        assert res.error == "thieu_ten_mon"
        assert res.prompt_en == ""

    def test_no_network_dependency(self) -> None:
        """Module không import llm/urllib — prompt không phụ thuộc mạng."""
        import ca_agents.menu_prompt as module

        text = Path(module.__file__).read_text(encoding="utf-8")
        assert "urllib" not in text
        assert "from ca_agents.llm" not in text
        assert "requests" not in text
