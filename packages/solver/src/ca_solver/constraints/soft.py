"""Soft constraint penalty helpers (s01–s05) — used as CP-SAT objective terms."""

from __future__ import annotations

# Weights (higher = more preferred to satisfy)
W_S01_NGUYEN_VONG = 3
W_S02_WEEKEND_NIGHT = 5
W_S03_CONTIGUOUS = 2
W_S04_STABILITY = 2
W_S05_NEWBIE_PAIR = 4


def soft_ids(n: int = 5) -> list[str]:
    all_ids = ["s01", "s02", "s03", "s04", "s05"]
    return all_ids[: max(0, min(n, 5))]
