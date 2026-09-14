"""Chuẩn hoá tên món ăn F&B — hàm thuần tuý (ADR-002).

Re-export từ ca_agents.sources.dish_name_normalizer để tuân thủ kiến trúc test_architecture.
"""

from __future__ import annotations

from ca_agents.sources.dish_name_normalizer import (
    _COOKING_METHODS,
    _FILLER_WORDS,
    _STOPWORDS,
    _remove_vietnamese_diacritics,
    _tokenize,
    are_dishes_similar,
    normalize_dish_name,
    normalize_dish_names,
)

__all__ = [
    "_COOKING_METHODS",
    "_FILLER_WORDS",
    "_STOPWORDS",
    "_remove_vietnamese_diacritics",
    "_tokenize",
    "are_dishes_similar",
    "normalize_dish_name",
    "normalize_dish_names",
]
