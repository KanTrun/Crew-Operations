"""AG-COPILOT agent implementation — Two-phase proposal generator & Conversational Assistant."""

from __future__ import annotations

import uuid
try:
    from datetime import UTC, datetime, timedelta
except ImportError:
    from datetime import datetime, timedelta, timezone
    UTC = timezone.utc
from typing import Any

from ca_agents.ag_copilot.intent_parser import (
    OUT_OF_SCOPE,
    parse_intent,
)
from ca_agents.ag_copilot.tool_registry import (
    execute_whitelisted_tool,
)
from ca_agents.ag_supervisor import supervise_outgoing_response
from ca_contracts import (
    ActionProposal,
    ActionProposalStatus,
    CopilotIntent,
    CopilotResponse,
    copilot_role_can_use_intent,
)


def _compute_hash(data: Any) -> str:
    import hashlib
    import json
    blob = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def run_copilot(
    message: str,
    context: dict[str, Any] | None = None,
    *,
    ttl_minutes: int = 30,
) -> CopilotResponse:
    """Main AG-COPILOT entrypoint."""
    ctx = context or {}
    store_id = str(ctx.get("store_id") or "quan_01")
    user_id = str(ctx.get("user_id") or "nv_01")
    # Fail-closed: role thiếu/lạ → nhan_vien (đặc quyền thấp nhất).
    raw_role = str(ctx.get("user_role") or "").strip()
    user_role = raw_role if raw_role in ("chu_quan", "quan_ly", "nhan_vien") else "nhan_vien"

    # 1. Parse Intent & Security Filter
    parsed = parse_intent(message, ctx)

    # 1.0 Role-based intent authorization (VF-SCOPE pre-check, fail-closed).
    # Chặn TRƯỚC khi chạy tool để AI của role thấp không bao giờ thực thi
    # intent vượt quyền, kể cả khi LLM parse đúng intent đó.
    if parsed.intent != OUT_OF_SCOPE and not copilot_role_can_use_intent(
        user_role, parsed.intent
    ):
        reply = (
            "Dạ lỗi này vượt phạm vi vai trò của anh/chị. "
            "Việc này chỉ quản lý hoặc chủ quán mới có thể yêu cầu em thực hiện ạ. "
            "Anh/chị có thể nhờ quản lý duyệt giúp, hoặc hỏi em các việc trong phạm vi ca của mình."
        )
        return CopilotResponse(
            reply_text=reply,
            intent=CopilotIntent.OUT_OF_SCOPE,
            confidence=0.99,
            action_proposal=None,
            direct_answer=reply,
        )

    # 1.1 Check Prompt Injection / Bypass Approval attempts
    if parsed.security_flag == "bypass_approval_rejected":
        reply = (
            "Dạ em không thể bỏ qua bước duyệt được ạ, đây là quy định an toàn bắt buộc của hệ thống. "
            "Em vẫn có thể tạo bản nháp để anh/chị xem trước khi duyệt — anh/chị có muốn em thực hiện không ạ?"
        )
        return CopilotResponse(
            reply_text=reply,
            intent=CopilotIntent.OUT_OF_SCOPE,
            confidence=0.99,
            action_proposal=None,
            direct_answer=reply,
        )

    # 1.2 Low-confidence clarification
    if parsed.clarification_needed and parsed.clarification_question:
        return CopilotResponse(
            reply_text=parsed.clarification_question,
            intent=getattr(CopilotIntent, parsed.intent, CopilotIntent.OUT_OF_SCOPE),
            confidence=parsed.confidence,
            action_proposal=None,
            direct_answer=None,
        )

    # 1.3 Out of scope
    if parsed.intent == OUT_OF_SCOPE:
        reply = (
            "Dạ em có thể hỗ trợ anh/chị: xếp lịch tuần, duyệt đổi ca, bản tin sáng, tra cứu quy trình, "
            "báo cáo hao hụt, đề xuất luật mới và kiểm tra tồn kho. Anh/chị cần em làm gì ạ?"
        )
        return CopilotResponse(
            reply_text=reply,
            intent=CopilotIntent.OUT_OF_SCOPE,
            confidence=parsed.confidence,
            action_proposal=None,
            direct_answer=reply,
        )

    # 2. Execute Whitelisted Tool
    tool_res = execute_whitelisted_tool(parsed.intent, {**parsed.params, "store_id": store_id})

    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    expires_iso = (datetime.now(UTC) + timedelta(minutes=ttl_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot_hash = _compute_hash(tool_res.data)

    action_prop: ActionProposal | None = None
    direct_answer: str | None = None

    if tool_res.requires_confirmation:
        action_id = f"act_{uuid.uuid4().hex[:8]}"
        action_prop = ActionProposal(
            action_id=action_id,
            intent=getattr(CopilotIntent, parsed.intent),
            status=ActionProposalStatus.ready_for_approval if tool_res.success else ActionProposalStatus.draft,
            summary=tool_res.summary,
            explanation=tool_res.explanation,
            payload_diff=tool_res.data,
            requires_confirmation=True,
            store_id=store_id,
            created_by=user_id,
            confidence=parsed.confidence,
            data_snapshot_hash=snapshot_hash,
            created_at=now_iso,
            expires_at=expires_iso,
        )
        reply = f"Dạ em đã hoàn thành bước chuẩn bị: {tool_res.summary} Anh/chị xem qua và bấm duyệt để áp dụng nhé!"
    else:
        direct_answer = tool_res.summary
        reply = f"Dạ kết quả tra cứu cho anh/chị: {tool_res.summary}"

    # 3. Supervise outgoing response for safety & leaks
    sup_res = supervise_outgoing_response(message, reply)
    final_reply = sup_res.sanitized_response

    # Citations: lấy từ tool data nếu có (QUERY_SOP / survey).
    citations = list(tool_res.data.get("citations", []) or []) if isinstance(tool_res.data, dict) else []

    return CopilotResponse(
        reply_text=final_reply,
        intent=getattr(CopilotIntent, parsed.intent, CopilotIntent.OUT_OF_SCOPE),
        confidence=parsed.confidence,
        action_proposal=action_prop,
        direct_answer=direct_answer,
        citations=citations,
    )
