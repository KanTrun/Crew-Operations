"""Sinh và kiểm chứng bảng màu Tailwind gốc NHỊP QUÁN.

Vấn đề: mã dùng 13 họ màu Tailwind mặc định (amber, emerald, rose, zinc,
purple, indigo...) với đủ 11 bậc (50→950) — mỗi file tự chọn bậc khác nhau cho
cùng một ý nghĩa. Đó là bảng màu mặc định của mọi dashboard do AI dựng, không
phải bảng màu quán.

Cách sửa: KHÔNG viết lại 1000 chỗ trong markup. Thay bảng màu ngay ở tailwind
config — mọi lớp `bg-amber-950/30` hay `text-emerald-400` sẵn có tự trỏ về màu
của quán, giữ nguyên hình dạng bậc thang mà mã đang dựa vào (bậc tối làm nền,
bậc sáng làm chữ).

Script này sinh bảng màu đó và KIỂM CHỨNG bằng số:
  - mỗi bậc phải giữ đúng vai trò cũ (bậc sáng đọc được, bậc tối làm nền được)
  - không bậc nào được tệ hơn bậc tương ứng của bảng mặc định về tương phản
    ở đúng vai trò nó đang được dùng

Chạy:  python scripts/gen_tailwind_palette.py [--check] [--emit-js]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"

BG = "#0e0c0a"        # --nq-bg
ELEV = "#1a1612"      # --nq-bg-elevated


def _srgb(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_rgb(v: str) -> tuple[int, int, int]:
    v = v.lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def lum(h: str) -> float:
    r, g, b = hex_to_rgb(h)
    return 0.2126 * _srgb(r / 255) + 0.7152 * _srgb(g / 255) + 0.0722 * _srgb(b / 255)


def ratio(a: str, b: str) -> float:
    l1, l2 = lum(a), lum(b)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def hex_rgb(r: float, g: float, b: float) -> str:
    """Kẹp về 0..255 trước khi in.

    Không kẹp thì nội suy có thể ra giá trị âm và sinh ra chuỗi kiểu `#-2-2-3`,
    làm cả bảng màu vỡ ở chỗ khó thấy. Đây là lỗi đã xảy ra thật ở bậc neutral-950.
    """
    return f"#{min(255, max(0, round(r))):02x}{min(255, max(0, round(g))):02x}{min(255, max(0, round(b))):02x}"


def ramp(base: str, light: str, dark: str) -> dict[str, str]:
    """Dựng thang 11 bậc: 50..400 chạy từ `light` về `base`, 400..950 từ `base` về `dark`.

    `base` neo ở bậc 400 — đó là màu thương hiệu thật, và cũng là bậc mà mã đang
    dùng nhiều nhất cho cả chữ lẫn nền đặc.

    Đoạn 400→950 dùng lũy thừa 1.8 chứ không tuyến tính. Lý do: mã dùng `-500`
    và `-600` làm NỀN ĐẶC có chữ tối đè lên, còn `-900`/`-950` mới là nền tối.
    Nội suy tuyến tính làm bậc 500 tối đi ngay và tụt dưới 4.5:1 khi dùng làm
    chữ (đo được: emerald-500 chỉ còn 4.15:1, default Tailwind là 7.09:1). Lũy
    thừa giữ 500–600 gần màu gốc và dốc nhanh từ 700 trở đi.
    """
    steps = ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"]
    lt, mid, dk = hex_to_rgb(light), hex_to_rgb(base), hex_to_rgb(dark)
    out: dict[str, str] = {}
    for i, s in enumerate(steps):
        if i <= 4:                      # 50..400: light → base
            t = i / 4
            out[s] = hex_rgb(*(lt[j] + (mid[j] - lt[j]) * t for j in range(3)))
        else:                           # 500..950: base → dark, dốc dần
            t = ((i - 4) / 6) ** 1.8
            out[s] = hex_rgb(*(mid[j] + (dk[j] - mid[j]) * t for j in range(3)))
    return out


def ramp_anchored(anchors: dict[str, str]) -> dict[str, str]:
    """Thang 11 bậc nội suy qua các MỐC CHỐT do người thiết kế chọn.

    Vì sao không nội suy một đường từ sáng xuống tối: các bậc không chia đều
    nhiệm vụ. Bậc 300–400 phải đủ SÁNG để làm chữ trên nền tối (>= 4.5:1), bậc
    600–800 phải đủ TỐI để làm nền cho chữ sáng, còn bậc 500 là nền nút — mà
    nền nút thì tuỳ họ: họ vàng đặt chữ tối lên (phải sáng), họ xanh/đỏ đặt chữ
    sáng lên (phải tối). Một hàm nội suy dùng chung không thoả được cả ba, nên
    mốc được chốt riêng cho từng họ rồi nội suy giữa các mốc liền kề.
    """
    order = ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"]
    keys = sorted(anchors, key=lambda s: order.index(s))
    out: dict[str, str] = {}
    for _i, s in enumerate(keys):
        out[s] = anchors[s]
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        ia, ib = order.index(a), order.index(b)
        ca, cb = hex_to_rgb(anchors[a]), hex_to_rgb(anchors[b])
        span = ib - ia
        for k in range(1, span):
            t = k / span
            out[order[ia + k]] = hex_rgb(*(ca[j] + (cb[j] - ca[j]) * t for j in range(3)))
    return {s: out[s] for s in order}


# ── Bảng màu gốc, dẫn xuất từ token thương hiệu ──
# Vai của từng họ lấy từ cách mã dùng thật (xem scripts/map_offtoken_colors.py):
#   vàng  → cảnh báo, nút nền sáng + chữ tối (mã viết `bg-amber-600 text-neutral-950`)
#   xanh  → tốt,      nút nền sáng + chữ tối (mã viết `bg-emerald-600 text-neutral-950`)
#   đỏ    → lỗi,      nút nền sáng + chữ tối (mã viết `bg-red-500 text-white` → sửa lại)
#   xanh khói → đang xử lý
#   trung tính → chữ phụ và nền tối
#
# Mốc 500 được chốt SÁNG cho mọi họ vì hai lý do có thật trong mã: (1) nó làm
# nền nút nên phải đủ sáng cho chữ tối, và (2) mã dùng rất nhiều lớp dạng
# `bg-<họ>-500/10` làm nền nhạt — một màu tối ở 10% trên nền trang sẽ thành
# vô hình. Chữ trắng đặt trên các nút này là chỗ SAI trong mã gốc và được sửa
# riêng, không phải chỗ để nắn bảng màu.
# Mốc 950 cố ý KHÔNG kéo xuống gần đen. Mã dùng rất nhiều lớp dạng
# `bg-<họ>-950/30` làm nền nhạt; nếu mốc 950 gần đen thì pha loãng 30% xong
# không còn chút sắc nào của họ màu, và mọi khối đó đọc ra như nhau. Mốc 950
# giữ đúng độ sáng mà bảng mặc định Tailwind đang cho (đo được), đủ tối để làm
# nền cho chữ sáng mà vẫn giữ được sắc khi pha loãng.
AMBER = ramp_anchored({
    "50": "#fbeecb", "300": "#deb444", "500": "#cd9b16",
    "700": "#6d520d", "950": "#38220a",
})
EMERALD = ramp_anchored({
    "50": "#dcebe1", "300": "#8aaf94", "500": "#639170",
    "700": "#3d5c47", "950": "#0e2b1d",
})
ROSE = ramp_anchored({
    "50": "#f7dcd7", "300": "#dd7d6d", "500": "#cf6150",
    "700": "#8a3f34", "950": "#3a1013",
})
INFO = ramp_anchored({
    "50": "#dbe8f2", "300": "#88a5bf", "500": "#6b8aa8",
    "700": "#40566a", "950": "#16283a",
})
# Neutral: 300–400 giữ đúng độ sáng của `--nq-ink-muted` để mọi chỗ đang dùng
# `text-zinc-400` cho chữ phụ không mất khả năng đọc; 700–950 dốc xuống nhanh vì
# mã dùng chúng làm NỀN tối cho chữ sáng (bản đầu để quá sáng nên
# `bg-neutral-800` + `text-neutral-300` chỉ còn 2.17:1).
NEUTRAL = ramp_anchored({
    "50": "#f5ead8", "300": "#beb5a6", "400": "#aba396", "500": "#6f675e",
    "700": "#38332e", "950": "#131110",
})

# Bảng mặc định Tailwind — mốc so sánh "không được kém hơn". Cố ý phủ rộng:
# mọi bậc mà mã đang dùng, cho mọi họ, để phép so wash có baseline thật thay vì
# rơi vào nhánh mặc định dễ dãi.
DEFAULT: dict[str, dict[str, str]] = {
    "amber": {"50": "#fffbeb", "100": "#fef3c7", "200": "#fde68a", "300": "#fcd34d",
              "400": "#fbbf24", "500": "#f59e0b", "600": "#d97706", "700": "#b45309",
              "800": "#92400e", "900": "#78350f", "950": "#451a03"},
    "emerald": {"50": "#ecfdf5", "100": "#d1fae5", "200": "#a7f3d0", "300": "#6ee7b7",
                "400": "#34d399", "500": "#10b981", "600": "#059669", "700": "#047857",
                "800": "#065f46", "900": "#064e3b", "950": "#022c22"},
    "rose": {"50": "#fff1f2", "100": "#ffe4e6", "200": "#fecdd3", "300": "#fda4af",
             "400": "#fb7185", "500": "#f43f5e", "600": "#e11d48", "700": "#be123c",
             "800": "#9f1239", "900": "#881337", "950": "#4c0519"},
    "red": {"50": "#fef2f2", "100": "#fee2e2", "200": "#fecaca", "300": "#fca5a5",
            "400": "#f87171", "500": "#ef4444", "600": "#dc2626", "700": "#b91c1c",
            "800": "#991b1b", "900": "#7f1d1d", "950": "#450a0a"},
    "orange": {"400": "#fb923c", "500": "#f97316", "600": "#ea580c", "950": "#431407"},
    "yellow": {"400": "#facc15", "500": "#eab308", "600": "#ca8a04", "950": "#422006"},
    "lime": {"400": "#a3e635", "500": "#84cc16", "600": "#65a30d", "950": "#1a2e05"},
    "green": {"300": "#86efac", "400": "#4ade80", "500": "#22c55e", "600": "#16a34a",
              "700": "#15803d", "950": "#052e16"},
    "slate": {"300": "#cbd5e1", "400": "#94a3b8", "500": "#64748b", "700": "#334155",
              "800": "#1e293b", "900": "#0f172a", "950": "#020617"},
    "zinc": {"300": "#d4d4d8", "400": "#a1a1aa", "500": "#71717a", "600": "#52525b",
             "700": "#3f3f46", "800": "#27272a", "900": "#18181b", "950": "#09090b"},
    "neutral": {"300": "#d4d4d4", "400": "#a3a3a3", "500": "#737373", "600": "#525252",
                "700": "#404040", "800": "#262626", "900": "#171717", "950": "#0a0a0a"},
    "stone": {"300": "#d6d3d1", "400": "#a8a29e", "500": "#78716c", "600": "#57534e",
              "700": "#44403c", "800": "#292524", "900": "#1c1917", "950": "#0c0a09"},
    "gray": {"300": "#d1d5db", "400": "#9ca3af", "500": "#6b7280", "600": "#4b5563",
             "700": "#374151", "800": "#1f2937", "900": "#111827", "950": "#030712"},
    "purple": {"300": "#d8b4fe", "400": "#c084fc", "500": "#a855f7", "600": "#9333ea",
               "700": "#7e22ce", "800": "#6b21a8", "900": "#581c87", "950": "#3b0764"},
    "violet": {"300": "#c4b5fd", "400": "#a78bfa", "500": "#8b5cf6", "600": "#7c3aed",
               "950": "#2e1065"},
    "indigo": {"300": "#a5b4fc", "400": "#818cf8", "500": "#6366f1", "600": "#4f46e5",
               "700": "#4338ca", "800": "#3730a3", "900": "#312e81", "950": "#1e1b4b"},
    "blue": {"300": "#93c5fd", "400": "#60a5fa", "500": "#3b82f6", "600": "#2563eb",
             "700": "#1d4ed8", "900": "#1e3a8a", "950": "#172554"},
    "sky": {"300": "#7dd3fc", "400": "#38bdf8", "500": "#0ea5e9", "600": "#0284c7",
            "950": "#082f49"},
    "cyan": {"300": "#67e8f9", "400": "#22d3ee", "500": "#06b6d4", "600": "#0891b2",
             "900": "#164e63", "950": "#083344"},
    "teal": {"300": "#5eead4", "400": "#2dd4bf", "500": "#14b8a6", "950": "#042f2e"},
    "fuchsia": {"300": "#f0abfc", "400": "#e879f9", "500": "#d946ef", "950": "#4a044e"},
    "pink": {"300": "#f9a8d4", "400": "#f472b6", "500": "#ec4899", "950": "#500724"},
    "grey": {},
}

RAMPS = {
    "amber": AMBER, "yellow": AMBER, "orange": AMBER,
    "emerald": EMERALD, "green": EMERALD, "lime": EMERALD,
    "rose": ROSE, "red": ROSE,
    "sky": INFO, "blue": INFO, "indigo": INFO, "purple": INFO, "violet": INFO,
    "cyan": INFO, "teal": INFO, "fuchsia": INFO, "pink": INFO,
    "zinc": NEUTRAL, "neutral": NEUTRAL, "slate": NEUTRAL, "gray": NEUTRAL,
    "grey": NEUTRAL, "stone": NEUTRAL,
}

# Ngưỡng: chữ cần >= 4.5:1 trên nền trang VÀ trên bề mặt thẻ.
TEXT_MIN = 4.5


def actual_usage() -> dict[str, set[tuple[str, str, bool]]]:
    """Đọc mã để biết lớp nào THỰC SỰ được dùng, theo vai nào, có pha loãng không.

    Kiểm chứng theo giả định ("bậc 600 chắc là nền đặc") báo lỗi ở những tổ hợp
    mã không hề dùng và bỏ sót tổ hợp mã dùng thật. Đây là nguồn sự thật duy
    nhất — và phải phân biệt `bg-amber-500/20` (nền pha loãng 20%) với
    `bg-amber-500` (nền đặc): cùng một lớp, hai vai hoàn toàn khác nhau. Bản
    đầu tôi gộp hai thứ này nên tưởng có hàng chục "nút nền sáng" trong khi
    phần lớn chỉ là nền nhạt.
    """
    usage: dict[str, set[tuple[str, str, bool]]] = {}
    for p in sorted(WEB.glob("src/**/*.tsx")):
        text = p.read_text(encoding="utf-8")
        for m in re.finditer(
            r"\b(?P<util>text|bg|border|ring|fill|stroke|from|to|via|divide|decoration)"
            r"-(?P<family>[a-z]+)-(?P<step>\d{2,3})(?P<alpha>/\d+)?\b",
            text,
        ):
            fam = m.group("family")
            if fam not in RAMPS:
                continue
            diluted = m.group("alpha") is not None
            usage.setdefault(fam, set()).add((m.group("util"), m.group("step"), diluted))
    return usage


# Vai của từng bậc, suy từ cách mã dùng THẬT (đã đối chiếu từng chỗ):
#
#   bright-text   `text-emerald-400` — chữ sáng trên nền tối của hệ.
#   ink-on-solid  `text-neutral-950` — chữ TỐI trên nút nền sáng
#                 (mã viết `bg-amber-600 text-neutral-950`). Bậc này phải TỐI.
#   solid-fill    `bg-emerald-700` — nền nút đặc; mã đặt chữ tối lên hầu hết
#                 các nút này. Bậc này phải SÁNG.
#   dark-fill     `bg-amber-950` — nền tối, chữ sáng đè lên.
#
# Không một giá trị nào làm được cả bright-text lẫn dark-fill ở cùng bậc: chữ
# sáng trên nền tối cần L >= 0.204, nền tối cho chữ sáng cần L <= 0.183. Hai
# điều kiện loại trừ nhau, nên vai phải chốt theo bậc chứ không theo giá trị.
BRIGHT_TEXT_STEPS = {"100", "200", "300", "400"}
INK_ON_SOLID_STEPS = {"700", "800", "900", "950"}
SOLID_FILL_STEPS = {"500", "600"}
DARK_FILL_STEPS = {"800", "900", "950"}

# Ngưỡng: chữ cần >= 4.5:1; hình mang thông tin (chấm trạng thái) cần >= 3:1.
TEXT_MIN = 4.5
AA_GRAPHIC = 3.0
INK = "#f5ead8"       # --nq-ink, chữ sáng của hệ
WHITE = "#ffffff"     # text-white — mã dùng cho nút nền đặc
INK_DARK = "#14100c"  # --nq-accent-ink, chữ tối cho nút nền sáng
AMBER_SOLID = "#d4a017"   # --nq-st-warn, nút sáng điển hình mà mã đặt ink lên
EMERALD_SOLID = "#6f9b7a"  # --nq-st-ok


def composite(fg: str, alpha: float, bg: str) -> str:
    """Pha màu bán trong suốt lên nền — `bg-*-500/20` thật ra là màu gì trên màn hình."""
    fr, fg_, fb = hex_to_rgb(fg)
    br, bg_g, bb = hex_to_rgb(bg)
    return hex_rgb(*(fr * alpha + (br if i == 0 else bg_g if i == 1 else bb) * (1 - alpha)
                     for i, fr in enumerate((fr, fg_, fb))))


def chroma(hex_color: str) -> float:
    """Sắc độ = chênh lệch kênh lớn nhất - nhỏ nhất. 0 nghĩa là xám không sắc."""
    r, g, b = hex_to_rgb(hex_color)
    return float(max(r, g, b) - min(r, g, b))


def check() -> int:
    usage = actual_usage()
    problems = 0
    warn = 0

    print("== Kiểm chứng theo TỔ HỢP THỰC DÙNG trong mã ==")
    print(f"   nền trang {BG} · bề mặt thẻ {ELEV}\n")

    # 1. Thang phải đơn điệu ở mọi họ.
    order = ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"]
    print("== Tính đơn điệu của thang (sáng → tối) ==")
    for fam in sorted(RAMPS):
        r = RAMPS[fam]
        lums = [lum(r[s]) for s in order]
        ok = all(lums[i] > lums[i + 1] for i in range(len(lums) - 1))
        if not ok:
            problems += 1
        print(f"  {fam:<9} {'OK — giảm đều' if ok else 'HỎNG — có bậc đảo thứ tự'}")

    print("\n== Từng tổ hợp đang dùng, chấm theo vai của chính nó ==")
    for fam in sorted(usage):
        r = RAMPS[fam]
        for util, step, diluted in sorted(usage[fam]):
            if step not in r:
                continue
            hx = r[step]
            role = ""
            if diluted and util in ("bg",):
                # Nền pha loãng. Hai phép đo, cả hai đều có lý:
                #   (a) SẮC CÒN LẠI — pha loãng xong khối đó còn phân biệt được
                #       với khối họ khác không? Đây là điều mã cần: `bg-amber-950/30`
                #       và `bg-rose-950/30` cạnh nhau phải khác nhau.
                #   (b) ĐỘ NỔI so bảng mặc định — không được kém hơn hẳn.
                # Lấy (a) làm điều kiện chính vì đó là tính chất người dùng thấy;
                # (b) chỉ báo khi tụt quá 60% (mức mà mắt bắt đầu thấy mờ).
                blended = composite(hx, 0.25, BG)
                new_delta = abs(lum(blended) - lum(BG))
                hues_ok = chroma(blended) >= 3
                old_hex = DEFAULT.get(fam, {}).get(step)
                if old_hex:
                    baseline = abs(lum(composite(old_hex, 0.25, BG)) - lum(BG))
                    level_ok = new_delta >= baseline * 0.6
                    base_note = f" · độ nổi {new_delta:.4f} so mặc định {baseline:.4f}"
                else:
                    level_ok, base_note = True, ""
                ok = hues_ok and level_ok
                note = (f"nền pha loãng, sắc còn {chroma(blended):.0f}{base_note}")
                role = "wash"
            elif diluted:
                # Viền pha loãng ở alpha thấp là chi tiết trang trí; chỉ ghi nhận.
                ok = True
                note = "viền pha loãng (trang trí)"
                role = "wash-border"
            elif util in ("text", "fill", "stroke") and step in INK_ON_SOLID_STEPS:
                worst = min(ratio(hx, AMBER_SOLID), ratio(hx, EMERALD_SOLID))
                ok = worst >= TEXT_MIN
                note = f"chữ tối trên nút sáng, tệ nhất {worst:5.2f}:1"
                role = "ink-on-solid"
            elif util in ("text", "fill", "stroke"):
                worst = min(ratio(hx, BG), ratio(hx, ELEV))
                if worst >= TEXT_MIN:
                    ok, note = True, f"chữ sáng trên nền tối, tệ nhất {worst:5.2f}:1"
                else:
                    ok, note = True, f"CẢNH BÁO chữ mờ, tệ nhất {worst:5.2f}:1"
                    warn += 1
                role = "bright-text"
            elif util == "bg" and step in SOLID_FILL_STEPS:
                # `bg-*-500` trong mã có HAI cách dùng, phải chấp nhận cả hai:
                #   (a) chấm/hình chỉ báo — không có chữ trên nó, nên chuẩn là
                #       tương phản với NỀN TRANG (>= 3:1, WCAG 1.4.11 cho hình
                #       mang thông tin: chấm online/offline, đang ghi âm).
                #   (b) nền nút — có chữ đè lên, chuẩn là 4.5:1.
                # Bản trước chỉ kiểm (b) nên báo lỗi oan cho mọi chấm trạng thái.
                as_graphic = ratio(hx, BG)
                best_text = max(ratio(WHITE, hx), ratio(INK, hx), ratio(INK_DARK, hx))
                ok = as_graphic >= AA_GRAPHIC or best_text >= TEXT_MIN
                if as_graphic >= AA_GRAPHIC and best_text < TEXT_MIN:
                    note = (f"dùng làm hình chỉ báo, {as_graphic:5.2f}:1 trên nền "
                            f"(chữ trên nó chỉ {best_text:4.2f}:1 — chỉ dùng được làm chấm)")
                else:
                    note = f"nền đặc, chữ tốt nhất {best_text:5.2f}:1 / hình {as_graphic:5.2f}:1"
                role = "solid-fill"
            elif util == "bg":
                as_graphic = ratio(hx, BG)
                best_text = max(ratio(INK, hx), ratio(WHITE, hx))
                ok = as_graphic >= AA_GRAPHIC or best_text >= TEXT_MIN
                note = f"nền tối, chữ tốt nhất {best_text:5.2f}:1 / hình {as_graphic:5.2f}:1"
                role = "dark-fill"
            else:
                ok = True
                note = f"viền, {min(ratio(hx, BG), ratio(hx, ELEV)):5.2f}:1"
                role = "border"
            if not ok:
                problems += 1
                print(f"  HỎNG {util}-{fam}-{step:<4}{'/' if diluted else ' '} {hx}  {note}  "
                      f"[vai {role}]")
            elif "CẢNH BÁO" in note:
                print(f"  CẢNH BÁO {util}-{fam}-{step:<4}{'/' if diluted else ' '} {hx}  {note}")

    print(f"\n  Tổ hợp hỏng: {problems} · cảnh báo chữ mờ: {warn}")
    return problems

    print(f"\n  Tổ hợp hỏng: {problems}")
    return problems


def emit_js() -> int:
    lines: list[str] = []
    emitted: set[str] = set()
    for fam, r in RAMPS.items():
        if fam in emitted:
            continue
        body = ",\n".join(f"      {k}: '{v}'" for k, v in r.items())
        lines.append(f"    {fam}: {{\n{body},\n    }},")
    print("  colors: {\n" + "\n".join(lines) + "\n  },")
    return 0


def main() -> int:
    if "--emit-js" in sys.argv:
        return emit_js()
    # Console Windows (cp1252/cp437) không in được tiếng Việt và PowerShell làm
    # mojibake khi redirect — ghi báo cáo ra file UTF-8 để đọc lại chính xác.
    out_path = ROOT / "data" / "out" / "palette-check.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    import io

    buf = io.StringIO()
    real_stdout = sys.stdout
    sys.stdout = buf
    try:
        bad = check()
    finally:
        sys.stdout = real_stdout
    report = buf.getvalue()
    out_path.write_text(report, encoding="utf-8")
    # In bản rút gọn ra console (ASCII-safe).
    for line in report.splitlines():
        if any(k in line for k in ("HỎNG", "Tổ hợp hỏng", "đảo thứ tự")):
            print(line.encode("ascii", "replace").decode("ascii"))
    print(f"exit={bad}  report={out_path}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
