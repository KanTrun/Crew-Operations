"""VF-CONFLICT — two agents disagree; never auto-pick (hồ sơ §5.5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ConflictResult:
    conflict: bool
    khong_tu_chon: bool
    a: dict[str, Any]
    b: dict[str, Any]
    reason: str


def present_conflict(a: dict[str, Any], b: dict[str, Any]) -> ConflictResult:
    """If claims differ on same (nguoi, khung), surface both. Never reconcile."""
    same_slot = (
        a.get("nguoi") == b.get("nguoi") and a.get("khung") == b.get("khung")
    )
    differ = a.get("claim") != b.get("claim")
    hit = bool(same_slot and differ)
    return ConflictResult(
        conflict=hit,
        khong_tu_chon=True,
        a=a,
        b=b,
        reason="hai_agent_trai_nhau" if hit else "khong_xung_dot",
    )
