"""Evidence read model — bằng chứng cho một candidate (timeline, actors, shifts).

Chỉ đọc qua contracts/events — không query KV internals từ agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ca_contracts import RuleCandidate


@dataclass
class EvidenceTimeline:
    """Timeline bằng chứng của một candidate."""

    candidate_id: str = ""
    events: list[dict[str, Any]] = field(default_factory=list)
    repeated_decisions: int = 0
    actors: list[str] = field(default_factory=list)
    affected_shifts: list[str] = field(default_factory=list)
    counterexamples: list[str] = field(default_factory=list)
    confidence: float = 0.0


def build_evidence_readmodel(
    candidate: RuleCandidate,
    decision_events: list[dict[str, Any]],
) -> EvidenceTimeline:
    """Dựng read-model bằng chứng từ sự kiện — chú thích nguồn fixture."""
    events = [
        ev for ev in decision_events if ev.get("event_id") in candidate.evidence_refs
    ]
    actors = sorted({str(ev.get("actor_id") or "") for ev in events if ev.get("actor_id")})
    shifts = sorted(
        {
            str(ev.get("payload", {}).get("shift_id") or "")
            for ev in events
            if ev.get("payload", {}).get("shift_id")
        }
    )
    return EvidenceTimeline(
        candidate_id=candidate.candidate_id,
        events=events,
        repeated_decisions=len(events),
        actors=actors,
        affected_shifts=shifts,
        counterexamples=list(candidate.counterexample_refs),
        confidence=candidate.confidence,
    )