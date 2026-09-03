"""VF-STALE gate: verify data snapshot hash has not diverged between draft and confirm.

Rules:
1. When creating a draft ActionProposal, orchestrator computes a snapshot hash of underlying data.
2. At confirm time (execute-action), orchestrator recalculates current data snapshot hash.
3. If current_hash != draft_snapshot_hash -> fail closed with stale_rejected.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class StaleResult:
    passed: bool
    stale: bool = False
    reason: str = ""


def compute_snapshot_hash(data: Any) -> str:
    """Compute deterministic SHA256 digest of data payload."""
    blob = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def validate_stale(
    *,
    draft_snapshot_hash: str,
    current_snapshot_hash: str,
) -> StaleResult:
    """Compare draft snapshot hash with current snapshot hash."""
    if not draft_snapshot_hash:
        # If no snapshot hash was tracked, pass with notice
        return StaleResult(passed=True)

    if draft_snapshot_hash != current_snapshot_hash:
        return StaleResult(
            passed=False,
            stale=True,
            reason=f"data_stale_mismatch:draft={draft_snapshot_hash}_current={current_snapshot_hash}",
        )

    return StaleResult(passed=True)
