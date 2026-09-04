"""Deterministic rollout selection for owner-approved learning rules."""

from __future__ import annotations

import hashlib
from typing import Any


def select_active_rules(
    rules: list[dict[str, Any]], *, store_id: str, identity: str,
) -> tuple[list[dict[str, Any]], str]:
    """Select active rules using a stable per-store recipient/conversation bucket.

    Rules without an explicit canary configuration retain the existing 100% behavior.
    """
    normalized_identity = identity.strip() or "default"
    digest = hashlib.sha256(f"{store_id}:{normalized_identity}".encode()).digest()
    bucket = int.from_bytes(digest[:8], "big") % 100
    selected: list[dict[str, Any]] = []
    rollout_bucket = "control"

    for rule in rules:
        rollout = rule.get("rollout") or {}
        if str(rollout.get("mode") or "active") != "canary":
            selected.append(rule)
            rollout_bucket = "active_100"
            continue
        percentage = max(0, min(100, int(rollout.get("percentage") or 0)))
        if bucket < percentage:
            selected.append(rule)
            rollout_bucket = "canary_10" if percentage <= 10 else "canary_50"

    return selected, rollout_bucket