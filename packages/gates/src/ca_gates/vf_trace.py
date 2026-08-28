"""VF-TRACE gate: every extraction must have a traceable source span.

A valid source span is one of:
  - Spatial:    {"page": int, "x": float, "y": float, "w": float, "h": float}
  - Text-offset: {"text_offset": int}  — offset must exist within evidence string/list.

Decision logic:
- Span present AND verifiable in evidence → pass
- Span absent or unverifiable → escalate immediately (no retry; traceability is non-negotiable)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TraceResult:
    passed: bool
    escalate: bool = False
    reason: str = ""


_SPATIAL_KEYS = {"page", "x", "y", "w", "h"}


def _has_spatial_span(span: dict[str, Any]) -> bool:
    return _SPATIAL_KEYS.issubset(span.keys())


def _has_text_offset(span: dict[str, Any]) -> bool:
    return "text_offset" in span


def _offset_in_evidence(offset: int, evidence: str | list[str]) -> bool:
    if isinstance(evidence, list):
        # treat list as joined text; offset indexes into the concatenation
        joined = " ".join(evidence)
    else:
        joined = evidence
    return 0 <= offset < len(joined)


def validate_trace(
    extraction: dict[str, Any],
    evidence: str | list[str] | dict[str, Any],
) -> TraceResult:
    """Check that *extraction* carries a valid source span traceable in *evidence*.

    Args:
        extraction: Must contain a "source_span" key.
        evidence: Raw evidence — string, list of strings, or a dict with a
                  "text" key used for text-offset validation.

    Returns:
        TraceResult with decision flags.
    """
    span = extraction.get("source_span")

    if span is None:
        return TraceResult(
            passed=False,
            escalate=True,
            reason="Missing 'source_span' in extraction",
        )

    if not isinstance(span, dict):
        return TraceResult(
            passed=False,
            escalate=True,
            reason=f"'source_span' must be a dict, got {type(span).__name__}",
        )

    # Spatial span — just check all keys present (coordinates are self-evidencing)
    if _has_spatial_span(span):
        return TraceResult(passed=True)

    # Text-offset span — verify offset is within evidence bounds
    if _has_text_offset(span):
        offset = span["text_offset"]
        if not isinstance(offset, int):
            return TraceResult(
                passed=False,
                escalate=True,
                reason=f"'text_offset' must be int, got {type(offset).__name__}",
            )

        # Resolve evidence text
        if isinstance(evidence, dict):
            ev_text = evidence.get("text", "")
        else:
            ev_text = evidence

        if _offset_in_evidence(offset, ev_text):
            return TraceResult(passed=True)

        return TraceResult(
            passed=False,
            escalate=True,
            reason=f"text_offset {offset} is out of bounds for evidence (len={len(ev_text) if isinstance(ev_text, str) else sum(len(s) for s in ev_text) + len(ev_text) - 1})",  # noqa: E501
        )

    return TraceResult(
        passed=False,
        escalate=True,
        reason=f"'source_span' has neither spatial keys {_SPATIAL_KEYS} nor 'text_offset'",
    )
