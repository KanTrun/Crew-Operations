"""Trợ lý Quánverse — lớp DIỄN ĐẠT câu trả lời trên brief tất định.

Nguyên tắc bất di bất dịch
------------------------
Module này KHÔNG tính toán gì về nghiệp vụ. Mọi con số đến từ
`ag_quanverse.brief` (tất định). Ở đây chỉ có hai việc:

1. **Chế độ replay (mặc định)**: trả câu trả lời dựng thẳng từ brief, không gọi
   mạng. Nhờ vậy demo, CI và máy không có API key vẫn có câu trả lời đầy đủ —
   và câu trả lời đó không thể sai số vì nó chính là brief.
2. **Chế độ live**: nhờ `ca_agents.llm.complete()` diễn đạt lại brief cho tự
   nhiên hơn. Nhưng LLM **không được** thêm số mới hay kết luận mới:

   - LLM chỉ thấy `brief` dưới dạng chữ, không thấy bản ghi thô.
   - Sau khi sinh, câu trả lời phải qua **cổng grounding**: nếu nó nhắc tới một
     con số không có trong brief, hoặc dùng từ tuyệt đối ("chắc chắn", "100%"),
     thì đánh dấu `unsupported_claims`. Khi bật mà không kiểm được gì, ta
     **rơi về câu tất định** thay vì trình bày lời LLM như sự thật.

Đây đúng khuôn `ag_spatial_memory.grounding`: câu trả lời không có căn cứ thì
phải NÓI RA là không có căn cứ, không được đội lốt kết luận.
"""

from __future__ import annotations

import re

from ca_contracts import (
    QuanverseAskResponse,
    QuanverseBrief,
    QuanversePage,
)

from ca_agents.ag_quanverse.brief import build_brief
from ca_agents.llm import agent_mode, complete

# Từ tuyệt đối — cùng tinh thần với `ag_spatial_memory.grounding._UNSUPPORTED_HINTS`.
# Brief của quán không bao giờ khẳng định tuyệt đối, nên thấy chúng là dấu hiệu
# LLM đang "nói quá" dữ liệu.
_ABSOLUTE_HINTS = (
    "chắc chắn",
    "luôn luôn",
    "không bao giờ",
    "tất cả khách",
    "100%",
    "chắc chắn rằng",
)

# Mọi số xuất hiện trong câu trả lời phải có mặt trong brief. Bắt cả số nguyên
# lẫn số thập phân (ví dụ "0.7", "12").
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")

_SYSTEM_PROMPT = (
    "Bạn là Trợ lý Quánverse của quán cà phê NHỊP QUÁN. "
    "Bạn CHỈ được diễn đạt lại các dữ kiện đã cho trong phần DỮ KIỆN. "
    "TUYỆT ĐỐI không thêm con số mới, không suy đoán kết luận mới, "
    "không dùng từ tuyệt đối như 'chắc chắn', 'luôn luôn', '100%'. "
    "Nếu DỮ KIỆN trống hoặc không đủ để trả lời, hãy nói thẳng là chưa có dữ liệu. "
    "Trả lời bằng tiếng Việt, ngắn gọn (tối đa 4 câu), không markdown."
)


def _brief_as_text(brief: QuanverseBrief) -> str:
    """Chuyển brief thành ngữ cảnh chữ cho LLM — CHỈ dữ kiện, không bản ghi thô."""
    lines: list[str] = [f"Trang: {brief.page.value}", f"Tóm tắt: {brief.headline}"]
    if brief.metrics:
        lines.append("Chỉ số:")
        for m in brief.metrics:
            value = "chưa có dữ liệu" if m.value is None else m.value
            lines.append(f"- {m.label}: {value}{(' ' + m.unit) if m.unit else ''}")
    if brief.facts:
        lines.append("Dữ kiện:")
        lines.extend(f"- {f}" for f in brief.facts)
    if brief.risks:
        lines.append("Rủi ro:")
        lines.extend(f"- {r}" for r in brief.risks)
    if brief.next_actions:
        lines.append("Việc nên làm:")
        lines.extend(f"- {a}" for a in brief.next_actions)
    return "\n".join(lines)


def _numbers_in(text: str) -> set[str]:
    """Tập số xuất hiện trong một đoạn chữ (đã bỏ dấu phân cách nghìn)."""
    found: set[str] = set()
    for raw in _NUMBER_RE.findall(text):
        found.add(raw.replace(",", "").replace(".", ""))
        found.add(raw.replace(",", "."))
    return found


def audit_answer(answer: str, brief: QuanverseBrief) -> list[str]:
    """Cổng grounding: trả danh sách claim KHÔNG được dữ liệu hậu thuẫn.

    Rỗng nghĩa là câu trả lời chỉ nói lại điều brief đã có. Không rỗng nghĩa là
    LLM đã thêm số hoặc khẳng định quá mức — lớp gọi phải xử lý (ở đây là rơi
    về bản tất định).
    """
    problems: list[str] = []
    low = answer.lower()
    for hint in _ABSOLUTE_HINTS:
        if hint in low:
            problems.append(f"khẳng định tuyệt đối không có trong dữ kiện: {hint}")

    allowed = _numbers_in(_brief_as_text(brief))
    for number in _numbers_in(answer):
        if number not in allowed:
            problems.append(f"con số không có trong dữ kiện: {number}")
    return problems


def _deterministic_answer(question: str, brief: QuanverseBrief) -> str:
    """Câu trả lời dựng thẳng từ brief — dùng cho replay và làm lưới an toàn.

    Không tra cứu từ khoá trong câu hỏi rồi bịa: chỉ trả phần dữ kiện liên quan
    nhất, và nói rõ khi không có gì để nói.
    """
    if not brief.facts and not brief.metrics:
        return (
            "Chưa có dữ liệu cho trang này nên tôi chưa thể trả lời. "
            "(Không suy đoán nội dung.)"
        )

    parts: list[str] = [brief.headline + "."]
    if brief.risks:
        parts.append("Điểm cần chú ý: " + "; ".join(brief.risks[:3]) + ".")
    if brief.facts:
        parts.append("Chi tiết: " + "; ".join(brief.facts[:4]) + ".")
    if brief.next_actions:
        parts.append("Việc nên làm: " + "; ".join(brief.next_actions[:3]) + ".")
    return " ".join(parts)


def answer_question(
    *,
    page: QuanversePage,
    question: str,
    brief: QuanverseBrief | None = None,
    payload: dict[str, object] | None = None,
) -> QuanverseAskResponse:
    """Trả lời một câu hỏi gắn với một trang Quánverse.

    `brief` có thể truyền sẵn (router đã dựng) hoặc để hàm tự dựng từ `payload`.
    Truyền sẵn là đường chính: bảo đảm bản tóm tắt trên màn hình và ngữ cảnh của
    câu trả lời là CÙNG một khối.
    """
    if brief is None:
        brief = build_brief(page, **(payload or {}))

    provider = "replay"
    answer = _deterministic_answer(question, brief)
    unsupported: list[str] = []

    # Chỉ gọi LLM khi thật sự ở chế độ live. Replay phải tất định và không mạng.
    if agent_mode() == "live" and (brief.facts or brief.metrics):
        result = complete(
            system=_SYSTEM_PROMPT,
            user=f"DỮ KIỆN:\n{_brief_as_text(brief)}\n\nCÂU HỎI: {question}",
            task="text:quanverse_ask",
            json_mode=False,
        )
        if result.ok and result.text.strip():
            violations = audit_answer(result.text, brief)
            if violations:
                # LLM nói quá dữ liệu → KHÔNG trình bày như sự thật. Giữ bản tất
                # định và ghi lại lý do để UI có thể hiển thị minh bạch.
                unsupported = violations
                provider = f"replay:chan_{result.provider}"
            else:
                answer = result.text.strip()
                provider = result.provider
        else:
            # Provider chết/hết quota là chuyện thường — rơi về tất định, KHÔNG
            # báo lỗi cho người dùng khi bản tất định đã đầy đủ.
            provider = f"replay:khong_co_{result.provider or 'llm'}"

    citations = list(dict.fromkeys(brief.grounded_refs))  # giữ thứ tự, bỏ trùng
    grounded = bool(citations)
    if not grounded:
        # Không có bản ghi nào để dẫn chứng → câu trả lời PHẢI nói rõ điều đó,
        # kể cả khi brief có vài chỉ số bằng 0. Nếu không, người đọc sẽ tưởng
        # "hệ thống đã kiểm tra và kết luận", trong khi thực ra không có dữ liệu.
        answer = (
            "Chưa có bản ghi nào ở trang này để dẫn chứng nên tôi chưa thể kết luận. "
            "(Không suy đoán nội dung.)"
        )

    return QuanverseAskResponse(
        page=page,
        question=question,
        answer=answer,
        brief=brief,
        citations=citations,
        unsupported_claims=unsupported,
        grounded=grounded,
        provider=provider,
    )
