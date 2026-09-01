"""VF-SCOPE gate: multi-tenant store_id and role-based scope authorization.

Rules:
1. store_id must match target store_id (no cross-store operations).
2. Privileged operations require appropriate role (quan_ly or chu_quan).
3. Fail-closed on mismatch.
4. Role→Intent permissions derive from COPILOT_ROLE_INTENT_MATRIX (contracts)
   — single source of truth, fail-closed for unknown roles/intents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ca_contracts import (
    COPILOT_ROLE_INTENT_MATRIX,
    copilot_intents_allowed_for_role,
)

# Intent permissions — derived from the single-source matrix in contracts.
# Kept as module-level names for backward compatibility with existing imports.
_PRIVILEGED_INTENTS: dict[str, frozenset[str]] = {
    intent: {
        role
        for role, intents in COPILOT_ROLE_INTENT_MATRIX.items()
        if intent in intents
    }
    for intent in (
        "SCHEDULE_SOLVE",
        "APPROVE_SHIFT_SWAP",
        "CREATE_RULE_PROPOSAL",
        "INVENTORY_RESTOCK_CHECK",
    )
}

_PUBLIC_INTENTS: dict[str, frozenset[str]] = {
    intent: {
        role
        for role, intents in COPILOT_ROLE_INTENT_MATRIX.items()
        if intent in intents
    }
    for intent in (
        "GENERATE_DAILY_BRIEF",
        "QUERY_SOP",
        "ANALYZE_WASTE",
        "OUT_OF_SCOPE",
    )
}


@dataclass
class ScopeResult:
    passed: bool
    blocked: bool = False
    reason: str = ""


def validate_scope(
    *,
    caller_store_id: str,
    target_store_id: str,
    caller_role: str,
    intent: str,
    action_created_by: str | None = None,
    caller_user_id: str | None = None,
) -> ScopeResult:
    """Validate that caller has authority for the store and intent."""
    if not caller_store_id or not target_store_id:
        return ScopeResult(
            passed=False,
            blocked=True,
            reason="missing_store_id",
        )

    if caller_store_id != target_store_id:
        return ScopeResult(
            passed=False,
            blocked=True,
            reason=f"cross_store_forbidden:{caller_store_id}!={target_store_id}",
        )

    # Role→Intent từ ma trận single-source trong contracts.
    allowed_roles = {
        role
        for role, intents in COPILOT_ROLE_INTENT_MATRIX.items()
        if intent in intents
    }
    if not allowed_roles:
        # Fail-closed: intent không có trong ma trận → không ai được gọi.
        return ScopeResult(
            passed=False,
            blocked=True,
            reason=f"unknown_intent:{intent}",
        )
    if caller_role not in allowed_roles:
        return ScopeResult(
            passed=False,
            blocked=True,
            reason=f"insufficient_role:{caller_role}_not_in_{sorted(allowed_roles)}",
        )

    return ScopeResult(passed=True)
