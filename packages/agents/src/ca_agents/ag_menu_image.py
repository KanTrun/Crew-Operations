"""Agent tạo ảnh quảng cáo cho menu — prompt TẤT ĐỊNH, không tiền xử lý ảnh.

Luồng cũ chạy vision-LLM trên ảnh ly nước để "đoán" ra prompt, rồi (khi muốn giữ
nguyên ly) còn tách chủ thể bằng mask màu + composite bằng Pillow. Cả hai bước đó
đã bỏ:

1. **Vision LLM là điểm hỏng thừa.**  Mỗi ảnh tốn 3–10 giây và một lượt gọi mạng
   chỉ để suy ra vài tính từ mô tả món — trong khi tên món + phong cách đã có sẵn
   trong dữ liệu menu. Provider LLM lỗi là cả tính năng đứng.
2. **Tách/composite cục bộ không còn cần thiết.**  Model sinh ảnh dựng lại cả ly
   nước đẹp hơn ảnh chụp vội tại quán, nên "giữ nguyên pixel ly gốc" chỉ giữ lại
   ảnh xấu. Muốn sửa chính ảnh thật thì dùng chế độ `edit_photo` — Cloudflare
   Workers AI nhận ảnh người dùng trực tiếp, không cần mask/composite.

Nguồn prompt duy nhất: :func:`ca_agents.menu_prompt.build_menu_prompt`.

Fail-closed: thiếu tên món → trả lỗi rõ ràng, không bịa prompt.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ca_agents.menu_prompt import build_menu_prompt, translate_mon_ten
from ca_agents.menu_style import MenuStyle

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MenuImageResult:
    """Kết quả tạo prompt cho ảnh menu."""

    ok: bool
    prompt_en: str = ""
    prompt_vi: str = ""
    error: str = ""
    provider: str = "local-template"


def generate_menu_prompt(
    mon_ten: str,
    *,
    mo_ta: str = "",
    style: MenuStyle | None = None,
    aspect_ratio: str = "1:1",
) -> MenuImageResult:
    """Dựng prompt sinh ảnh từ tên món + phong cách (tất định, không gọi LLM).

    Args:
        mon_ten: Tên món như hiển thị trên menu (tiếng Việt vẫn được).
        mo_ta: Mô tả thêm của người dùng (tuỳ chọn).
        style: Phong cách thiết kế; None → preset mặc định của quán.
        aspect_ratio: Tỷ lệ khung, dùng cho gợi ý bố cục.

    Returns:
        MenuImageResult — ok=True kèm ``prompt_en``; ok=False kèm ``error`` khi
        tên món trống (không bao giờ sinh ảnh từ prompt rỗng).
    """
    prompt = build_menu_prompt(mon_ten, mo_ta=mo_ta, style=style, aspect_ratio=aspect_ratio)
    if not prompt:
        return MenuImageResult(ok=False, error="thieu_ten_mon")
    # Bản tiếng Việt để người dùng đọc lại và biết ảnh sẽ ra cái gì; dịch bằng
    # chính từ điển đã dùng cho prompt nên hai bên không lệch nhau.
    subject_vi = mon_ten.strip()
    subject_en = translate_mon_ten(mon_ten)
    if subject_en and subject_en != subject_vi:
        prompt_vi = f"Ảnh quảng cáo cho món {subject_vi} ({subject_en})"
    else:
        prompt_vi = f"Ảnh quảng cáo cho món {subject_vi}"
    return MenuImageResult(ok=True, prompt_en=prompt, prompt_vi=prompt_vi)
