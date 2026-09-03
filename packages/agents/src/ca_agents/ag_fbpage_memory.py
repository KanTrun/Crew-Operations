"""AG-FBPAGE MEMORY: Lưu trữ và trích xuất cặp mẫu chuẩn CSKH (Golden Few-Shot Dataset).

Học trực tiếp từ các chỉnh sửa câu trả lời của Quản lý trên hệ thống.
Tuân thủ kiến trúc: Chỉ dùng thư viện chuẩn Python, không import DB/FastAPI.
"""

from __future__ import annotations

from typing import Any


def extract_cskh_golden_pair(
    customer_msg: str,
    ai_draft: str,
    manager_reply: str,
    intent: str = "khac",
    customer_name: str = "",
) -> dict[str, Any] | None:
    """So sánh câu bot gợi ý và câu Quản lý duyệt gửi đi để tạo cặp mẫu chuẩn (Golden Pair).

    Nếu Quản lý có chỉnh sửa (khác biệt đáng kể về nội dung/văn phong),
    lưu lại làm bài học mẫu cho AI các lần sau.
    """
    clean_cust = customer_msg.strip()
    clean_draft = ai_draft.strip()
    clean_mgr = manager_reply.strip()

    if not clean_cust or not clean_mgr:
        return None

    # Nếu quản lý giữ nguyên câu của AI (không sửa gì), không cần lưu làm bài học sửa đổi
    if clean_draft and clean_draft == clean_mgr:
        return None

    # Xác định điểm nhấn cải thiện từ câu trả lời của quản lý
    highlights = []
    mgr_lower = clean_mgr.lower()
    draft_lower = clean_draft.lower()

    if any(k in mgr_lower for k in ("dạ em chào", "chào anh", "chào chị", "dạ anh", "dạ chị")) and not any(
        k in draft_lower for k in ("dạ anh", "dạ chị")
    ):
        highlights.append("xung_ho_than_mat")

    if any(k in mgr_lower for k in ("rất tiếc", "thành thật xin lỗi", "mong anh/chị thông cảm")) and not any(
        k in draft_lower for k in ("thành thật xin lỗi", "mong anh/chị thông cảm")
    ):
        highlights.append("thau_cam_sau_sac")

    if any(k in mgr_lower for k in ("hotline", "quản lý sẽ liên hệ", "đổi ly mới", "gửi lại món")):
        highlights.append("giai_phap_dut_khoat")

    return {
        "customer_msg": clean_cust,
        "ai_draft": clean_draft,
        "manager_reply": clean_mgr,
        "intent": intent,
        "customer_name": customer_name or "Khách hàng",
        "improvement_highlights": highlights,
    }


def format_golden_cskh_prompt(golden_examples: list[dict[str, Any]] | None) -> str:
    """Chuyển đổi danh sách bài học mẫu đã duyệt thành đoạn chỉ dẫn Few-Shot trong system prompt."""
    if not golden_examples:
        return ""

    lines = [
        "--- CÁC CÂU TRẢ LỜI MẪU CHUẨN MỰC TỪ QUẢN LÝ (BẮT BUỘC HỌC THEO PHONG CÁCH NÀY) ---",
        "Dưới đây là các tình huống thực tế đã được Quản lý quán trực tiếp chỉnh sửa và phê duyệt:",
    ]

    for idx, ex in enumerate(golden_examples[:5], start=1):
        cust = ex.get("customer_msg", "")
        mgr = ex.get("manager_reply", "")
        intent = ex.get("intent", "CSKH")
        if cust and mgr:
            lines.append(f"\n[Ví dụ mẫu #{idx} - Tình huống: {intent}]")
            lines.append(f"- Khách hỏi: \"{cust}\"")
            lines.append(f"- Quản lý phản hồi chuẩn: \"{mgr}\"")

    lines.append("\nHÃY ÁP DỤNG ĐÚNG GIỌNG ĐIỆU VÀ CÁCH XỬ LÝ NHÃ NHẶN CỦA QUẢN LÝ Ở TRÊN!")
    lines.append("--------------------------------------------------------------------------------")
    return "\n".join(lines)
