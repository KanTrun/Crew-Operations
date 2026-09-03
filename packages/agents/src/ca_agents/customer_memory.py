"""CUSTOMER MEMORY: Quản lý hồ sơ sở thích và nhận diện Khách Quen cho Nhịp Quán.

Giúp AI ghi nhớ tên gọi, món quen, lưu ý dị ứng/thói quen của từng khách hàng.
Tuân thủ kiến trúc: Chỉ dùng thư viện chuẩn Python, không import DB/FastAPI.
"""

from __future__ import annotations

import re
from typing import Any

_NAME_PATTERNS = (
    r"(?:mình tên|tôi tên|em tên|anh tên|chị tên)\s+([A-ZÀ-Ỹa-zà-ỹ\s]{2,20})",
    r"(?:gọi cho|liên hệ)\s+(?:anh|chị|em|bạn)\s+([A-ZÀ-Ỹa-zà-ỹ\s]{2,20})",
    r"^(?:anh|chị|em)\s+([A-ZÀ-Ỹa-zà-ỹ]{2,15})\s+(?:đây|nè|đây ạ)",
)

_DRINK_KEYWORDS = (
    "cà phê đen",
    "cà phê sữa",
    "cafe sữa",
    "bạc xỉu",
    "bac xiu",
    "cà phê muối",
    "trà đào",
    "trà vải",
    "matcha",
    "cappuccino",
    "latte",
    "cold brew",
)

_PREFERENCE_KEYWORDS = (
    "ít đường",
    "it duong",
    "ít ngọt",
    "it ngot",
    "không đường",
    "khong duong",
    "không ngọt",
    "khong ngot",
    "ít đá",
    "it da",
    "không đá",
    "khong da",
    "nhiều sữa",
    "nhieu sua",
    "sữa yến mạch",
    "oat milk",
    "sữa hạnh nhân",
    "dị ứng sữa",
    "di ung sua",
    "dị ứng đậu phộng",
)


def extract_customer_preferences(messages: list[str]) -> dict[str, Any]:
    """Phân tích các câu nhắn của khách để trích xuất tên gọi, món yêu thích và lưu ý cá nhân."""
    extracted_name = ""
    favorite_drinks = set()
    special_notes = set()

    full_text = " \n ".join(messages)

    # 1. Tìm tên khách
    for pat in _NAME_PATTERNS:
        match = re.search(pat, full_text, re.IGNORECASE)
        if match:
            raw_name = match.group(1).strip()
            # Loại bỏ các từ thừa
            words = [w for w in raw_name.split() if w.lower() not in ("là", "nè", "nha", "nhé", "đây", "ạ")]
            if words:
                extracted_name = " ".join(words).title()
                break

    # 2. Tìm món uống được nhắc tới
    text_lower = full_text.lower()
    for drink in _DRINK_KEYWORDS:
        if drink in text_lower:
            # Chuẩn hóa tên món đẹp
            pretty_name = drink.replace("cafe", "cà phê").title()
            favorite_drinks.add(pretty_name)

    # 3. Tìm khẩu vị / lưu ý đặc biệt
    for pref in _PREFERENCE_KEYWORDS:
        if pref in text_lower:
            special_notes.add(pref.title())

    return {
        "ten_khach": extracted_name,
        "favorite_drinks": sorted(favorite_drinks),
        "special_notes": sorted(special_notes),
    }


def merge_customer_profile(
    existing: dict[str, Any] | None,
    new_info: dict[str, Any],
) -> dict[str, Any]:
    """Hợp nhất thông tin mới vào hồ sơ khách hàng hiện có."""
    profile = dict(existing or {})

    # Tên khách
    if new_info.get("ten_khach") and not profile.get("ten_khach"):
        profile["ten_khach"] = new_info["ten_khach"]

    # Số lần tương tác / ghé
    profile["visit_count"] = int(profile.get("visit_count", 0)) + 1

    # Món quen
    favs = set(profile.get("favorite_drinks") or [])
    favs.update(new_info.get("favorite_drinks") or [])
    profile["favorite_drinks"] = sorted(favs)

    # Lưu ý khẩu vị
    notes = set(profile.get("special_notes") or [])
    notes.update(new_info.get("special_notes") or [])
    profile["special_notes"] = sorted(notes)

    # Đánh dấu khách quen nếu tương tác từ 3 lần trở lên
    profile["is_vip_or_regular"] = profile["visit_count"] >= 3

    return profile


def format_customer_greeting_context(profile: dict[str, Any] | None) -> str:
    """Định dạng thông tin khách quen thành đoạn ngữ cảnh cho bot ứng xử tự nhiên."""
    if not profile:
        return ""

    parts = []
    name = profile.get("ten_khach")
    visits = profile.get("visit_count", 1)
    favs = profile.get("favorite_drinks", [])
    notes = profile.get("special_notes", [])

    if name:
        parts.append(f"Khách hàng: {name}")
    if visits > 1:
        parts.append(f"Khách quen đã tương tác {visits} lần")
    if favs:
        parts.append(f"Món yêu thích: {', '.join(favs)}")
    if notes:
        parts.append(f"Khẩu vị / Lưu ý: {', '.join(notes)}")

    if not parts:
        return ""

    return (
        "--- HỒ SƠ KHÁCH HÀNG THÂN THIẾT (HÃY XƯNG HÔ THÂN MẬT VÀ TƯ VẤN ĐÚNG GU) ---\n"
        + "\n".join(f"- {p}" for p in parts)
        + "\n----------------------------------------------------------------------------"
    )
