#!/usr/bin/env python3
"""Confusion matrix AG-MSG on golden 200 messages — honest numbers."""

from __future__ import annotations

import json
import pathlib
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "packages" / "agents" / "src"))

from ca_agents.ag_msg import INTENTS, classify

ROOT = pathlib.Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "data" / "golden" / "messages" / "messages.jsonl"
DOCS = ROOT / "docs" / "metrics-18-2.md"


def main() -> None:
    rows = [
        json.loads(line)
        for line in GOLDEN.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    gold = [r["intent"] for r in rows]
    pred = [classify(r["text"]).intent for r in rows]
    n = len(rows)
    correct = sum(g == p for g, p in zip(gold, pred, strict=True))
    hard_rows = [r for r in rows if r.get("difficulty") in {"hard", "medium"}]
    hard_n = len(hard_rows)
    hard_ok = sum(
        classify(r["text"]).intent == r["intent"] for r in hard_rows
    )
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for g, p in zip(gold, pred, strict=True):
        matrix[g][p] += 1
    acc = correct / n if n else 0
    hard_acc = (hard_ok / hard_n) if hard_n else 0
    print(f"AG-MSG: {correct}/{n} accuracy={acc:.2%} hard={hard_ok}/{hard_n} ({hard_acc:.2%})")
    lines = [
        "",
        "## AG-MSG confusion (Sprint 3)",
        "",
        "| Date | Correct | Total | Accuracy |",
        "|------|---------|-------|----------|",
        f"| {date.today().isoformat()} | {correct} | {n} | {acc:.2%} |",
        "",
        f"Hard/medium subset: {hard_ok}/{hard_n} = {hard_acc:.2%}",
        "",
        "Golden gồm ~40% hard/medium (`hard_cases.jsonl`). Classifier keyword tier-1; "
        "unmatched → `khac`. Replay only, no live network.",
        "",
        "| gold \\ pred | " + " | ".join(INTENTS) + " |",
        "|---" * (len(INTENTS) + 1) + "|",
    ]
    for g in INTENTS:
        cells = [str(matrix[g][p]) for p in INTENTS]
        lines.append(f"| {g} | " + " | ".join(cells) + " |")
    existing = DOCS.read_text(encoding="utf-8") if DOCS.exists() else "# Metrics 18.2\n"
    if "## AG-MSG" in existing:
        head = existing.split("## AG-MSG")[0].rstrip()
        DOCS.write_text(head + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    else:
        DOCS.write_text(existing.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
