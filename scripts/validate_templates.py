from __future__ import annotations

import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "infra" / "templates"
REQUIRED = ("ma", "ten", "buoc")


def main() -> int:
    if not TEMPLATES.exists():
        print("no templates dir")
        return 0
    errors: list[str] = []
    for path in sorted(TEMPLATES.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            errors.append(f"{path.name}: root must be mapping")
            continue
        for key in REQUIRED:
            if key not in data:
                errors.append(f"{path.name}: missing '{key}'")
        buoc = data.get("buoc", [])
        if not isinstance(buoc, list) or not buoc:
            errors.append(f"{path.name}: buoc must be non-empty list")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"ok: {len(list(TEMPLATES.glob('*.yaml')))} templates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
