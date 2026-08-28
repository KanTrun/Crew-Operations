"""VF-NUM — every number in a sentence must exist in source data."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_NUM = re.compile(r"\d+(?:[.,]\d+)?")


@dataclass
class NumResult:
    passed: bool
    numbers: list[str]
    missing: list[str]
    reason: str = ""


def validate_num(text: str, allowed: set[str] | list[Any]) -> NumResult:
    pool = {str(x).replace(",", ".") for x in allowed}
    found = _NUM.findall(text or "")
    missing = []
    for raw in found:
        key = raw.replace(",", ".")
        if key not in pool and raw not in pool:
            missing.append(raw)
    ok = not missing
    return NumResult(
        passed=ok,
        numbers=found,
        missing=missing,
        reason="" if ok else "so_khong_co_trong_du_lieu",
    )
