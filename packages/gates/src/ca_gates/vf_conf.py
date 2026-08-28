"""VF-CONF gate: confidence check with mandatory human escalation.

Rule: if confidence < threshold → ALWAYS escalate to human. No retry.

Also provides `blur_case` helper: derives confidence from a blur_score where
lower blur_score means more blur (less confidence).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_THRESHOLD = 0.7


@dataclass
class ConfResult:
    passed: bool
    confidence: float
    escalate: bool = False
    reason: str = ""


def validate_conf(
    extraction: dict[str, Any],
    *,
    threshold: float = DEFAULT_THRESHOLD,
    confidence_key: str = "confidence",
) -> ConfResult:
    """Check that *extraction[confidence_key]* >= *threshold*.

    If confidence is absent or below threshold → escalate=True, no retry.

    Args:
        extraction: Extraction dict that should carry a confidence score.
        threshold: Minimum acceptable confidence (default 0.7).
        confidence_key: Key name for confidence value (default "confidence").

    Returns:
        ConfResult with decision flags.
    """
    raw = extraction.get(confidence_key)

    if raw is None:
        return ConfResult(
            passed=False,
            confidence=0.0,
            escalate=True,
            reason=f"Missing '{confidence_key}' in extraction — cannot assess confidence",
        )

    try:
        conf = float(raw)
    except (TypeError, ValueError):
        return ConfResult(
            passed=False,
            confidence=0.0,
            escalate=True,
            reason=f"'{confidence_key}' value {raw!r} is not numeric",
        )

    if conf < threshold:
        return ConfResult(
            passed=False,
            confidence=conf,
            escalate=True,
            reason=f"Confidence {conf:.3f} < threshold {threshold:.3f} — human review required",
        )

    return ConfResult(passed=True, confidence=conf)


# ---------------------------------------------------------------------------
# blur_case helper
# ---------------------------------------------------------------------------

def blur_case(blur_score: float, *, max_blur: float = 100.0) -> float:
    """Convert a *blur_score* (higher = sharper) to a confidence in [0, 1].

    The mapping is linear: confidence = blur_score / max_blur, clamped to [0, 1].

    Args:
        blur_score: Raw blur metric (e.g. Laplacian variance). Higher = sharper.
        max_blur: Score considered "fully sharp" (default 100.0).

    Returns:
        Confidence in [0.0, 1.0].
    """
    if max_blur <= 0:
        raise ValueError(f"max_blur must be positive, got {max_blur}")
    return max(0.0, min(1.0, blur_score / max_blur))
