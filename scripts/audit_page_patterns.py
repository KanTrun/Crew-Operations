"""Chấm điểm từng trang theo 16 lỗi kiểu "AI-made" — NHỊP QUÁN.

Sinh bảng audit: mỗi trang/khu vực mắc lỗi nào trong 2 nhóm:
  NHÓM A — "2D dashboard AI-made"  (A1..A8)
  NHÓM B — "3D/hiệu ứng AI-made"   (B1..B6)

Chạy:  python scripts/audit_page_patterns.py [--json] [--only <substr>]
Đây là công cụ ĐO, không sửa gì. Dùng lại sau khi sửa để so before/after.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"
SRC = WEB / "src"

TAILWIND_COLOR = re.compile(
    r"\b(?:bg|text|border|ring|from|to|via|fill|stroke|divide)"
    r"-(?:amber|blue|green|red|slate|zinc|gray|emerald|violet|indigo|purple|sky|teal|cyan|orange|rose|yellow|lime|pink|fuchsia|stone|neutral)-\d{2,3}\b"
)
EMOJI = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U00002b00-\U00002bff\U0000fe0f]"
)
RAW_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
CLAMP = re.compile(r"line-clamp|text-overflow:\s*ellipsis|nq-clamp-\d")
BORDER_RADIUS_TW = re.compile(r"\brounded(?:-[a-z0-9]+)?\b")
SHADOW_TW = re.compile(r"\bshadow-(?:sm|md|lg|xl|2xl|inner)\b")
BLUR_TW = re.compile(r"\bbackdrop-blur(?:-[a-z0-9]+)?\b")
GRADIENT_TW = re.compile(r"\bbg-gradient-to-[a-z]+\b")
TILT = re.compile(r"rotateX|rotateY|useTilt|transformPerspective")
SPRING_DEFAULT = re.compile(r"type:\s*[\"']spring[\"']|stiffness:|useSpring\(")
FRAMER = re.compile(r"framer-motion")
THREE = re.compile(r"@react-three|useFrame|<Canvas")
PARTICLE = re.compile(r"Particle|particle")
GLOW = re.compile(r"glow|blur\(|drop-shadow")
AUTOROTATE = re.compile(r"rotation\.[xy] \+=|autoRotate")
GRAIN = re.compile(r"nq-grain|grain")

# Token màu trạng thái dùng đúng hệ.
STATUS_TOKEN = re.compile(r"--nq-(warn|ok|danger|red|green)\b")


def score(text: str) -> dict[str, int]:
    """Đếm số lần xuất hiện của mỗi dấu hiệu lỗi."""
    return {
        "A1_status_color": 0,  # ĐO RIÊNG: không suy từ regex (xem has_status_system)
        "A2_truncate": len(CLAMP.findall(text)),
        "A3_flat_surface": len(BORDER_RADIUS_TW.findall(text)),
        "A4_type_scale": len(re.findall(r"text-(?:\[[^\]]+\]|xs|sm|base|lg|xl|\dxl)", text)),
        "A5_emoji_icon": len(EMOJI.findall(text)),
        "A6_offtoken_color": len(TAILWIND_COLOR.findall(text)),
        "A7_raw_hex": len(RAW_HEX.findall(text)),
        "A8_gradient": len(GRADIENT_TW.findall(text)),
        "B1_particle": len(PARTICLE.findall(text)),
        "B2_blur": len(BLUR_TW.findall(text)),
        "B3_3d_object": len(THREE.findall(text)),
        "B4_spring_default": len(SPRING_DEFAULT.findall(text)),
        "B5_tilt": len(TILT.findall(text)),
        "B6_glow": len(GLOW.findall(text)),
        "_framer": len(FRAMER.findall(text)),
        "_autorotate": len(AUTOROTATE.findall(text)),
        "_shadow_tw": len(SHADOW_TW.findall(text)),
        "_status_token": len(STATUS_TOKEN.findall(text)),
    }


def main() -> int:
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]

    rows = []
    pages = sorted((SRC / "app").rglob("page.tsx"))
    pages.append(SRC / "app" / "hom-nay" / "page.tsx")
    pages = sorted(set(pages))

    # CSS dùng chung — đếm lỗi ở tầng style để biết lỗi nằm ở token hay ở trang.
    css = (SRC / "app" / "globals.css").read_text(encoding="utf-8")
    css_exp = (SRC / "app" / "experience.css").read_text(encoding="utf-8")

    for p in pages:
        if not p.is_file():
            continue
        route = "/" + p.parent.relative_to(SRC / "app").as_posix()
        route = route.replace("/.", "") if route == "/." else route
        if route == "/.":
            route = "/"
        if only and only not in route:
            continue
        text = p.read_text(encoding="utf-8")
        s = score(text)
        # Component con cùng thư mục (page.tsx thường mỏng)
        for extra in p.parent.glob("*.tsx"):
            if extra == p:
                continue
            t2 = extra.read_text(encoding="utf-8")
            s2 = score(t2)
            for k in s2:
                s[k] += s2[k]
        s["_loc"] = len(text.splitlines())
        s["_route"] = route
        rows.append(s)

    rows.sort(key=lambda r: -(r["A6_offtoken_color"] + r["A5_emoji_icon"] + r["A2_truncate"] * 2))

    if "--json" in sys.argv:
        print(json.dumps({"pages": rows, "css_globals": score(css), "css_experience": score(css_exp)},
                         ensure_ascii=False, indent=2))
        return 0

    hdr = f"{'route':<34}{'LOC':>5}{'A2clmp':>7}{'A5emoji':>8}{'A6color':>8}{'A7hex':>6}{'A8grad':>7}{'B2blur':>7}{'B4spr':>6}{'B5tilt':>7}{'B6glow':>7}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        if r["A6_offtoken_color"] + r["A5_emoji_icon"] + r["A2_truncate"] == 0 and r["_loc"] < 40:
            continue
        print(
            f"{r['_route'][:33]:<34}{r['_loc']:>5}{r['A2_truncate']:>7}{r['A5_emoji_icon']:>8}"
            f"{r['A6_offtoken_color']:>8}{r['A7_raw_hex']:>6}{r['A8_gradient']:>7}"
            f"{r['B2_blur']:>7}{r['B4_spring_default']:>6}{r['B5_tilt']:>7}{r['B6_glow']:>7}"
        )

    print("\n== CSS dùng chung ==")
    for name, s in (("globals.css", score(css)), ("experience.css", score(css_exp))):
        print(
            f"  {name:<18} emoji={s['A5_emoji_icon']:>3} offtoken={s['A6_offtoken_color']:>3} "
            f"hex={s['A7_raw_hex']:>3} grad={s['A8_gradient']:>3} clamp={s['A2_truncate']:>3} "
            f"blur={s['B2_blur']:>3} glow={s['B6_glow']:>3}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
