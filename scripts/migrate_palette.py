"""Chuyen mau PALETTE TAILWIND mac dinh sang he mau cua quan — NHIP QUAN.

VAN DE: 790 cho dung mau Tailwind mac dinh (amber/neutral/emerald/zinc/rose/
purple/red/indigo/blue...) trong khi quan da co he rieng:
  - mau trang thai `--nq-st-{ok,warn,danger,info}` + ban `-ink` de lam chu
  - mau trung tinh `--nq-ink`, `--nq-ink-muted`, `--nq-line`, `--nq-bg`, `--nq-surface`
Mau Tailwind nam NGOAI ca hai he nen khong doi theo theme, khong co ban sao cho che
do sang, va lech tong so voi charcoal am (indigo/purple la mau LANH — khong thuoc
bang mau cua quan). He qua thi giac: moi trang mot tong, dung tieu chi "1 concept
thi giac xuyen suot".

BANG ANH XA (theo VAI TRO, khong theo sac do):
  amber/yellow/orange  -> canh bao   -> --nq-st-warn / -ink / -soft
  emerald/green/lime   -> tot        -> --nq-st-ok   / -ink / -soft
  rose/red             -> nguy hiem  -> --nq-st-danger / -ink / -soft
  blue/cyan/sky/indigo -> trung tinh -> --nq-st-info / -ink / -soft
  purple/violet/pink/fuchsia -> `nhap y / y tuong` -> --nq-st-info (khong co vai
      rieng trong he; dung info de khong sinh them mau thu 5)
  neutral/zinc/gray/slate/stone -> trung tinh -> ink / ink-muted / line / bg / surface

Chay:  .venv\\Scripts\\python.exe scripts/migrate_palette.py [--dry]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "apps" / "web" / "src"

# Vai tro -> ten token trang thai
ROLE = {
    # canh bao
    "amber": "warn", "yellow": "warn", "orange": "warn",
    # tot
    "emerald": "ok", "green": "ok", "lime": "ok",
    # nguy hiem
    "rose": "danger", "red": "danger",
    # trung tinh / thong tin
    "blue": "info", "cyan": "info", "sky": "info", "indigo": "info",
    # khong co vai rieng trong he -> dung info thay vi sinh mau thu 5
    "purple": "info", "violet": "info", "pink": "info", "fuchsia": "info",
}

# Trung tinh -> token trung tinh (theo sac do: cang toi cang gan nen)
NEUTRAL_TOKENS = {
    "bg": {
        "50": "bg-[var(--nq-ink)]", "100": "bg-[var(--nq-ink)]",
        "200": "bg-[var(--nq-line-strong)]", "300": "bg-[var(--nq-line-strong)]",
        "400": "bg-[var(--nq-line-control)]", "500": "bg-[var(--nq-line-control)]",
        "600": "bg-[var(--nq-line)]", "700": "bg-[var(--nq-line)]",
        "800": "bg-[var(--nq-surface)]", "900": "bg-[var(--nq-bg-elevated)]",
        "950": "bg-[var(--nq-bg)]",
    },
    "text": {
        "50": "text-[var(--nq-ink)]", "100": "text-[var(--nq-ink)]",
        "200": "text-[var(--nq-ink)]", "300": "text-[var(--nq-ink)]",
        "400": "text-[var(--nq-ink-muted)]", "500": "text-[var(--nq-ink-muted)]",
        "600": "text-[var(--nq-ink-muted)]", "700": "text-[var(--nq-ink-muted)]",
        "800": "text-[var(--nq-ink-muted)]", "900": "text-[var(--nq-ink-muted)]",
        "950": "text-[var(--nq-ink)]",
    },
    "border": {
        "50": "border-[var(--nq-line-strong)]", "100": "border-[var(--nq-line-strong)]",
        "200": "border-[var(--nq-line-strong)]", "300": "border-[var(--nq-line-strong)]",
        "400": "border-[var(--nq-line-control)]", "500": "border-[var(--nq-line-control)]",
        "600": "border-[var(--nq-line)]", "700": "border-[var(--nq-line)]",
        "800": "border-[var(--nq-line)]", "900": "border-[var(--nq-line)]",
        "950": "border-[var(--nq-line)]",
    },
    "divide": {
        "700": "divide-[var(--nq-line)]", "800": "divide-[var(--nq-line)]",
        "900": "divide-[var(--nq-line)]",
    },
}

NEUTRAL_FAMS = "neutral|zinc|gray|grey|slate|stone"


def status_repl(util: str, role: str, shade: str, alpha: str | None) -> str:
    """Doi mot utility trang thai sang token tuong ung."""
    if util == "bg":
        # Nen dac (shade dam) -> mau trang thai; nen mo (co alpha) -> ban -soft.
        return f"bg-[var(--nq-st-{role}-soft)]" if alpha else f"bg-[var(--nq-st-{role})]"
    if util in ("text", "fill", "stroke", "decoration"):
        return f"text-[var(--nq-st-{role}-ink)]" if util == "text" else f"{util}-[var(--nq-st-{role}-ink)]"
    if util == "border":
        return f"border-[color-mix(in_srgb,var(--nq-st-{role})_46%,var(--nq-line))]"
    if util == "divide":
        return f"divide-[color-mix(in_srgb,var(--nq-st-{role})_46%,var(--nq-line))]"
    if util in ("from", "via", "to"):
        return f"{util}-[var(--nq-st-{role})]"
    if util in ("ring", "outline"):
        return f"{util}-[var(--nq-st-{role})]"
    if util in ("accent", "caret"):
        return f"{util}-[var(--nq-st-{role})]"
    return f"{util}-[var(--nq-st-{role})]"


def main() -> int:
    dry = "--dry" in sys.argv
    grand = 0

    status_pat = re.compile(
        r"(?<![-\w])(bg|text|border|divide|ring|outline|from|via|to|fill|stroke|accent|caret|decoration)"
        r"-(" + "|".join(ROLE) + r")-(\d{2,3})(/\d+)?"
    )
    neutral_pat = re.compile(
        r"(?<![-\w])(bg|text|border|divide)-(" + NEUTRAL_FAMS + r")-(\d{2,3})(/\d+)?"
    )

    for p in sorted(SRC.rglob("*.tsx")):
        orig = p.read_text(encoding="utf-8")
        lines = orig.splitlines(keepends=True)
        out: list[str] = []
        changed = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("{/*", "*", "//")):
                out.append(line)
                continue
            t = line

            def _st(m: re.Match[str]) -> str:
                nonlocal changed
                rep = status_repl(m.group(1), ROLE[m.group(2)], m.group(3), m.group(4))
                if rep != m.group(0):
                    changed += 1
                return rep

            def _nt(m: re.Match[str]) -> str:
                nonlocal changed
                util, _fam, shade = m.group(1), m.group(2), m.group(3)
                table = NEUTRAL_TOKENS.get(util)
                if not table:
                    return m.group(0)
                rep = table.get(shade)
                if rep:
                    changed += 1
                    return rep
                return m.group(0)

            t = status_pat.sub(_st, t)
            t = neutral_pat.sub(_nt, t)

            # ── Sua CAP mau chu/nen sau khi doi ──────────────────────────────
            # Bon mau trang thai deu la mau SANG (vang/xanh la/xanh duong). Khi lam
            # NEN dac, chu phai la ink toi — do duoc: vang #d4a017 + kem #f5ead8 chi
            # 1.5:1, con + ink toi #14100c dat 8.3:1. Manh `text-white` hay
            # `text-[var(--nq-ink)]` di kem nen trang thai dac la sai cap; doi sang
            # `--nq-accent-ink`. Chi ap khi trong CUNG chuoi class co nen trang thai
            # dac (khong co `-soft`).
            if re.search(r"bg-\[var\(--nq-st-\w+\)\]", t) and not re.search(
                r"bg-\[var\(--nq-st-\w+-soft\)\]", t
            ):
                t2 = re.sub(r"(?<![-\w])text-white\b", "text-[var(--nq-accent-ink)]", t)
                t2 = re.sub(
                    r"(?<![-\w])text-\[var\(--nq-ink\)\]", "text-[var(--nq-accent-ink)]", t2
                )
                if t2 != t:
                    changed += 1
                    t = t2

            out.append(t)

        new = "".join(out)
        if new != orig:
            grand += changed
            print(f"  {changed:4}  {p.relative_to(ROOT).as_posix()}")
            if not dry:
                p.write_text(new, encoding="utf-8")

    print(f"\nTONG: {grand} utility{' (DRY RUN)' if dry else ''}")
    if not dry:
        print("Kiem lai: python scripts/audit_palette_leaks.py && node scripts/contrast.mjs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
