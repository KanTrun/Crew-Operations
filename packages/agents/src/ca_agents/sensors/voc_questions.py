"""Bộ câu hỏi Jev cho AG-VOC (Voice of Customer — phản hồi khách).

Dùng trong `phan_loai_nang_cao()` để bổ sung phân loại sau khi regex đã chạy.
Tái dùng định nghĩa từ FB_QUESTIONS nhưng tách riêng để VOC có thể
điều chỉnh instructions phù hợp với ngữ cảnh review/phản hồi, không phải
tin nhắn trực tiếp.

Signals:
- `nguy_co_suc_khoe`: review đề cập vệ sinh an toàn thực phẩm → rút hạn 1h.
- `muc_gay_gat`: mức tức giận trong phản hồi → nếu ≥ 1.5 rút hạn 2h.
- `co_ve_mia_mai`: phát hiện mỉa mai ngầm mà keyword bỏ lọt.
"""

from __future__ import annotations

from typing import Any

VOC_QUESTIONS: dict[str, dict[str, Any]] = {
    "nguy_co_suc_khoe": {
        "type": "noul",
        "instructions": (
            "Phản hồi có đề cập tới ngộ độc, đau bụng, dị ứng, dị vật, "
            "hoặc bất kỳ ảnh hưởng sức khỏe sau khi dùng đồ của quán không?"
        ),
    },
    "muc_gay_gat": {
        "type": "score",
        "instructions": "Mức tức giận / bức xúc trong nội dung phản hồi của khách?",
        "criteria": [
            "Bình thường: nhận xét khách quan hoặc khen",
            "Thất vọng nhẹ, ôn hòa",
            "Khiếu nại gay gắt, dùng lời lẽ nặng",
            "Đe dọa, xúc phạm hoặc tuyên bố tẩy chay",
        ],
    },
    "co_ve_mia_mai": {
        "type": "noul",
        "instructions": (
            "Nội dung có vẻ mỉa mai, nói ngược với ý thật "
            "(khen giả vờ nhưng thực ra chê, hoặc sử dụng ngôn ngữ mỉa mai)?"
        ),
    },
}
