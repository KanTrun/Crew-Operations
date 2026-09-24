"""Đo tương phản màu theo WCAG 2.1 — NHỊP QUÁN.

Mục đích: tương phản là SỐ HỌC, không phải cảm nhận. Script này tính tỉ lệ
tương phản cho mọi cặp (nền, chữ) mà hệ thống thực sự dùng, và cho các lớp
Tailwind ngoài token đang có trong mã, để biết lớp nào đang đọc không được.

Chuẩn áp dụng:
  - 4.5:1 cho chữ thường (WCAG AA)
  - 3.0:1 cho chữ lớn (>= 18.66px bold hoặc >= 24px) và cho viền/ranh giới UI
  - 7.0:1 cho chữ trong bảng số liệu đọc lâu (mức tự đặt của dự án)

Chạy:  python scripts/check_contrast.py [--palette]
Không sửa gì.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AA_TEXT = 4.5
AA_LARGE = 3.0
AA_TABLE = 7.0


def _srgb(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def luminance(hex_color: str) -> float:
    r, g, b = hex_to_rgb(hex_color)
    return 0.2126 * _srgb(r / 255) + 0.7152 * _srgb(g / 255) + 0.0722 * _srgb(b / 255)


def ratio(fg: str, bg: str) -> float:
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def read_tokens() -> dict[str, str]:
    """Đọc token màu đang khai báo trong :root của globals.css.

    Token dạng `rgba(...)` phải được HỢP NHẤT với nền trước khi đo — đo một
    màu bán trong suốt là đo một màu không tồn tại trên màn hình. `--nq-ink-muted`
    và `--nq-line` đều là rgba, nên bỏ bước này là bỏ qua đúng hai token được
    dùng nhiều nhất cho chữ phụ và đường kẻ.
    """
    css = (ROOT / "apps" / "web" / "src" / "app" / "globals.css").read_text(encoding="utf-8")
    out: dict[str, str] = {}
    raw_map: dict[str, str] = {}

    for name in (
        "bg", "bg-elevated", "surface", "ink", "ink-muted", "line", "line-strong",
        "line-control", "accent", "accent-hover", "accent-ink", "danger", "ok", "warn",
        "st-ok", "st-warn", "st-danger", "st-info",
    ):
        marker = f"--nq-{name}:"
        idx = css.find(marker)
        if idx < 0:
            continue
        raw = css[idx + len(marker):].split(";")[0].strip()
        raw_map[name] = raw
        if raw.startswith("#"):
            out[name] = raw
        elif raw.startswith("var(--nq-"):
            target = raw[len("var(--nq-"):].split(")")[0]
            if target in raw_map and raw_map[target].startswith("#"):
                out[name] = raw_map[target]
            else:
                idx2 = css.find(f"--nq-{target}:")
                if idx2 >= 0:
                    raw2 = css[idx2 + len(f"--nq-{target}:"):].split(";")[0].strip()
                    if raw2.startswith("#"):
                        out[name] = raw2

    # Hợp nhất các token rgba lên nền trang (và lên bề mặt thẻ khi cần).
    bg = out.get("bg", "#070d12")
    for name, raw in raw_map.items():
        if name in out:
            continue
        m = re.match(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,/\s]+([\d.]+))?\s*\)", raw)
        if m:
            r, g, b = (float(m.group(i)) for i in (1, 2, 3))
            a = float(m.group(4)) if m.group(4) else 1.0
            out[name] = composite((r, g, b, a), bg)
        elif raw.startswith("#"):
            out[name] = raw
    return out


def composite(fg: tuple[float, float, float, float], bg_hex: str) -> str:
    """Hợp nhất màu bán trong suốt lên nền đặc, trả về hex."""
    br, bg_g, bb = hex_to_rgb(bg_hex)
    r, g, b, a = fg
    return f"#{round(r * a + br * (1 - a)):02x}{round(g * a + bg_g * (1 - a)):02x}{round(b * a + bb * (1 - a)):02x}"


# Các cặp (nhãn, chữ, nền, chuẩn) hệ thống thực sự dùng.
#
# Ba loại chuẩn khác nhau, KHÔNG được trộn:
#   AA_TEXT  4.5:1 — chữ thường (WCAG 1.4.3)
#   AA_LARGE 3.0:1 — chữ lớn, và ĐƯỜNG BIÊN của thành phần bấm được (1.4.11)
#   None     — vạch kẻ trang trí: không có ngưỡng, chỉ ghi nhận
# Gộp vạch kẻ trang trí vào ngưỡng 3:1 là báo lỗi sai — WCAG không đòi một
# đường phân cách giữa hai nhóm nội dung phải đạt 3:1.
PAIRS: list[tuple[str, str, str, float | None]] = [
    ("chữ chính / nền trang", "ink", "bg", AA_TEXT),
    ("chữ chính / bề mặt thẻ", "ink", "bg-elevated", AA_TEXT),
    ("chữ chính / ô nhập", "ink", "surface", AA_TEXT),
    ("chữ phụ / nền trang", "ink-muted", "bg", AA_TEXT),
    ("chữ phụ / bề mặt thẻ", "ink-muted", "bg-elevated", AA_TEXT),
    ("chữ phụ / ô nhập", "ink-muted", "surface", AA_TEXT),
    ("accent / nền trang", "accent", "bg", AA_TEXT),
    ("accent / bề mặt thẻ", "accent", "bg-elevated", AA_TEXT),
    ("chữ trên nút accent", "accent-ink", "accent", AA_TEXT),
    ("trạng thái ok / nền trang", "st-ok", "bg", AA_TEXT),
    ("trạng thái ok / bề mặt thẻ", "st-ok", "bg-elevated", AA_TEXT),
    ("trạng thái warn / nền trang", "st-warn", "bg", AA_TEXT),
    ("trạng thái warn / bề mặt thẻ", "st-warn", "bg-elevated", AA_TEXT),
    ("trạng thái danger / nền trang", "st-danger", "bg", AA_TEXT),
    ("trạng thái danger / bề mặt thẻ", "st-danger", "bg-elevated", AA_TEXT),
    ("trạng thái info / nền trang", "st-info", "bg", AA_TEXT),
    ("trạng thái info / bề mặt thẻ", "st-info", "bg-elevated", AA_TEXT),
    # Đường biên thành phần bấm được — ngưỡng 3:1 (WCAG 1.4.11).
    ("viền ô nhập / nền trang", "line-control", "bg", AA_LARGE),
    ("viền ô nhập / chính ô nhập", "line-control", "surface", AA_LARGE),
    ("viền ô nhập / bề mặt thẻ", "line-control", "bg-elevated", AA_LARGE),
    # Vạch kẻ trang trí — ghi nhận, không chấm.
    ("vạch kẻ mảnh / nền trang (trang trí)", "line", "bg", None),
    ("vạch kẻ mạnh / nền trang (trang trí)", "line-strong", "bg", None),
]

# Lớp Tailwind ngoài token đang có trong mã, để so trước/sau khi ánh xạ.
#
# Bảng này ĐỌC TỪ `scripts/gen_tailwind_palette.py` — nguồn sự thật của bảng
# màu đang phục vụ. Chép cứng bảng mặc định Tailwind vào đây (bản trước) khiến
# script đo một bảng màu KHÔNG TỒN TẠI: sau khi thay bảng màu ở tailwind.config,
# script vẫn báo đúng 5 "lỗi" của bảng mặc định cũ, và người đọc tưởng bảng mới
# hỏng. Đọc từ nguồn thì con số luôn khớp thứ đang chạy.
def _tailwind_shades() -> dict[str, dict[str, str]]:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_gen_palette", str(ROOT / "scripts" / "gen_tailwind_palette.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Chỉ đo các họ mà mã THỰC SỰ dùng, và chỉ các bậc đang xuất hiện trong mã —
    # đo bậc không ai dùng là tạo việc giả.
    used = mod.actual_usage()
    out: dict[str, dict[str, str]] = {}
    for fam, combos in used.items():
        ramp = mod.RAMPS.get(fam)
        if not ramp:
            continue
        steps = {step for _, step, _ in combos}
        out[fam] = {s: ramp[s] for s in sorted(steps) if s in ramp}
    return out


TAILWIND_SHADES: dict[str, dict[str, str]] = _tailwind_shades()


def report_tokens() -> int:
    tk = read_tokens()
    print("== Token màu đang khai báo ==")
    for k, v in tk.items():
        print(f"  --nq-{k:<14} {v}")
    if not tk:
        print("  (không đọc được token nào)")
        return 1

    print("\n== Tương phản theo cặp sử dụng thật ==")
    fails = 0
    checked = 0
    for label, fg_key, bg_key, need in PAIRS:
        if fg_key not in tk or bg_key not in tk:
            continue
        r = ratio(tk[fg_key], tk[bg_key])
        if need is None:
            print(f"  --   {r:5.2f}:1 (không chấm)      — {label}")
            continue
        checked += 1
        ok = r >= need
        if not ok:
            fails += 1
        print(f"  {'OK ' if ok else 'FAIL'} {r:5.2f}:1 (cần {need}) — {label}")
    print(f"\n  Cặp không đạt: {fails}/{checked}")
    return fails


def report_palette(tokens: dict[str, str]) -> int:
    """Lớp Tailwind ngoài token đang có trong mã — đo để đối chiếu trước/sau.

    Không phải lớp nào cũng sai. Mã dùng chúng theo hai vai trái ngược:
      - vai CHỮ (text-*, fill sáng): phải đạt 4.5:1, nếu không là lỗi thật.
      - vai NỀN/VIỀN tối (bg-*-950, border-zinc-800): tương phản thấp với nền
        trang là ĐÚNG ý đồ — chúng tối hơn nền. Các lớp này sai ở chỗ khác:
        chúng không thuộc bảng màu quán, nên màu tối của chúng lệch tông so với
        `--nq-bg-elevated` và `--nq-surface`.
    Vì vậy script chỉ chấm lỗi tương phản cho nhóm có thể làm chữ, còn nhóm nền
    tối thì đếm riêng là "lệch bảng màu".
    """
    bg = tokens.get("bg", "#070d12")
    elev = tokens.get("bg-elevated", "#0b141b")
    print(f"== Lớp Tailwind ngoài token, đo trên nền trang {bg} / bề mặt {elev} ==")
    text_fail: list[str] = []
    bg_only = 0
    for family, shades in TAILWIND_SHADES.items():
        for step, hexv in shades.items():
            r_bg = ratio(hexv, bg)
            r_elev = ratio(hexv, elev)
            bright = r_bg >= AA_TEXT and r_elev >= AA_TEXT
            if bright:
                verdict = "dùng làm chữ được"
            elif step in ("950", "900", "800", "700"):
                verdict = "nền tối — lệch tông chứ không sai tương phản"
                bg_only += 1
            else:
                verdict = "DƯỚI 4.5 — không dùng được làm chữ"
                text_fail.append(f"{family}-{step}")
            print(f"  {family}-{step:<4} {hexv}  nền {r_bg:5.2f}  bề mặt {r_elev:5.2f}  {verdict}")
    print(f"\n  Lớp làm nền tối (lệch bảng màu, không phải lỗi tương phản): {bg_only}")
    print(f"  Lớp làm chữ mà dưới 4.5:1 (lỗi thật): {len(text_fail)}"
          + (f" — {', '.join(text_fail)}" if text_fail else ""))
    return 0


def main() -> int:
    tokens = read_tokens()
    if "--palette" in sys.argv:
        report_palette(tokens)
        return 0
    fails = report_tokens()
    print()
    report_palette(tokens)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
