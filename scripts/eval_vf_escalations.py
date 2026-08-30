#!/usr/bin/env python3
"""#11 nhóm A — đếm escalate theo cổng VF trên fixture có chủ đích."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "gates" / "src"))

from ca_gates.vf_conf import validate_conf  # noqa: E402
from ca_gates.vf_schema import validate_schema  # noqa: E402
from ca_gates.vf_trace import validate_trace  # noqa: E402

OUT = ROOT / "docs" / "metrics-18-2.md"
GOOD = {
    "value": "Nguyen Van A",
    "label": "name",
    "source_span": {"page": 1, "x": 10.0, "y": 20.0, "w": 100.0, "h": 15.0},
    "confidence": 0.92,
}
EVIDENCE = "Nguyen Van A is the applicant listed on page 1."


def main() -> int:
    cases: list[tuple[str, object]] = [
        ("VF-SCHEMA", validate_schema({"intent": "doi_ca"}, ["intent"])),
        ("VF-SCHEMA", validate_schema({}, ["intent", "ca_id"])),
        ("VF-TRACE", validate_trace(GOOD, EVIDENCE)),
        (
            "VF-TRACE",
            validate_trace({k: v for k, v in GOOD.items() if k != "source_span"}, EVIDENCE),
        ),
        ("VF-CONF", validate_conf({"confidence": 0.92})),
        ("VF-CONF", validate_conf({"confidence": 0.45})),
        ("VF-CONF", validate_conf({})),
    ]
    counts: dict[str, int] = {}
    for gate, res in cases:
        if getattr(res, "escalate", False):
            counts[gate] = counts.get(gate, 0) + 1
    total_esc = sum(counts.values())
    print("VF escalations by gate:", counts, "total=", total_esc)
    lines = [
        "",
        "## VF escalate (fixture demo)",
        "",
        "| Cổng | Lần đẩy lên người (fixture) |",
        "|------|---------------------------|",
    ]
    for gate in ("VF-SCHEMA", "VF-TRACE", "VF-CONF"):
        lines.append(f"| {gate} | {counts.get(gate, 0)} |")
    lines.append(f"| **Tổng** | **{total_esc}** |")
    lines.append("")
    lines.append("Replay fixture — không traffic quán thật.")
    block = "\n".join(lines) + "\n"
    if OUT.exists():
        text = OUT.read_text(encoding="utf-8")
        if "## VF escalate" in text:
            text = text.split("## VF escalate")[0].rstrip()
        OUT.write_text(text + block, encoding="utf-8")
    else:
        OUT.write_text("# Metrics 18.2\n" + block, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
