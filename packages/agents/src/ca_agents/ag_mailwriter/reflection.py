"""Deterministic Gmail learning reflection over persisted feedback records."""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any


REFLECTION_VERSION = "gmail-reflection-v1"
MINIMUM_EVIDENCE = 3


def _feedback_text(event: dict[str, Any], key: str) -> str:
    content = event.get(key) or {}
    return str(content.get("body") or "") if isinstance(content, dict) else ""


def _style_pattern(events: list[dict[str, Any]]) -> tuple[str, list[str]] | None:
    greeting_counts: Counter[str] = Counter()
    signoff_counts: Counter[str] = Counter()
    evidence: dict[tuple[str, str], list[str]] = {}
    for event in events:
        if event.get("type") != "manager_edit" or not event.get("materially_edited"):
            continue
        final_body = _feedback_text(event, "final")
        lines = [line.strip() for line in final_body.splitlines() if line.strip()]
        if not lines:
            continue
        greeting = lines[0] if len(lines[0]) <= 80 else ""
        signoff = lines[-1] if len(lines[-1]) <= 80 else ""
        if greeting:
            greeting_counts[greeting] += 1
            evidence.setdefault(("greeting", greeting), []).append(str(event["id"]))
        if signoff:
            signoff_counts[signoff] += 1
            evidence.setdefault(("signoff", signoff), []).append(str(event["id"]))
    candidates = [(count, "greeting", value) for value, count in greeting_counts.items()]
    candidates += [(count, "signoff", value) for value, count in signoff_counts.items()]
    if not candidates:
        return None
    count, kind, value = max(candidates, key=lambda item: (item[0], item[1], item[2]))
    if count < MINIMUM_EVIDENCE:
        return None
    text = f"Dùng lời chào '{value}' cho email nội bộ." if kind == "greeting" else f"Kết thư bằng '{value}' cho email nội bộ."
    return text, evidence[(kind, value)]


def run_gmail_reflection(
    *, store_id: str, feedback_events: list[dict[str, Any]], existing_rule_texts: set[str] | None = None
) -> dict[str, Any]:
    """Summarize feedback and suggest one pending style rule when evidence is sufficient.

    This function is intentionally pure: persistence, approval, activation, and conflict
    handling belong to the API/repository layer.
    """
    events = [event for event in feedback_events if event.get("store_id") == store_id and event.get("channel") == "gmail"]
    counts = Counter(str(event.get("type") or "unknown") for event in events)
    edited = [event for event in events if event.get("type") == "manager_edit" and event.get("materially_edited")]
    total_manager_decisions = sum(counts[kind] for kind in ("manager_approve", "manager_edit", "manager_reject"))
    proposal = None
    pattern = _style_pattern(edited)
    if pattern:
        rule_text, evidence_ids = pattern
        if rule_text not in (existing_rule_texts or set()):
            fingerprint = hashlib.sha256(f"{store_id}:{REFLECTION_VERSION}:{rule_text}:{','.join(sorted(evidence_ids))}".encode()).hexdigest()
            proposal = {
                "id": f"gmail-rule-{fingerprint[:20]}",
                "store_id": store_id,
                "channel": "gmail",
                "rule_type": "style",
                "rule": {"text": rule_text, "intent_scope": ["internal_email"], "audience_scope": ["employee"], "priority": 10},
                "evidence_count": len(evidence_ids),
                "evidence_ids": evidence_ids,
                "confidence": min(0.95, 0.6 + len(evidence_ids) * 0.1),
                "status": "pending",
                "version": 1,
                "rollout": {"mode": "none", "percentage": 0, "min_sample": 20},
                "idempotency_key": f"reflection:{fingerprint}",
            }
    return {
        "version": REFLECTION_VERSION,
        "store_id": store_id,
        "metrics": {
            "feedback_count": len(events),
            "manager_decision_count": total_manager_decisions,
            "approval_count": counts["manager_approve"],
            "edit_count": counts["manager_edit"],
            "reject_count": counts["manager_reject"],
            "send_failure_count": counts["send_failure"],
            "edit_rate": len(edited) / total_manager_decisions if total_manager_decisions else 0.0,
        },
        "proposal": proposal,
    }