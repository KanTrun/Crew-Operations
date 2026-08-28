#!/usr/bin/env python3
"""Merge hard_cases into messages.jsonl — giữ 200 dòng, ~40% hard."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "data" / "golden" / "messages"
MAIN = GOLDEN / "messages.jsonl"
HARD = GOLDEN / "hard_cases.jsonl"
META = GOLDEN / "meta.json"


def main() -> None:
    easy = [
        json.loads(line)
        for line in MAIN.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    hard = [
        json.loads(line)
        for line in HARD.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    # Giữ 120 easy đầu (cân bằng intent), thay 80 cuối bằng hard
    head = easy[:120]
    tail_hard = []
    for i, row in enumerate(hard[:80]):
        tail_hard.append(
            {
                "id": f"msg_{121 + i:03d}",
                "text": row["text"],
                "intent": row["intent"],
                "annotator_a": row.get("annotator_a", row["intent"]),
                "annotator_b": row.get("annotator_b", row["intent"]),
                "synthetic": True,
                "difficulty": row.get("difficulty", "hard"),
            }
        )
    out = head + tail_hard
    if len(out) != 200:
        raise SystemExit(f"expected 200 rows, got {len(out)}")
    MAIN.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n",
        encoding="utf-8",
    )
    n_hard = sum(1 for r in out if r.get("difficulty") in {"hard", "medium"})
    META.write_text(
        json.dumps(
            {
                "n": len(out),
                "n_hard_or_medium": n_hard,
                "note": "120 easy + 80 hard/medium từ hard_cases.jsonl — không chỉ keyword dễ",
                "synthetic": True,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(out)} messages ({n_hard} hard/medium)")


if __name__ == "__main__":
    main()
