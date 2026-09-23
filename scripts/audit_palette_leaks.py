"""Kiem tra mau PALETTE TAILWIND con sot ngoai he mau cua quan.

VI SAO: quan co he mau rieng (charcoal am + copper) va he trang thai rieng
(`--nq-st-*`). Mau Tailwind mac dinh (indigo, purple, amber, zinc, slate...) nam
ngoai ca hai he, nen:
  - khong doi theo theme, khong co ban sao cho che do sang,
  - lech tong so voi charcoal am (indigo/purple la mau LANH, khong thuoc bang mau),
  - va thuong truot nguong tuong phan vi chung duoc chon cho nen sang.
Script liet ke moi cho con dung de sua theo token tuong ung.

Chay:  .venv\\Scripts\\python.exe scripts/audit_palette_leaks.py
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "apps" / "web" / "src"

# Ten ho mau mac dinh cua Tailwind (tru mau trung tinh da duoc thay bang token).
FAMILIES = [
    "indigo", "purple", "violet", "fuchsia", "pink", "rose", "red", "orange",
    "amber", "yellow", "lime", "green", "emerald", "teal", "cyan", "sky",
    "blue", "slate", "gray", "grey", "zinc", "neutral", "stone",
]

# Mau cua he: `--nq-*` khong tinh. `white`/`black` tinh la ngoai he khi lam chu/vien.
PAT = re.compile(
    r"(?<![-\w])(?:bg|text|border|from|via|to|ring|outline|shadow|fill|stroke|decoration|divide|accent|caret)"
    r"-(" + "|".join(FAMILIES) + r")-(\d{2,3})(/\d+)?"
)


def main() -> int:
    by_family: Counter[str] = Counter()
    by_file: dict[str, list[str]] = {}

    for p in sorted(SRC.rglob("*.tsx")):
        lines = p.read_text(encoding="utf-8").splitlines()
        hits: list[str] = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(("{/*", "*", "//")):
                continue
            for m in PAT.finditer(line):
                by_family[m.group(1)] += 1
                hits.append(f"  {i:5}  {m.group(0):28} {stripped[:78]}")
        if hits:
            by_file[p.relative_to(SRC).as_posix()] = hits

    total = sum(by_family.values())
    print(f"== Mau Tailwind mac dinh con sot: {total} ==\n")
    print("Theo ho mau:")
    for fam, n in by_family.most_common():
        print(f"  {fam:10} {n:3}")
    print()
    for rel, hits in sorted(by_file.items(), key=lambda kv: -len(kv[1])):
        print(f"{rel}  ({len(hits)})")
        for h in hits[:10]:
            print(h)
        if len(hits) > 10:
            print(f"  ... va {len(hits) - 10} cho nua")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
