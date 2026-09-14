"""Chuẩn hoá tên món ăn F&B — hàm thuần tuý (ADR-002).

Plan mục 2.2: "Cơm sườn bì chả" ≈ "Cơm tấm sườn bì" ≈ "Cơm sườn nướng bì chả"
phải chuẩn hoá về cùng một dạng để group theo `core_category`, tránh việc một món
bị tính lệch nhóm vì khác tên gọi.

Chiến lược:
1. Lowercase + bỏ dấu tiếng Việt → ASCII
2. Loại bỏ từ chỉ phương pháp chế biến (nướng, chiên, xào...)
3. Loại bỏ từ đệm (tấm, món, phần, size...)
4. Sắp xếp token theo thứ tự alphabet → dạng canonical
5. Trả về chuỗi đã chuẩn hoá

KHÔNG dùng LLM, KHÔNG gọi network, KHÔNG đọc file — hoàn toàn tất định.
"""

from __future__ import annotations

import re
import unicodedata

# Từ chỉ phương pháp chế biến — loại bỏ vì không ảnh hưởng đến bản chất món
_COOKING_METHODS = frozenset({
    "nuong", "chien", "xao", "luoc", "hap", "kho", "ram", "rang",
    "om", "tim", "nau", "xien", "que", "cuon", "tron",
    "grilled", "fried", "steamed", "boiled", "roasted", "baked",
})

# Từ đệm / từ chỉ đơn vị — loại bỏ vì không mang nghĩa phân biệt món
_FILLER_WORDS = frozenset({
    "tam", "mon", "phan", "size", "loai", "suat", "dia", "to",
    "chen", "ly", "coc", "chai", "lon", "nhỏ", "vua",
    "dac", "biet", "thuong", "combo", "set",
    "s", "m", "l", "xl", "xxl",
})

# Từ nối / từ hư — loại bỏ
_STOPWORDS = frozenset({
    "va", "voi", "cung", "theo", "kieu", "style", "with", "and",
})


def _remove_vietnamese_diacritics(text: str) -> str:
    """Bỏ dấu tiếng Việt, chuyển về ASCII.

    "Cơm sườn bì chả" → "Com suon bi cha"
    """
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    replacements = {
        "đ": "d", "Đ": "D",
        "ơ": "o", "Ơ": "O",
        "ư": "u", "Ư": "U",
        "ă": "a", "Ă": "A",
        "ê": "e", "Ê": "E",
        "ô": "o", "Ô": "O",
    }
    for vi_char, ascii_char in replacements.items():
        ascii_text = ascii_text.replace(vi_char, ascii_char)
    return ascii_text


def _tokenize(text: str) -> list[str]:
    """Tách chuỗi thành token, loại bỏ ký tự đặc biệt."""
    text = text.lower()
    text = _remove_vietnamese_diacritics(text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t.strip() for t in text.split() if t.strip()]
    return tokens


def normalize_dish_name(raw_name: str) -> str:
    """Chuẩn hoá tên món về dạng canonical.

    Args:
        raw_name: Tên món gốc (VD: "Cơm sườn nướng bì chả")

    Returns:
        Chuỗi đã chuẩn hoá, token sắp xếp alphabet (VD: "bi cha com suon")
    """
    if not raw_name or not raw_name.strip():
        return ""

    tokens = _tokenize(raw_name)

    filtered = [
        t for t in tokens
        if t not in _COOKING_METHODS
        and t not in _FILLER_WORDS
        and t not in _STOPWORDS
        and len(t) > 0
    ]

    canonical = sorted(filtered)
    return " ".join(canonical)


def normalize_dish_names(names: list[str]) -> list[str]:
    """Chuẩn hoá danh sách tên món (tiện ích cho batch processing)."""
    return [normalize_dish_name(name) for name in names]


def are_dishes_similar(name1: str, name2: str, *, threshold: float = 0.7) -> bool:
    """Kiểm tra 2 tên món có tương đồng sau chuẩn hoá không."""
    norm1 = normalize_dish_name(name1)
    norm2 = normalize_dish_name(name2)

    if not norm1 or not norm2:
        return False

    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())

    if not tokens1 or not tokens2:
        return False

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    jaccard = len(intersection) / len(union)
    return jaccard >= threshold
