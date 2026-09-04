"""Deterministic Facebook learning reflection over persisted feedback records."""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any

REFLECTION_VERSION = "facebook-reflection-v1"
MINIMUM_EVIDENCE = 3


def run_facebook_reflection(
    *, store_id: str, feedback_events: list[dict[str, Any]], existing_rule_texts: set[str] | None = None,
) -> dict[str, Any]:
    """Suggest one pending reply-style rule from repeated manager edits.

    Persistence and human approval deliberately remain at the API boundary.
    """
    events = [event for event in feedback_events if event.get("store_id") == store_id and event.get("channel") == "facebook"]
    edited = [event for event in events if event.get("type") == "manager_edit" and event.get("materially_edited")]
    openings: Counter[str] = Counter()
    evidence: dict[str, list[str]] = {}
    for event in edited:
        final = event.get("final") or {}
        body = str(final.get("body") or "") if isinstance(final, dict) else ""
        opening = next((line.strip() for line in body.splitlines() if line.strip()), "")
        if opening and len(opening) <= 100:
            openings[opening] += 1
            evidence.setdefault(opening, []).append(str(event["id"]))

    proposal = None
    if openings:
        opening, count = max(openings.items(), key=lambda item: (item[1], item[0]))
        rule_text = f"Mở đầu phản hồi khách bằng '{opening}' khi phù hợp ngữ cảnh."
        evidence_ids = evidence[opening]
        if count >= MINIMUM_EVIDENCE and rule_text not in (existing_rule_texts or set()):
            fingerprint = hashlib.sha256(
                f"{store_id}:{REFLECTION_VERSION}:{rule_text}:{','.join(sorted(evidence_ids))}".encode()
            ).hexdigest()
            proposal = {
                "id": f"facebook-rule-{fingerprint[:20]}", "store_id": store_id,
                "channel": "facebook", "rule_type": "style",
                "rule": {"text": rule_text, "intent_scope": ["customer_reply"], "audience_scope": ["customer"], "priority": 10},
                "evidence_count": len(evidence_ids), "evidence_ids": evidence_ids,
                "confidence": min(0.95, 0.6 + len(evidence_ids) * 0.1),
                "status": "pending", "version": 1,
                "rollout": {"mode": "none", "percentage": 0, "min_sample": 20},
                "idempotency_key": f"reflection:{fingerprint}",
            }

    counts = Counter(str(event.get("type") or "unknown") for event in events)
    decisions = sum(counts[kind] for kind in ("manager_approve", "manager_edit", "manager_reject"))
    return {
        "version": REFLECTION_VERSION, "store_id": store_id,
        "metrics": {
            "feedback_count": len(events), "manager_decision_count": decisions,
            "approval_count": counts["manager_approve"], "edit_count": counts["manager_edit"],
            "reject_count": counts["manager_reject"], "customer_negative_count": counts["customer_negative"],
            "edit_rate": len(edited) / decisions if decisions else 0.0,
        },
        "proposal": proposal,
    }