#!/usr/bin/env python3
"""Independent hard-constraint verifier — does NOT trust solver self-report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "solver" / "src"))

from ca_solver import build_lich_input, solve_hard_only  # noqa: E402


def main() -> int:
    out = ROOT / "data" / "out" / "lich_tuan.json"
    if not out.exists():
        print("MISSING data/out/lich_tuan.json — run scripts/solve_tuan.py first")
        return 2
    payload = json.loads(out.read_text(encoding="utf-8"))
    base = build_lich_input()
    base.phan_cong = {cid: list(nvs) for cid, nvs in payload.get("phan_cong", {}).items()}
    result = solve_hard_only(base)
    print("=== VERIFY HARD (independent) ===")
    print(f"ok={result.ok}")
    for line in (
        "c01",
        "c02",
        "c03",
        "c04",
        "c05",
        "c06",
    ):
        hits = [v for v in result.violations if v.startswith(f"{line}:")]
        print(f"{line}: {len(hits)}")
        for h in hits[:5]:
            print(" ", h)
    if result.violations:
        print("TOTAL", len(result.violations))
        return 1
    print("TOTAL 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
