"""Style Extractor & Tone Memory for AG-MAILWRITER.

Trích xuất đặc trưng văn phong từ những lần Chủ quán / Quản lý chỉnh sửa bản nháp email,
lưu vào Tone Memory để các lần soạn thảo sau viết đúng gu của quán.
"""

from __future__ import annotations

import re
from typing import Any


def extract_style_preferences(original_body: str, amended_body: str) -> dict[str, Any]:
    """Phân tích so sánh bản gốc do AI soạn và bản do chủ quán sửa lại."""
    orig = (original_body or "").strip()
    amend = (amended_body or "").strip()
    if not amend:
        return {}

    lines = [line.strip() for line in amend.split("\n") if line.strip()]
    first_line = lines[0] if lines else ""
    last_lines = lines[-2:] if len(lines) >= 2 else (lines[-1:] if lines else [])

    # 1. Nhận diện cách mở đầu / xưng hô
    greeting_style = "Thân gửi"
    if re.search(r"chào\s+em", first_line, re.IGNORECASE):
        greeting_style = "Chào em"
    elif re.search(r"chào\s+bạn", first_line, re.IGNORECASE):
        greeting_style = "Chào bạn"
    elif re.search(r"gửi\s+(team|cả\s*nhà|các\s*bạn)", first_line, re.IGNORECASE):
        greeting_style = "Gửi team"
    elif re.search(r"kính\s*gửi", first_line, re.IGNORECASE):
        greeting_style = "Kính gửi"

    # 2. Nhận diện chữ ký / người gửi
    signoff_name = ""
    for line in reversed(last_lines):
        if any(w in line.lower() for w in ("anh ", "chị ", "quản lý", "chủ quán", "ban quản lý", "team")):
            signoff_name = line
            break

    # 3. Độ dài và phong thái
    orig_words = len(orig.split())
    amend_words = len(amend.split())
    if amend_words < orig_words * 0.7:
        brevity = "ngan_gon_suc_tich"
    elif amend_words > orig_words * 1.3:
        brevity = "chi_tiet_dan_do"
    else:
        brevity = "vua_phai"

    # 4. Sử dụng emoji
    has_emoji = bool(re.search(r"[📌✨☕️💪❤️👉👋]", amend))

    return {
        "greeting_style": greeting_style,
        "signoff_name": signoff_name,
        "brevity": brevity,
        "has_emoji": has_emoji,
        "amended_sample": amend[:500],
    }


def format_style_prompt(style_memory: dict[str, Any] | None) -> str:
    """Chuyển đổi Style Memory thành chỉ dẫn bổ sung cho System Prompt của AG-MAILWRITER."""
    if not style_memory:
        return ""

    parts: list[str] = ["QUY CHUẨN VĂN PHONG RIÊNG CỦA CHỦ QUÁN (ĐÃ HỌC TỪ CÁC LẦN SỬA TRƯỚC):"]

    greeting = style_memory.get("greeting_style")
    if greeting:
        parts.append(f"- Lời chào quen thuộc: Ưu tiên mở đầu dạng \"{greeting} [Tên nhân viên],\"")

    signoff = style_memory.get("signoff_name")
    if signoff:
        parts.append(f"- Chữ ký đại diện: Ký tên là \"{signoff}\"")

    brevity = style_memory.get("brevity")
    if brevity == "ngan_gon_suc_tich":
        parts.append("- Độ dài: Chủ quán thích cực kỳ ngắn gọn, súc tích, chỉ gạch 2-3 ý quan trọng nhất.")
    elif brevity == "chi_tiet_dan_do":
        parts.append("- Độ dài: Trình bày chi tiết, dặn dò cẩn thận các bước thực hiện.")

    samples = style_memory.get("samples") or []
    if samples and isinstance(samples, list):
        parts.append("\nVí dụ các bức thư thực tế Chủ quán từng chỉnh sửa và ưng ý:")
        for idx, sample in enumerate(samples[-2:], 1):
            s_subj = sample.get("subject", "")
            s_body = sample.get("body", "")
            parts.append(f"[Mẫu {idx}] Tiêu đề: {s_subj}\nNội dung:\n{s_body}\n")

    return "\n".join(parts)
