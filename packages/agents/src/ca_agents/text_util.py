"""Helper so khớp từ khoá tiếng Việt — dùng chung cho các bộ phân loại danh mục.

Lý do tồn tại: các module `sources/*_source.py` đều có `_detect_category()` riêng
và đều dùng `any(w in blob for w in keywords)` — **so khớp SUBSTRING**. Với tiếng
Việt, cách này sai một cách âm thầm:

    "ăn" in "giá xăng dầu hôm nay"  →  True  (sai: xăng không phải đồ ăn)
    "trà" in "trà sữa"              →  True  (đúng)

Hậu quả đo live 2026-09-24: xu hướng `giá xăng dầu hôm nay` bị gán nhãn
`am_thuc_fnb` trên radar AG-TREND.

`re` của Python hiểu Unicode nên `\\băn\\b` KHÔNG khớp trong `"xăng"` — đúng
ngữ nghĩa "từ khoá là một TỪ", không phải một đoạn ký tự bất kỳ.
"""

from __future__ import annotations

import re

# Cache regex theo keyword — `_detect_category` chạy cho mọi item trong mọi
# request, biên dịch lại mỗi lần sẽ lãng phí CPU vô ích.
_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    pat = _PATTERN_CACHE.get(keyword)
    if pat is None:
        pat = re.compile(rf"\b{re.escape(keyword)}\b")
        _PATTERN_CACHE[keyword] = pat
    return pat


def match_any_keyword(blob: str, keywords: tuple[str, ...] | list[str]) -> bool:
    """True nếu `blob` (đã lowercase) chứa BẤT KỲ keyword nào như một TỪ riêng.

    Args:
        blob: văn bản đã hạ chữ thường (caller tự `.lower()`).
        keywords: danh sách từ khoá, cũng nên ở dạng chữ thường.

    Ví dụ:
        >>> match_any_keyword("giá xăng dầu hôm nay", ("ăn", "trà"))
        False
        >>> match_any_keyword("quán ăn vặt", ("ăn",))
        True
    """
    return any(_keyword_pattern(w).search(blob) for w in keywords)


__all__ = ["match_any_keyword"]
