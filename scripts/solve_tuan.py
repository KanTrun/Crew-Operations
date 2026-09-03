#!/usr/bin/env python3
"""CLI: solve one week; inject luật hiệu lực; write data/out/lich_tuan.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "contracts" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "gates" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "solver" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "playbook" / "src"))

from ca_playbook import list_luat  # noqa: E402
from ca_solver import apply_luat, build_lich_input, solve_cpsat  # noqa: E402


def main() -> int:
    data = build_lich_input()
    data, applied = apply_luat(data, list_luat())
    result = solve_cpsat(data, time_limit_s=60.0)
    out_dir = ROOT / "data" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "nguon": "quan",
        "adr": "ADR-012",
        "tuan_iso": "2026-W01",
        "status": result.status,
        "ok": result.ok,
        "elapsed_s": round(result.elapsed_s, 3),
        "objective": result.objective,
        "violations": result.violations,
        "phan_cong": result.phan_cong,
        "debt_after": result.debt_after,
        "luat_ap_dung": applied,
    }
    (out_dir / "lich_tuan.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"solve status={result.status} ok={result.ok} "
        f"elapsed={result.elapsed_s:.2f}s violations={len(result.violations)} "
        f"luat={len(applied)}"
    )
    for v in result.violations[:20]:
        print(" ", v)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
