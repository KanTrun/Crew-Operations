"""VF-SCHEMA gate: validate extraction dict against required keys.

Decision logic:
- All required keys present → pass
- Missing keys, first occurrence → fail with retry_once=True
- Missing keys, already retried → escalate
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SchemaResult:
    passed: bool
    missing_keys: list[str] = field(default_factory=list)
    retry_once: bool = False
    escalate: bool = False
    reason: str = ""


def validate_schema(
    extraction: dict[str, Any],
    required_keys: list[str],
    *,
    already_retried: bool = False,
) -> SchemaResult:
    """Validate *extraction* has all *required_keys*.

    Args:
        extraction: The extraction dict to validate.
        required_keys: Keys that must be present.
        already_retried: True if this extraction has already been retried once.

    Returns:
        SchemaResult with decision flags.
    """
    missing = [k for k in required_keys if k not in extraction]

    if not missing:
        return SchemaResult(passed=True)

    reason = f"Missing required keys: {missing}"

    if already_retried:
        return SchemaResult(
            passed=False,
            missing_keys=missing,
            retry_once=False,
            escalate=True,
            reason=reason + " (escalated after retry)",
        )

    return SchemaResult(
        passed=False,
        missing_keys=missing,
        retry_once=True,
        escalate=False,
        reason=reason,
    )
