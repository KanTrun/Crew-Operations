"""Audit nhất quán UI/UX — NHỊP QUÁN.

Đếm và phân loại các vi phạm design system trong apps/web:
  - màu Tailwind ngoài token (amber-500, blue-400...)
  - mã hex trần trong .tsx
  - scale chữ rời rạc (font-size lẻ trong CSS)
  - emoji dùng làm icon
  - giá trị spacing ngoài thang --nq-s*

Chạy:  python scripts/audit_ui_consistency.py [--json]
Mục đích: sinh số liệu cho bảng before/after, KHÔNG sửa gì.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web" / "src"

TAILWIND_PALETTE = re.compile(
    r"\b(?:bg|text|border|ring|from|to|via|fill|stroke|shadow|outline|divide|decoration|accent|caret)"
    r"-(?:amber|blue|green|red|slate|zinc|gray|grey|emerald|violet|indigo|purple|sky|teal|cyan|orange|rose|yellow|lime|pink|fuchsia|stone|neutral)-\d{2,3}\b"
)
# Hex trần trong JSX/TS (bỏ qua chuỗi token hợp lệ trong lib màu).
RAW_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
EMOJI = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U00002b00-\U00002bff\U0000fe0f\U00002190-\U000021ff\U00002700-\U000027bf]"
)
FONT_SIZE = re.compile(r"font-size:\s*([0-9.]+)rem")
SPACING = re.compile(r"(?:margin|padding|gap)(?:-[a-z]+)?:\s*([0-9.]+)rem")

# File được phép chứa hex: nơi định nghĩa token / bảng màu có chủ đích.
HEX_ALLOWLIST = {
    "lib/ops-pulse.ts",
    "app/globals.css",
    "app/experience.css",
    "ui/fonts.ts",
}


def rel(p: Path) -> str:
    return p.relative_to(WEB).as_posix()


def collect(exts: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for ext in exts:
        out.extend(sorted(WEB.rglob(f"*{ext}")))
    return [p for p in out if p.is_file()]


def audit_tailwind() -> dict[str, object]:
    per_file: Counter[str] = Counter()
    per_color: Counter[str] = Counter()
    for p in collect((".tsx", ".ts")):
        text = p.read_text(encoding="utf-8")
        for m in TAILWIND_PALETTE.finditer(text):
            per_file[rel(p)] += 1
            per_color[m.group(0).split("-")[-2] if False else m.group(0)] += 1
    return {
        "total": sum(per_file.values()),
        "files": per_file.most_common(),
        "classes": per_color.most_common(20),
    }


def audit_hex() -> dict[str, object]:
    per_file: Counter[str] = Counter()
    for p in collect((".tsx", ".ts")):
        r = rel(p)
        if r in HEX_ALLOWLIST:
            continue
        text = p.read_text(encoding="utf-8")
        n = len(RAW_HEX.findall(text))
        if n:
            per_file[r] = n
    return {"total": sum(per_file.values()), "files": per_file.most_common()}


def audit_emoji() -> dict[str, object]:
    per_file: Counter[str] = Counter()
    samples: dict[str, list[str]] = defaultdict(list)
    for p in collect((".tsx",)):
        r = rel(p)
        text = p.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            for ch in EMOJI.findall(line):
                per_file[r] += 1
                if len(samples[r]) < 4:
                    samples[r].append(f"{i}: {line.strip()[:70]}")
    return {
        "total": sum(per_file.values()),
        "files": per_file.most_common(),
        "samples": {k: v for k, v in list(samples.items())[:20]},
    }


def audit_type_scale() -> dict[str, object]:
    sizes: Counter[str] = Counter()
    for name in ("globals.css", "experience.css"):
        p = WEB / "app" / name
        if not p.exists():
            continue
        for m in FONT_SIZE.finditer(p.read_text(encoding="utf-8")):
            sizes[m.group(1)] += 1
    return {"distinct": len(sizes), "values": sizes.most_common()}


def audit_spacing() -> dict[str, object]:
    vals: Counter[str] = Counter()
    p = WEB / "app" / "globals.css"
    for m in SPACING.finditer(p.read_text(encoding="utf-8")):
        vals[m.group(1)] += 1
    return {"distinct": len(vals), "values": vals.most_common(40)}


def audit_tokens() -> dict[str, object]:
    """Liệt kê token đã khai báo trong :root."""
    p = WEB / "app" / "globals.css"
    text = p.read_text(encoding="utf-8")
    names = sorted(set(re.findall(r"(--nq-[a-z0-9-]+):", text)))
    return {"count": len(names), "names": names}


def main() -> int:
    report = {
        "tailwind_off_token": audit_tailwind(),
        "raw_hex": audit_hex(),
        "emoji_as_icon": audit_emoji(),
        "css_type_scale": audit_type_scale(),
        "css_spacing_values": audit_spacing(),
        "declared_tokens": audit_tokens(),
    }
    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    tw = report["tailwind_off_token"]
    print(f"== Màu Tailwind ngoài token: {tw['total']} ==")
    for f, n in tw["files"][:20]:
        print(f"  {n:4}  {f}")

    hx = report["raw_hex"]
    print(f"\n== Hex trần trong TS/TSX: {hx['total']} ==")
    for f, n in hx["files"][:20]:
        print(f"  {n:4}  {f}")

    em = report["emoji_as_icon"]
    print(f"\n== Emoji dùng làm icon: {em['total']} trong {len(em['files'])} file ==")
    for f, n in em["files"][:20]:
        print(f"  {n:4}  {f}")

    ts = report["css_type_scale"]
    print(f"\n== font-size rời rạc trong CSS: {ts['distinct']} giá trị khác nhau ==")
    print("   " + ", ".join(f"{v}({c})" for v, c in ts["values"]))

    sp = report["css_spacing_values"]
    print(f"\n== Giá trị spacing trong globals.css: {sp['distinct']} giá trị khác nhau ==")
    print("   " + ", ".join(f"{v}({c})" for v, c in sp["values"][:24]))

    tk = report["declared_tokens"]
    print(f"\n== Token --nq-* đã khai báo: {tk['count']} ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
