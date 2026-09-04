"""Human-gated HTTP controls for the AI generation/feedback learning loop."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from ca_agents.ag_fbpage_reflection import run_facebook_reflection
from ca_agents.ag_mailwriter import run_gmail_reflection
from ca_contracts import AIFeedbackEvent, AIRuleProposal
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ca_api.ai_learning.repository import AILearningRepository
from ca_api.persist import session

router = APIRouter(tags=["ai-learning"])


def _owner_session(authorization: str | None) -> dict[str, Any]:
    current = session(authorization)
    if not current:
        raise HTTPException(status_code=401, detail="thieu_token")
    if current["role"] != "chu_quan":
        raise HTTPException(status_code=403, detail="chi_chu_quan_duyet_luat")
    return current


def _manager_session(authorization: str | None) -> dict[str, Any]:
    current = session(authorization)
    if not current:
        raise HTTPException(status_code=401, detail="thieu_token")
    if current["role"] not in {"quan_ly", "chu_quan"}:
        raise HTTPException(status_code=403, detail="forbidden")
    return current


class RuleRejectBody(BaseModel):
    reason: str | None = None


class FeedbackBody(BaseModel):
    generation_id: str
    channel: Literal["gmail", "facebook"]
    type: Literal[
        "manager_approve", "manager_edit", "manager_reject", "customer_positive", "customer_negative",
        "customer_followup", "send_success", "send_failure", "manual_rating",
    ]
    original: dict[str, str] | None = None
    final: dict[str, str] | None = None
    edited_fields: list[Literal["subject", "body"]] = Field(default_factory=list)
    materially_edited: bool = False
    send_status: Literal["not_applicable", "sent", "failed"] = "not_applicable"
    failure_code: str | None = None


class CircuitBreakerBody(BaseModel):
    channel: str
    traffic_class: str = "default"
    open: bool


@router.get("/api/v1/ai/rules/proposals")
def list_rule_proposals(
    channel: str | None = None,
    status: str | None = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    current = _manager_session(authorization)
    return {"items": AILearningRepository().list_rule_proposals(store_id=current["store_id"], channel=channel, status=status)}


@router.get("/api/v1/ai/generations")
def list_generations(
    channel: str | None = None, authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    current = _manager_session(authorization)
    items = AILearningRepository().list("generation", store_id=current["store_id"], limit=200)
    return {"items": [item for item in items if channel is None or item.get("channel") == channel]}


@router.post("/api/v1/ai/feedback")
def add_feedback(body: FeedbackBody, authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    current = _manager_session(authorization)
    now = datetime.now(timezone.utc).isoformat()
    fingerprint = hashlib.sha256(f"{current['store_id']}:{body.generation_id}:{body.type}:{now}".encode()).hexdigest()
    event = AIFeedbackEvent(
        id=f"feedback-manual-{fingerprint[:24]}", store_id=current["store_id"], generation_id=body.generation_id,
        channel=body.channel, type=body.type, original=body.original, final=body.final,
        edited_fields=body.edited_fields, materially_edited=body.materially_edited, actor_user_id=current["username"],
        actor_role=current["role"], send_status=body.send_status, failure_code=body.failure_code,
        idempotency_key=f"manual:{fingerprint}", created_at=now,
    )
    return {"ok": AILearningRepository().save(event), "id": event.id}


@router.get("/api/v1/ai/evaluations/summary")
def evaluation_summary(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    current = _manager_session(authorization)
    evaluations = AILearningRepository().list("evaluation", store_id=current["store_id"], limit=200)
    feedback = AILearningRepository().list("feedback", store_id=current["store_id"], limit=200)
    average = sum(float(item.get("aggregate_score", 0)) for item in evaluations) / len(evaluations) if evaluations else 0.0
    return {"evaluation_count": len(evaluations), "average_score": average, "passed_count": sum(bool(item.get("passed")) for item in evaluations), "feedback_by_type": {kind: sum(item.get("type") == kind for item in feedback) for kind in sorted({str(item.get("type")) for item in feedback})}}


@router.get("/api/v1/ai/operations/status")
def operations_status(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    current = _manager_session(authorization)
    names = (
        "NHIPQUAN_FB_AUTO_SEND", "NHIPQUAN_FB_LEARNING_ENABLED", "NHIPQUAN_MAIL_QUALITY_GATE",
        "NHIPQUAN_MAIL_AUTO_APPROVE", "NHIPQUAN_MAIL_REFLECTION_ENABLED", "NHIPQUAN_RULE_AUTO_APPLY",
        "NHIPQUAN_AI_CIRCUIT_BREAKER", "NHIPQUAN_AI_CANARY_ENABLED",
    )
    flags = {name: os.environ.get(name, "").strip().lower() in {"1", "true", "yes"} for name in names}
    return {
        "store_id": current["store_id"], "flags": flags,
        "retention_days": max(1, int(os.environ.get("NHIPQUAN_AI_RETENTION_DAYS", "180"))),
    }


@router.post("/api/v1/ai/operations/circuit-breaker")
def set_circuit_breaker(
    body: CircuitBreakerBody, authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    current = _owner_session(authorization)
    key = f"ai_circuit_breaker:{current['store_id']}:{body.channel}:{body.traffic_class}"
    from ca_api.persist import kv_set
    kv_set(key, {"open": body.open, "updated_at": datetime.now(timezone.utc).isoformat(), "actor": current["username"]})
    return {"ok": True, "key": key, "open": body.open}


@router.get("/api/v1/ai/retention/dry-run")
def retention_dry_run(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    current = _owner_session(authorization)
    retention_days = max(1, int(os.environ.get("NHIPQUAN_AI_RETENTION_DAYS", "180")))
    cutoff = datetime.now(timezone.utc).timestamp() - retention_days * 86400
    repository = AILearningRepository()
    counts: dict[str, int] = {}
    for kind in ("generation", "feedback", "evaluation", "rule_proposal"):
        records = repository.list(kind, store_id=current["store_id"], limit=200)
        counts[kind] = sum(
            datetime.fromisoformat(str(record["created_at"]).replace("Z", "+00:00")).timestamp() < cutoff
            for record in records
        )
    return {"dry_run": True, "retention_days": retention_days, "eligible_counts": counts}


@router.post("/api/v1/ai/reflection/gmail/run")
def run_reflection(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    current = _manager_session(authorization)
    repository = AILearningRepository()
    active = repository.active_rules(store_id=current["store_id"], channel="gmail")
    report = run_gmail_reflection(
        store_id=current["store_id"],
        feedback_events=repository.list("feedback", store_id=current["store_id"], limit=200),
        existing_rule_texts={str((rule.get("rule") or {}).get("text") or "") for rule in active},
    )
    proposal_data = report.pop("proposal")
    if proposal_data:
        now = datetime.now(timezone.utc).isoformat()
        proposal_data["created_at"] = now
        proposal_data["updated_at"] = now
        proposal = AIRuleProposal.model_validate(proposal_data)
        report["proposal_saved"] = repository.save(proposal)
        report["proposal_id"] = proposal.id
    else:
        report["proposal_saved"] = False
        report["proposal_id"] = None
    return report


@router.post("/api/v1/ai/reflection/facebook/run")
def run_facebook_reflection_job(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    current = _manager_session(authorization)
    repository = AILearningRepository()
    active = repository.active_rules(store_id=current["store_id"], channel="facebook")
    report = run_facebook_reflection(
        store_id=current["store_id"],
        feedback_events=repository.list("feedback", store_id=current["store_id"], limit=200),
        existing_rule_texts={str((rule.get("rule") or {}).get("text") or "") for rule in active},
    )
    proposal_data = report.pop("proposal")
    if proposal_data:
        now = datetime.now(timezone.utc).isoformat()
        proposal_data["created_at"] = now
        proposal_data["updated_at"] = now
        proposal = AIRuleProposal.model_validate(proposal_data)
        report["proposal_saved"] = repository.save(proposal)
        report["proposal_id"] = proposal.id
    else:
        report["proposal_saved"] = False
        report["proposal_id"] = None
    return report


def _transition(proposal_id: str, target_status: str, authorization: str | None, rejection_reason: str | None = None) -> dict[str, Any]:
    current = _owner_session(authorization)
    proposal = AILearningRepository().transition_rule_proposal(
        store_id=current["store_id"], proposal_id=proposal_id, target_status=target_status,
        actor_id=current["username"], updated_at=datetime.now(timezone.utc).isoformat(),
        rejection_reason=rejection_reason,
    )
    if proposal is None:
        raise HTTPException(status_code=404, detail="khong_thay_proposal")
    return {"ok": True, "proposal": proposal}


@router.post("/api/v1/ai/rules/proposals/{proposal_id}/approve")
def approve_rule(proposal_id: str, authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    current = _owner_session(authorization)
    repository = AILearningRepository()
    proposal = repository.get_rule_proposal(store_id=current["store_id"], proposal_id=proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="khong_thay_proposal")
    conflicts = repository.rule_conflicts(proposal)
    if conflicts:
        _transition(proposal_id, "conflict_pending", authorization)
        return {"ok": False, "reason": "rule_conflict", "conflicts": [rule["id"] for rule in conflicts]}
    return _transition(proposal_id, "approved", authorization)


@router.post("/api/v1/ai/rules/proposals/{proposal_id}/activate")
def activate_rule(proposal_id: str, authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    return _transition(proposal_id, "active", authorization)


@router.post("/api/v1/ai/rules/proposals/{proposal_id}/reject")
def reject_rule(
    proposal_id: str, body: RuleRejectBody | None = None, authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    return _transition(proposal_id, "rejected", authorization, (body.reason if body else None))


@router.post("/api/v1/ai/rules/{proposal_id}/pause")
def pause_rule(proposal_id: str, authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    return _transition(proposal_id, "paused", authorization)


@router.post("/api/v1/ai/rules/{proposal_id}/rollback")
def rollback_rule(proposal_id: str, authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    return _transition(proposal_id, "rolled_back", authorization)