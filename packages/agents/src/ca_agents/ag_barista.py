"""
AG-BARISTA: Beverage Sommelier & Consultation Agent for Nhịp Quán.

Specialized in:
- Flavor profiling & customer taste matching (sweetness, ice, caffeine tolerance).
- Recommending signature drinks and customized beverage options.
- Natural upselling of bakery items and pairings (croissant, tiramisu).
- 100% natural, passionate barista Vietnamese service persona.
"""

from __future__ import annotations

from typing import Any


def consult_beverage(
    customer_query: str, menu: list[dict[str, Any]] | None = None
) -> tuple[str, list[str]]:
    """
    Provide expert beverage recommendations based on taste preferences.
    Returns (response_text, recommended_item_ids).
    """
    t = customer_query.lower()
    _ = menu

    # Case 1: Sensitive to caffeine / No coffee / Fruit tea preference
    if any(
        k in t
        for k in (
            "say cà phê",
            "say ca phe",
            "không uống được cà phê",
            "khong uong duoc ca phe",
            "không có caffeine",
            "trà",
            "tra ",
        )
    ):
        reply = (
            "Dạ nếu mình dễ bị say cà phê hoặc thích hương vị thanh mát thì em gợi ý mình thử món Trà đào bên em nha! 🍑\n"
            "Trà được ủ từ lá trà tự nhiên kết hợp đào giòn ngọt thơm dịu, giải nhiệt cực đã mà không lo mất ngủ ạ.\n"
            "Món này mình có thể chọn mức ngọt vừa hoặc ít ngọt tùy khẩu vị nhé ạ!"
        )
        return reply, ["mon_tra"]

    # Case 2: Sweet, creamy, mild coffee (Bạc xỉu / Salt coffee)
    if any(
        k in t
        for k in (
            "ít ngọt",
            "it ngot",
            "béo",
            "ngọt nhẹ",
            "dễ uống",
            "de uong",
            "bạc xỉu",
            "bac xiu",
            "muối",
            "muoi",
        )
    ):
        reply = (
            "Dạ nếu mình thích vị cà phê thơm nhẹ quyện với lớp sữa béo bùi thì món Bạc xỉu hoặc Cà phê muối là chân ái luôn ạ! ✨\n"
            "Vị đắng êm dịu hòa cùng sữa đặc sánh mịn, béo bùi mà không hề ngấy.\n"
            "Món này dùng kèm một chiếc Bánh sừng bò nóng giòn là chuẩn bài cho buổi trò chuyện luôn nha mình ơi!"
        )
        return reply, ["mon_da"]

    # Case 3: Strong traditional coffee for focus
    if any(
        k in t
        for k in ("đậm", "dam", "tỉnh táo", "tinh tao", "đen", "den", "sữa", "sua", "mạnh", "manh")
    ):
        reply = (
            "Dạ để nạp năng lượng tỉnh táo làm việc thì Cà phê đen hoặc Cà phê sữa pha phin truyền thống bên em là chuẩn nhất ạ! ☕\n"
            "Hạt cà phê Robusta mộc nguyên chất đậm vị, thơm nồng nàn đặc trưng của Nhịp Quán.\n"
            "Mình thích uống đá sảng khoái hay uống nóng đậm đà để em nhắn quầy chuẩn bị nha?"
        )
        return reply, ["mon_den", "mon_sua"]

    # Case 4: General consultation / Best sellers
    reply = (
        "Dạ bên em có 2 dòng đồ uống được khách yêu thích nhất nè mình ơi:\n"
        "• Dòng Cà phê: Bạc xỉu béo thơm dịu nhẹ (32.000đ) & Cà phê sữa truyền thống đậm đà (30.000đ).\n"
        "• Dòng Trà thanh nhiệt: Trà đào miếng giòn ngọt mát lành (35.000đ).\n\n"
        "Mình đang thích gu đậm đà tỉnh táo hay gu thanh ngọt nhẹ nhàng để em tư vấn chuẩn gu cho mình nha?"
    )
    return reply, ["mon_da", "mon_tra"]


__all__ = ["consult_beverage"]
