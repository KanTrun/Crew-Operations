#!/usr/bin/env python3
"""Evaluate AG-TKB extraction on the full golden set.

Usage:
    python scripts/eval_ag_tkb.py

Prints accuracy and writes docs/metrics-18-2.md.
Accuracy = fraction of items where extracted spans exactly match golden spans.
In replay mode this will be 100% for non-blur items (perfect recall from JSON)
and 0% for blur items (intentionally degraded).
"""

from __future__ import annotations

import json
import pathlib
import sys
from datetime import date

# Allow running without install
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "packages" / "agents" / "src"))

from ca_agents.ag_tkb.extract import extract_tkb

GOLDEN_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "golden" / "tkb"
DOCS_DIR = pathlib.Path(__file__).resolve().parents[1] / "docs"


def _spans_match(extracted: list[dict], golden_khoang: list[dict]) -> bool:
    def norm(k: dict) -> tuple:
        return (k.get("thu") or k.get("day"), k.get("start"), k.get("end"))

    ex = sorted(norm(s) for s in extracted)
    go = sorted(norm(k) for k in golden_khoang)
    return ex == go


def run_eval() -> None:
    idx_path = GOLDEN_DIR / "index.json"
    if not idx_path.exists():
        print("ERROR: data/golden/tkb/index.json not found", file=sys.stderr)
        sys.exit(1)

    items = json.loads(idx_path.read_text(encoding="utf-8")).get("items", [])
    total = len(items)
    correct = 0
    blur_count = 0
    escalate_count = 0
    hard_total = 0
    hard_correct = 0
    results = []

    for item in items:
        fid = item["id"]
        golden_khoang = item.get("khoang_ban", [])
        is_hard = item.get("difficulty") == "hard" or item.get("blur")
        try:
            out = extract_tkb(fid, mode="replay")
        except Exception as exc:
            results.append({"id": fid, "ok": False, "error": str(exc)})
            continue

        if out["blur"]:
            blur_count += 1
            # Blur items: spans intentionally empty/low-conf; count as incorrect
            ok = False
        else:
            ok = _spans_match(out["spans"], golden_khoang)

        if out.get("escalate"):
            escalate_count += 1
        if is_hard:
            hard_total += 1
            if ok:
                hard_correct += 1

        if ok:
            correct += 1
        results.append({"id": fid, "ok": ok, "blur": out["blur"], "confidence": out["confidence"]})

    accuracy = correct / total if total else 0.0
    escalate_pct = escalate_count / total if total else 0.0
    hard_acc = (hard_correct / hard_total) if hard_total else 0.0
    print(
        f"AG-TKB eval: {correct}/{total} correct  "
        f"accuracy={accuracy:.2%}  blur_items={blur_count}  "
        f"escalate={escalate_pct:.1%}  hard_acc={hard_acc:.1%} ({hard_correct}/{hard_total})"
    )

    # Write metrics doc
    DOCS_DIR.mkdir(exist_ok=True)
    today = date.today().isoformat()
    metrics_path = DOCS_DIR / "metrics-18-2.md"
    clear_n = total - blur_count
    clear_acc = (correct / clear_n) if clear_n else 0.0
    metrics_path.write_text(
        f"""# AG-TKB Accuracy Metrics

| Date | Correct | Total | Accuracy | Blur items |
|------|---------|-------|----------|------------|
| {today} | {correct} | {total} | {accuracy:.2%} | {blur_count} |

- % đẩy lên người (escalate): {escalate_pct:.1%} ({escalate_count}/{total})
- Hard/blur subset accuracy: {hard_acc:.2%} ({hard_correct}/{hard_total})

## Notes

- Mode: **replay** (golden JSON, no live LLM)
- Blur items ({blur_count}) counted as incorrect (confidence < 0.7)
- Non-blur accuracy: {clear_acc:.2%} ({correct}/{clear_n})
- Replay on clear fixtures = perfect recall by design; live vision will be lower.
""",
        encoding="utf-8",
    )
    print(f"Wrote {metrics_path.name}")


if __name__ == "__main__":
    run_eval()
