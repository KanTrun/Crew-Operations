"""HTTP router: user profile (email) + mail sending."""

from __future__ import annotations

import os
import hashlib
from typing import Annotated, Any

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc

from ca_agents.ag_mail import send_mail
from ca_agents.ag_mailwriter import evaluate_gmail, feedback_diff
from ca_contracts import AIEvaluation, AIFeedbackEvent, AIGenerationRecord
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ca_api.interfaces.http.sprint3 import _require_manager
from ca_api.persist import get_user_emails, session, set_user_email
from ca_api.ai_learning.repository import AILearningRepository
from ca_api.ai_learning.operations import circuit_breaker_open

router = APIRouter(tags=["mail"])


class UpdateEmailBody(BaseModel):
    email: str = Field(min_length=3, max_length=120)


class SendMailBody(BaseModel):
    to_nv_ids: list[str] = Field(min_length=1)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    original_subject: str | None = Field(default=None, max_length=200)
    original_body: str | None = Field(default=None, max_length=5000)
    ops_context: dict[str, Any] | None = None


def execute_supervised_mail(
    *,
    store_id: str,
    actor_user_id: str,
    actor_role: str,
    to_emails: list[str],
    subject: str,
    body: str,
    html_body: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
    original_subject: str | None = None,
    original_body: str | None = None,
    ops_context: dict[str, Any] | None = None,
    prompt_version: str = "mail-send-v1",
    rule_version: str = "none",
    rollout_bucket: str = "control",
) -> dict[str, Any]:
    """Run a Gmail send through the shared safety and learning audit pipeline."""
    if circuit_breaker_open(store_id=store_id, channel="gmail"):
        raise HTTPException(status_code=503, detail="ai_circuit_breaker_open")

    gate = evaluate_gmail(recipients=to_emails, subject=subject, body=body, store_id=store_id, ops_context=ops_context)
    policy_action = {"send": "auto_send", "queue_review": "queue_review", "block": "block_polite"}[gate.action]
    now = datetime.now(UTC).isoformat()
    fingerprint = hashlib.sha256(f"{store_id}:{to_emails}:{subject}:{body}".encode()).hexdigest()
    repository = AILearningRepository()
    generation_id = f"gmail-{fingerprint[:24]}"
    repository.save(AIGenerationRecord(
        id=generation_id, store_id=store_id, channel="gmail", request_kind="gmail_request",
        draft={"subject": subject, "body": body}, context_snapshot_hash=fingerprint,
        agent_version="ag-mailwriter", prompt_version=prompt_version, rule_version=rule_version, rollout_bucket=rollout_bucket,
        model={"provider": "deterministic", "model_id": "gmail-quality-gate", "temperature": 0, "tool_context_hash": fingerprint},
        policy_action=policy_action, idempotency_key=f"generation:{fingerprint}", created_at=now,
    ))
    repository.save(AIEvaluation(
        id=f"evaluation-{fingerprint[:24]}", store_id=store_id, generation_id=generation_id,
        channel="gmail", scores=gate.scores or {}, aggregate_score=gate.score, passed=gate.passed,
        action=policy_action, hard_fail_flags=gate.hard_fail_flags, flags=gate.flags,
        threshold_version=gate.threshold_version, calibration_version="deterministic-v1", sample_count=0,
        evaluation_window=f"per_send:{gate.threshold_store_id}", evaluator="ag-mailwriter-quality-gate",
        idempotency_key=f"evaluation:{fingerprint}", created_at=now,
    ))
    original_subject = original_subject if original_subject is not None else subject
    original_body = original_body if original_body is not None else body
    diff = feedback_diff(original_subject, original_body, subject, body)
    feedback_type = "manager_edit" if diff["materially_edited"] else "manager_approve"
    if gate.action != "send":
        feedback_type = "manager_reject"
    repository.save(AIFeedbackEvent(
        id=f"feedback-{fingerprint[:24]}-{feedback_type}", store_id=store_id, generation_id=generation_id,
        channel="gmail", type=feedback_type, original=diff["original"], final=diff["final"],
        edited_fields=diff["edited_fields"], materially_edited=diff["materially_edited"], actor_user_id=actor_user_id,
        actor_role=actor_role, idempotency_key=f"{feedback_type}:{fingerprint}", created_at=now,
    ))
    if gate.action != "send":
        return {"ok": False, "mode": os.environ.get("CA_AGENT_MODE", "replay"), "reason": "quality_gate", "quality_gate": gate.__dict__, "generation_id": generation_id}

    res = send_mail(to_emails=to_emails, subject=subject, body=body, html_body=html_body, attachments=attachments)
    outcome = "send_success" if res.ok else "send_failure"
    repository.save(AIFeedbackEvent(
        id=f"feedback-{fingerprint[:24]}-{outcome}", store_id=store_id, generation_id=generation_id,
        channel="gmail", type=outcome, actor_role="system", send_status="sent" if res.ok else "failed",
        failure_code=None if res.ok else res.reason, idempotency_key=f"{outcome}:{fingerprint}", created_at=datetime.now(UTC).isoformat(),
    ))
    return {"ok": res.ok, "mode": res.mode, "sent": res.sent, "failed": res.failed, "reason": res.reason, "quality_gate": gate.__dict__, "generation_id": generation_id}


@router.get("/api/v1/me/profile")
def get_profile(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Trả profile của nick đang đăng nhập (gồm email)."""
    s = session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    return {"username": s["username"], "role": s["role"], "nv_id": s["nv_id"], "email": s.get("email", "")}


@router.patch("/api/v1/me/profile/email")
def patch_email(
    body: UpdateEmailBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Nick cập nhật gmail của chính mình (người gửi thấy email này)."""
    s = session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    try:
        from ca_api.persist import DangKyLoi

        res = set_user_email(s["username"], body.email)
    except DangKyLoi as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, **res}


@router.get("/api/v1/users/emails")
def users_emails(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Chủ/quản lý xem danh sách email nhân viên đã cập nhật (để gửi mail)."""
    _require_manager(authorization)
    return {"emails": get_user_emails()}


@router.post("/api/v1/mail/send")
def mail_send(
    body: SendMailBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Chủ/quản lý gửi email cho nhân viên theo nv_id.

    - Lấy email từ user table (nhân viên phải tự cập nhật gmail ở trang /toi).
    - Replay/stub mode: chỉ ghi log, không gửi thật (an toàn CI).
    """
    manager = _require_manager(authorization)
    current = session(authorization)
    assert current is not None
    if circuit_breaker_open(store_id=current["store_id"], channel="gmail"):
        raise HTTPException(status_code=503, detail="ai_circuit_breaker_open")
    emails_nguoi = get_user_emails()
    to_emails: list[str] = []
    missing: list[str] = []
    for nv in body.to_nv_ids:
        em = emails_nguoi.get(nv)
        if em:
            to_emails.append(em)
        else:
            missing.append(nv)

    if not to_emails:
        return {
            "ok": False,
            "mode": os.environ.get("CA_AGENT_MODE", "replay"),
            "missing": missing,
            "detail": "khong_tim_thay_email",
        }

    result = execute_supervised_mail(
        store_id=current["store_id"], actor_user_id=current["username"], actor_role=manager,
        to_emails=to_emails, subject=body.subject, body=body.body,
        original_subject=body.original_subject, original_body=body.original_body, ops_context=body.ops_context,
        rollout_bucket="active_100",
    )
    result["missing"] = missing
    return result
