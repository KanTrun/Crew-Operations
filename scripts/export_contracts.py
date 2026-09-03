"""Export JSON Schema for the five contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "contracts" / "src"))

from ca_contracts import CONTRACTS  # noqa: E402

OUT = ROOT / "packages" / "contracts" / "schema"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    for name, model in CONTRACTS.items():
        schema = model.model_json_schema()
        path = OUT / f"{name}.json"
        path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
        index[name] = str(path.relative_to(ROOT)).replace("\\", "/")
    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ts = ROOT / "packages" / "contracts" / "ts" / "contracts.ts"
    ts.parent.mkdir(parents=True, exist_ok=True)
    lines = ["// Auto-generated stub types — refine with openapi-typescript in S2", ""]
    for name in CONTRACTS:
        lines.append(f"export type {name} = Record<string, unknown>;")
    ts.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", len(CONTRACTS), "schemas")


if __name__ == "__main__":
    main()
