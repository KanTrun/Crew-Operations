"""AG-MAILWRITER — Chuyên viên soạn thảo email chuyên nghiệp cho Nhịp Quán.

Hỗ trợ Compound Context Injection (Dữ liệu ca, kho, báo cáo sống)
và Tone Memory (Học gu văn phong riêng của chủ quán).
Tuân thủ kiến trúc: Không import DB, FastAPI hay agent khác.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ca_agents.ag_mailwriter.style_extractor import format_style_prompt
from ca_agents.llm import agent_mode, complete, parse_json_object

_MAIL_SYSTEM_BASE = """Bạn là AG-MAILWRITER — Chuyên viên soạn thảo email chuyên nghiệp nhất của hệ thống NHỊP QUÁN (Crew Operations).
Nhiệm vụ của bạn là chuyển hóa các yêu cầu, chỉ đạo thô từ Chủ quán / Quản lý thành văn bản email tiếng Việt chuẩn mực, lịch sự, đúng phong cách vận hành quán cà phê.

Quy chuẩn email bắt buộc:
1. Tiêu đề (Subject): Bắt đầu bằng "[Nhịp Quán]", súc tích, tóm tắt chính xác nội dung (dưới 80 ký tự). Ví dụ: "[Nhịp Quán] Thông báo lịch ca sáng mai" hoặc "[Nhịp Quán] Báo cáo vận hành quán hôm nay".
2. Lời chào (Greeting): Trang trọng, thân mật phù hợp với người nhận (hoặc tuân theo quy chuẩn văn phong riêng của chủ quán nếu được cung cấp).
3. Mở đầu: Nêu ngắn gọn lý do gửi email đại diện từ quán.
4. Thân bài: Trình bày chi tiết, gãy gọn. NẾU CÓ DỮ LIỆU VẬN HÀNH THỰC TẾ (Lịch ca, giờ giấc, bạn cùng ca, tồn kho), BẮT BUỘC phải dùng chính xác các số liệu đó, tuyệt đối không bịa đặt.
5. Lời dặn & Phản hồi: Dặn dò kiểm tra lại lịch/nhiệm vụ, báo lại quản lý/chủ quán trước thời hạn nếu có vướng mắc.
6. Lời chúc & Chữ ký: Kết thúc bằng lời chúc và chữ ký người gửi (ưu tiên theo chữ ký riêng của chủ quán nếu có).

Định dạng trả về duy nhất là JSON hợp lệ:
{
  "subject": "Tiêu đề email",
  "body": "Toàn văn nội dung email có xuống dòng đầy đủ",
  "tone": "lich_su | than_thien | nhac_nho",
  "summary": "Tóm tắt 1 câu nội dung chính"
}
"""


@dataclass
class EmailDraft:
    subject: str
    body: str
    recipient_name: str = ""
    recipient_email: str = ""
    tone: str = "lich_su"
    summary: str = ""
    ops_context_used: dict[str, Any] | None = None
    has_learned_style: bool = False


def _deterministic_draft(
    raw_request: str,
    recipient_name: str = "Bạn",
    sender_name: str = "Ban Quản Lý Nhịp Quán",
    store_name: str = "Nhịp Quán",
    ops_context: dict[str, Any] | None = None,
    style_memory: dict[str, Any] | None = None,
) -> EmailDraft:
    """Tạo bản nháp email tất định chất lượng cao khi ở chế độ replay hoặc LLM không khả dụng."""
    clean_req = raw_request.strip()
    recip = recipient_name.strip() or "Bạn"

    # 1. Áp dụng văn phong đã học từ chủ quán (nếu có)
    greeting_prefix = "Thân gửi"
    final_sender = sender_name
    if style_memory:
        if style_memory.get("greeting_style"):
            greeting_prefix = style_memory["greeting_style"]
        if style_memory.get("signoff_name"):
            final_sender = style_memory["signoff_name"]

    greeting_line = f"{greeting_prefix} {recip},"

    # 2. Xử lý Compound Context (dữ liệu ca làm việc, kho, báo cáo)
    context_lines: list[str] = []
    subject: str = ""
    action_note = "- Nếu có bất kỳ khó khăn hay vướng mắc nào, bạn vui lòng báo lại ngay cho quản lý để được hỗ trợ kịp thời."

    if ops_context and ops_context.get("type") == "shift":
        ngay = ops_context.get("ngay", "ngày mai")
        ca_ten = ops_context.get("ca_ten", "Ca làm việc")
        gio = ops_context.get("gio", "theo quy định")
        vi_tri = ops_context.get("vi_tri", "Pha chế / Phục vụ")
        dong_doi = ops_context.get("dong_doi", [])

        subject = f"[{store_name}] Thông báo lịch ca làm việc {ca_ten} ({ngay})"
        context_lines.append(f"📌 Chi tiết ca làm việc ({ngay}):")
        context_lines.append(f"- Ca: {ca_ten} (Khung giờ: {gio})")
        context_lines.append(f"- Vị trí phụ trách: {vi_tri}")
        if dong_doi:
            context_lines.append(f"- Bạn cùng ca: {', '.join(dong_doi)}")
        action_note = "- Đề nghị bạn có mặt trước ca 10 phút để nhận bàn giao và chuẩn bị mở quán chu đáo."

    elif ops_context and ops_context.get("type") == "inventory":
        mat_hang = ops_context.get("mat_hang", "Nguyên liệu")
        ton = ops_context.get("ton_kho", 0)
        dvt = ops_context.get("dvt", "đơn vị")
        nguong = ops_context.get("nguong", 10)

        subject = f"[{store_name}] Cảnh báo tồn kho & Kiểm tra mặt hàng {mat_hang}"
        context_lines.append("📌 Thông tin tồn kho thực tế:")
        context_lines.append(f"- Mặt hàng: {mat_hang}")
        context_lines.append(f"- Số lượng tồn hiện tại: {ton} {dvt}")
        context_lines.append(f"- Ngưỡng cảnh báo an toàn: {nguong} {dvt}")
        action_note = "- Đề nghị bạn kiểm đếm thực tế tại kho và lên phiếu yêu cầu nhập hàng nếu cần."

    elif ops_context and ops_context.get("type") == "daily_summary":
        ngay = ops_context.get("ngay", "hôm nay")
        doanh_thu = ops_context.get("doanh_thu", 0)
        so_don = ops_context.get("so_don", 0)
        formatted_dt = f"{doanh_thu:,.0f} VNĐ" if isinstance(doanh_thu, (int, float)) else str(doanh_thu)

        subject = f"[{store_name}] Báo cáo tổng kết vận hành ngày {ngay}"
        context_lines.append(f"📌 Số liệu vận hành ngày {ngay}:")
        context_lines.append(f"- Tổng doanh thu: {formatted_dt}")
        context_lines.append(f"- Tổng số đơn đã phục vụ: {so_don} đơn")
        if ops_context.get("ghi_chu"):
            context_lines.append(f"- Ghi chú vận hành: {ops_context.get('ghi_chu')}")

    # Fallback phân loại theo từ khóa câu nói nếu không có ops_context
    if not subject:
        req_lower = clean_req.lower()
        if any(k in req_lower for k in ("họp", "hop", "cuộc họp", "cuoc hop")):
            subject = f"[{store_name}] Thông báo lịch họp nội bộ quán"
            context_lines.append(f"📌 Nội dung cuộc họp:\n- {clean_req}")
            action_note = "- Đề nghị bạn có mặt đúng giờ và chuẩn bị sổ tay ghi chép."
        elif any(k in req_lower for k in ("đổi ca", "doi ca", "bù ca", "bu ca")):
            subject = f"[{store_name}] Thông báo về việc điều chỉnh ca làm việc"
            context_lines.append(f"📌 Chi tiết điều chỉnh:\n- {clean_req}")
            action_note = "- Vui lòng kiểm tra lại lịch ca cập nhật trên ứng dụng Nhịp Quán."
        elif any(k in req_lower for k in ("nhắc", "nhac", "đúng giờ", "dung gio", "đi làm", "di lam")):
            subject = f"[{store_name}] Nhắc nhở thời gian và nhiệm vụ ca làm việc"
            context_lines.append(f"📌 Nội dung dặn dò:\n- {clean_req}")
            action_note = "- Đề nghị bạn có mặt trước ca 10 phút để nhận bàn giao và chuẩn bị mở quán."
        else:
            subject = f"[{store_name}] Thông báo công việc từ Ban Quản Lý"
            context_lines.append(f"📌 Nội dung thông báo:\n- {clean_req}")

    details_block = "\n".join(context_lines)

    body = (
        f"{greeting_line}\n\n"
        f"Từ {store_name}, chúng tôi gửi email này để thông báo về công việc sau:\n\n"
        f"{details_block}\n\n"
        f"{action_note}\n\n"
        f"Chúc bạn một ca làm việc vui vẻ và tràn đầy năng lượng!\n\n"
        f"Trân trọng,\n"
        f"{final_sender}"
    )

    return EmailDraft(
        subject=subject,
        body=body,
        recipient_name=recip,
        tone="lich_su",
        summary=f"Bản nháp email gửi {recip}: {subject}",
        ops_context_used=ops_context,
        has_learned_style=bool(style_memory),
    )


def draft_email(
    raw_request: str,
    recipient_name: str = "Bạn",
    recipient_email: str = "",
    sender_name: str = "Ban Quản Lý Nhịp Quán",
    store_name: str = "Nhịp Quán",
    ops_context: dict[str, Any] | None = None,
    style_memory: dict[str, Any] | None = None,
    **extra: Any,
) -> EmailDraft:
    """Soạn thảo email chuyên nghiệp kết hợp Ngữ cảnh vận hành và Gu văn phong của chủ quán."""
    recip = recipient_name.strip() or "Bạn"

    if agent_mode() == "replay":
        draft = _deterministic_draft(
            raw_request,
            recip,
            sender_name,
            store_name,
            ops_context=ops_context,
            style_memory=style_memory,
        )
        draft.recipient_email = recipient_email
        return draft

    # Chuẩn bị system prompt cá nhân hóa với Tone Memory
    system_prompt = _MAIL_SYSTEM_BASE
    if style_memory:
        style_prompt = format_style_prompt(style_memory)
        if style_prompt:
            system_prompt += f"\n\n{style_prompt}"

    # Chuẩn bị prompt người dùng với Compound Context
    prompt_parts = [
        f"Yêu cầu từ Chủ quán / Quản lý: \"{raw_request}\"",
        f"Người nhận thư: {recip}",
        f"Người gửi đại diện: {sender_name}",
        f"Tên quán: {store_name}",
    ]

    if ops_context:
        prompt_parts.append("\n--- DỮ LIỆU VẬN HÀNH THỰC TẾ XÁC THỰC TỪ HỆ THỐNG (BẮT BUỘC ĐƯA VÀO EMAIL) ---")
        prompt_parts.append(json.dumps(ops_context, ensure_ascii=False, indent=2))
        prompt_parts.append("-----------------------------------------------------------------------------------")

    prompt_parts.append("\nHãy soạn thảo bức thư hoàn chỉnh, chuyên nghiệp nhất theo đúng quy chuẩn JSON.")
    prompt = "\n".join(prompt_parts)

    try:
        res = complete(prompt, system=system_prompt, temperature=0.3)
        if res.ok and res.text:
            data = parse_json_object(res.text)
            if data and data.get("subject") and data.get("body"):
                return EmailDraft(
                    subject=str(data["subject"]).strip(),
                    body=str(data["body"]).strip(),
                    recipient_name=recip,
                    recipient_email=recipient_email,
                    tone=str(data.get("tone") or "lich_su"),
                    summary=str(data.get("summary") or f"Bản nháp email gửi {recip}: {data['subject']}"),
                    ops_context_used=ops_context,
                    has_learned_style=bool(style_memory),
                )
    except Exception:
        pass

    # Fallback tất định
    draft = _deterministic_draft(
        raw_request,
        recip,
        sender_name,
        store_name,
        ops_context=ops_context,
        style_memory=style_memory,
    )
    draft.recipient_email = recipient_email
    return draft
