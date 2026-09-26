"""Ánh xạ lớp màu Tailwind ngoài token → token NHỊP QUÁN.

Sinh bảng ánh xạ có kiểm chứng để đổi hàng loạt lớp ngoài hệ sang token, thay
vì sửa tay từng file (240+ chỗ). Chỉ những lớp có ánh xạ RÕ NGHĨA mới được đưa
vào bảng; lớp không rõ nghĩa bị báo lại để quyết định riêng.

Quy tắc ánh xạ (tất cả đều dựa trên bảng màu đã đo ở scripts/check_contrast.py):

  amber-*   → --nq-st-warn    (cảnh báo: thiếu người, sắp hạn, chờ xử lý)
  emerald-* → --nq-st-ok      (tốt: đủ người, đúng hạn, đã xong)
  rose-*/red-* → --nq-st-danger (lỗi: quá hạn, trống ca, từ chối)
  sky-*/blue-*/indigo-*/purple-* → --nq-st-info (đang xử lý, chờ xác nhận)
  zinc-*/neutral-*/slate-*/gray-* → bề mặt và chữ của hệ (không phải trạng thái)

Chạy:  python scripts/map_offtoken_colors.py [--json] [--apply-report]
Không sửa file — chỉ báo cáo.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web" / "src"

CLASS_RE = re.compile(
    r"\b(?P<util>bg|text|border|ring|from|to|via|fill|stroke|divide|decoration|shadow|outline)"
    r"-(?P<stem>(?P<family>amber|blue|green|red|slate|zinc|gray|grey|emerald|violet|indigo|purple|sky|teal|cyan|orange|rose|yellow|lime|pink|fuchsia|stone|neutral)"
    r"-(?P<step>\d{2,3}))\b"
)

# Nhóm ngữ nghĩa: family → token trạng thái.
SEMANTIC = {
    "amber": "--nq-st-warn",
    "yellow": "--nq-st-warn",
    "orange": "--nq-st-warn",
    "emerald": "--nq-st-ok",
    "green": "--nq-st-ok",
    "lime": "--nq-st-ok",
    "rose": "--nq-st-danger",
    "red": "--nq-st-danger",
    "sky": "--nq-st-info",
    "blue": "--nq-st-info",
    "indigo": "--nq-st-info",
    "purple": "--nq-st-info",
    "violet": "--nq-st-info",
    "cyan": "--nq-st-info",
    "teal": "--nq-st-info",
    "fuchsia": "--nq-st-info",
    "pink": "--nq-st-info",
}

# Nhóm trung tính: family → token bề mặt/chữ của hệ.
NEUTRAL = {
    "zinc": None,
    "neutral": None,
    "slate": None,
    "gray": None,
    "grey": None,
    "stone": None,
}

# Bậc nào là "nền tối" (dùng cho bg-*) và bậc nào là "chữ sáng" (dùng cho text-*).
DARK_STEPS = {"950", "900", "800", "700", "600"}
LIGHT_STEPS = {"50", "100", "200", "300", "400", "500"}


def classify(util: str, family: str, step: str) -> str:
    """Trả về token đích, hoặc mã lý do không ánh xạ được."""
    if family in NEUTRAL:
        if util in ("bg", "from", "to", "via"):
            return "--nq-bg-elevated" if step in DARK_STEPS else "--nq-surface"
        if util in ("text", "fill", "stroke"):
            return "--nq-ink-muted" if step in DARK_STEPS else "--nq-ink"
        if util in ("border", "divide", "ring"):
            return "--nq-line"
    token = SEMANTIC.get(family)
    if token:
        if util in ("bg", "from", "to", "via"):
            if step in DARK_STEPS:
                return f"color-mix(in srgb, var({token}) 18%, transparent)"
            return token
        if util in ("text", "fill", "stroke"):
            return token
        if util in ("border", "divide", "ring"):
            return f"color-mix(in srgb, var({token}) 46%, var(--nq-line))"
    return "?"


def main() -> int:
    per_class: Counter[str] = Counter()
    per_file: dict[str, Counter[str]] = defaultdict(Counter)
    unmapped: Counter[str] = Counter()
    mapping: dict[str, str] = {}

    for p in sorted(WEB.rglob("*.tsx")):
        text = p.read_text(encoding="utf-8")
        rel = p.relative_to(WEB).as_posix()
        for m in CLASS_RE.finditer(text):
            cls = m.group(0)
            per_class[cls] += 1
            per_file[rel][cls] += 1
            target = classify(m.group("util"), m.group("family"), m.group("step"))
            if target == "?":
                unmapped[cls] += 1
            else:
                mapping[cls] = target

    total = sum(per_class.values())
    print(f"== Lớp màu ngoài token: {total} lần dùng, {len(per_class)} lớp khác nhau ==")
    print(f"   Ánh xạ được sang token: {total - sum(unmapped.values())} lần "
          f"({len(mapping)} lớp)")
    print(f"   Chưa ánh xạ được: {sum(unmapped.values())} lần ({len(unmapped)} lớp)")

    print("\n== Bảng ánh xạ theo nhóm ngữ nghĩa ==")
    groups: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
    for cls, n in per_class.most_common():
        m = CLASS_RE.match(cls)
        if not m:
            continue
        tgt = classify(m.group("util"), m.group("family"), m.group("step"))
        key = m.group("family")
        groups[key].append((cls, n, tgt))
    for fam in sorted(groups, key=lambda f: -sum(n for _, n, _ in groups[f])):
        items = groups[fam]
        tot = sum(n for _, n, _ in items)
        print(f"\n  {fam} ({tot} lần):")
        for cls, n, tgt in sorted(items, key=lambda x: -x[1])[:8]:
            print(f"    {cls:<26} ×{n:<4} → {tgt}")

    if unmapped:
        print("\n== Lớp chưa ánh xạ ==")
        for cls, n in unmapped.most_common():
            print(f"    {cls:<26} ×{n}")

    print("\n== File nhiều lớp ngoài token nhất ==")
    for rel, counter in sorted(per_file.items(), key=lambda kv: -sum(kv[1].values()))[:16]:
        print(f"  {sum(counter.values()):>4}  {rel}")

    if "--json" in sys.argv:
        out = {
            "total": total,
            "mapping": mapping,
            "unmapped": dict(unmapped),
            "per_file": {k: sum(v.values()) for k, v in per_file.items()},
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
