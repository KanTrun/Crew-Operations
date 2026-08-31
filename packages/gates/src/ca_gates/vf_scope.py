"""VF-SCOPE gate: multi-tenant store_id and role-based scope authorization.

Rules:
1. store_id must match target store_id (no cross-store operations).
2. Privileged operations require appropriate role (quan_ly or chu_quan).
3. Fail-closed on mismatch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Intent permissions
_PRIVILEGED_INTENTS = {
    "SCHEDULE_SOLVE": {"quan_ly", "chu_quan"},
    "APPROVE_SHIFT_SWAP": {"quan_ly", "chu_quan"},
    "CREATE_RULE_PROPOSAL": {"quan_ly", "chu_quan"},
    "INVENTORY_RESTOCK_CHECK": {"quan_ly", "chu_quan"},
}

_PUBLIC_INTENTS = {
    "GENERATE_DAILY_BRIEF": {"nhan_vien", "quan_ly", "chu_quan"},
    "QUERY_SOP": {"nhan_vien", "quan_ly", "chu_quan"},
    "ANALYZE_WASTE": {"nhan_vien", "quan_ly", "chu_quan"},
    "OUT_OF_SCOPE": {"nhan_vien", "quan_ly", "chu_quan"},
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

    allowed_roles = _PRIVILEGED_INTENTS.get(intent, _PUBLIC_INTENTS.get(intent, {"quan_ly", "chu_quan"}))
    if caller_role not in allowed_roles:
        return ScopeResult(
            passed=False,
            blocked=True,
            reason=f"insufficient_role:{caller_role}_not_in_{sorted(allowed_roles)}",
        )

    return ScopeResult(passed=True)
