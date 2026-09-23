"""Cong: moi chuyen dong trong apps/web phai lay nhip tu thang nhip cua he.

Vi sao can cong nay: thang nhip trong `globals.css` (`--nq-beat-*`, `--nq-ease-*`)
chi rang buoc duoc phan CSS. `framer-motion` nhan thoi luong bang so giay ngay
trong JavaScript nen no KHONG doc duoc bien CSS. Truoc khi co `src/lib/motion.ts`,
dieu do dan den 7 moc thoi luong khac nhau trong khi thang chi dinh nghia 4 bac,
va nhung cho lech khong ai phat hien vi ma van chay.

Cong kiem bon thu:
  1. Khong tep nao ngoai `src/lib/motion.ts` khai bao thoi luong/duong cong bang so.
  2. Gia tri du phong trong `motion.ts` khop dung gia tri trong `globals.css`.
  3. Khong con vong lap `repeat: Infinity` ngoai danh sach cho phep.
  4. Moi tep dung `framer-motion` deu xu ly giam chuyen dong, tru tep tinh.

Thoat 0 = sach, 1 = co vi pham.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"
GLOBALS_CSS = WEB_SRC / "app" / "globals.css"
MOTION_TS = WEB_SRC / "lib" / "motion.ts"

# Tep duoc phep khai bao thoi luong/duong cong bang so: chinh cau noi.
EXEMPT_FILES = {MOTION_TS}

# Tep khong can xu ly giam chuyen dong vi chung khong chay chuyen dong nao:
# chi nhap `motion` de dung `AnimatePresence`, hoac khong dat `initial/animate`.
REDUCED_MOTION_EXEMPT: set[str] = set()


def iter_tsx() -> list[Path]:
    return sorted(
        p
        for p in list(WEB_SRC.rglob("*.ts")) + list(WEB_SRC.rglob("*.tsx"))
        if "node_modules" not in p.parts
    )


def rel(p: Path) -> str:
    return p.relative_to(WEB_SRC).as_posix()


def code_lines(text: str) -> list[tuple[int, str]]:
    """Boc comment truoc khi soi.

    Can thiet vi chinh cac comment trong he dung de GIAI THICH vi sao mot gia tri
    bi bo — chung trich dan dung nhung chuoi ma cong dang tim (`repeat: Infinity`,
    `duration: 0.42`). Khong loc comment thi cong bao loi tren chinh ban mo ta
    cach sua loi, va se khong ai doc duoc ket qua.

    Xu ly `//` va `/* */`. Khong dung bo phan tich cu phap day du: du an chi can
    muc do nay, va mot bo phan tich that su se keo theo rui ro sai khac.
    """
    out: list[tuple[int, str]] = []
    in_block = False
    for i, line in enumerate(text.splitlines(), 1):
        s = line
        if in_block:
            if "*/" in s:
                s = s.split("*/", 1)[1]
                in_block = False
            else:
                continue
        while "/*" in s:
            before, after = s.split("/*", 1)
            if "*/" in after:
                s = before + after.split("*/", 1)[1]
            else:
                s = before
                in_block = True
                break
        if "//" in s:
            s = s.split("//", 1)[0]
        if s.strip():
            out.append((i, s))
    return out


# ── 1. khong con so tran cho thoi luong / duong cong ─────────────────────────

# `duration: 0.42` · `duration: 1.5` — nhung KHONG bat `transitionDuration`.
_DURATION_RE = re.compile(r"(?<![-\w])duration\s*:\s*[\d.]+")
# `ease: [0.22, 1, 0.36, 1]` · `ease: "circOut"`
_EASE_LITERAL_RE = re.compile(r"(?<![-\w])ease\s*:\s*(\[|\"|')")
# `damping: 25, stiffness: 250` — lo xo khai truc tiep thay vi qua springFor().
_SPRING_RE = re.compile(r"(?<![-\w])(stiffness|damping)\s*:\s*[\d.]+")


def check_hardcoded() -> list[str]:
    out: list[str] = []
    for p in iter_tsx():
        if p in EXEMPT_FILES:
            continue
        for i, line in code_lines(p.read_text(encoding="utf-8")):
            stripped = line.strip()
            for name, rx in (
                ("thoi luong", _DURATION_RE),
                ("duong cong", _EASE_LITERAL_RE),
                ("lo xo", _SPRING_RE),
            ):
                if rx.search(line):
                    out.append(f"{rel(p)}:{i}: {name} khai bang so → {stripped[:88]}")
    return out


# ── 2. du phong trong motion.ts khop globals.css ────────────────────────────


def parse_css_tokens() -> dict[str, str]:
    css = GLOBALS_CSS.read_text(encoding="utf-8")
    tokens: dict[str, str] = {}
    for m in re.finditer(r"(--nq-(?:beat|ease)-[\w-]+)\s*:\s*([^;]+);", css):
        name, value = m.group(1), m.group(2).strip()
        tokens[name] = value
    return tokens


def check_fallbacks() -> list[str]:
    css = parse_css_tokens()
    ts = MOTION_TS.read_text(encoding="utf-8")
    out: list[str] = []

    # Bốn bậc nhịp: FALLBACK_SECONDS phải khớp --nq-beat-* trong CSS.
    block = re.search(r"FALLBACK_SECONDS[^{]*\{(.*?)\}", ts, re.S)
    if not block:
        return ["motion.ts: khong tim thay FALLBACK_SECONDS"]
    ts_beats = dict(re.findall(r"(\w+)\s*:\s*([\d.]+)", block.group(1)))

    for beat in ("ack", "settle", "focus", "chapter"):
        css_raw = css.get(f"--nq-beat-{beat}", "")
        m = re.match(r"^([\d.]+)(ms|s)$", css_raw)
        if not m:
            out.append(f"globals.css: khong doc duoc --nq-beat-{beat} (gia tri: {css_raw!r})")
            continue
        css_s = float(m.group(1)) / (1000 if m.group(2) == "ms" else 1)
        ts_s = ts_beats.get(beat)
        if ts_s is None:
            out.append(f"motion.ts: FALLBACK_SECONDS thieu bac {beat!r}")
        elif abs(float(ts_s) - css_s) > 1e-9:
            out.append(
                f"motion.ts: FALLBACK_SECONDS.{beat} = {ts_s} nhung "
                f"--nq-beat-{beat} = {css_raw} ({css_s}s)"
            )

    # Hai đường cong: mảng số trong motion.ts phải khớp cubic-bezier trong CSS.
    for ts_name, css_name in (
        ("FALLBACK_EASE_OUT", "--nq-ease-out"),
        ("FALLBACK_EASE_INOUT", "--nq-ease-inout"),
    ):
        m = re.search(rf"{ts_name}\s*:\s*Cubic\s*=\s*\[([^\]]+)\]", ts)
        if not m:
            out.append(f"motion.ts: khong tim thay {ts_name}")
            continue
        ts_vals = [float(x.strip()) for x in m.group(1).split(",")]
        css_raw = css.get(css_name, "")
        cm = re.match(r"^cubic-bezier\(([^)]*)\)$", css_raw)
        if not cm:
            out.append(f"globals.css: khong doc duoc {css_name} (gia tri: {css_raw!r})")
            continue
        css_vals = [float(x.strip()) for x in cm.group(1).split(",")]
        if ts_vals != css_vals:
            out.append(f"motion.ts: {ts_name} = {ts_vals} nhung {css_name} = {css_vals}")
    return out


# ── 3. vong lap vo han ──────────────────────────────────────────────────────

# Cho phep: vong lap do NGUOI DUNG khoi dong (tro vao moi quay). Cam: vong lap tu
# chay khi tai trang. Phan biet bang cach doc ngu canh quanh dong do.
ALLOWED_INFINITE: list[tuple[str, str]] = [
    ("ui/Logo.tsx", "whileHover"),
]


def check_infinite_loops() -> list[str]:
    out: list[str] = []
    allowed = {f for f, _ in ALLOWED_INFINITE}
    for p in iter_tsx():
        lines = code_lines(p.read_text(encoding="utf-8"))
        joined = "\n".join(s for _, s in lines)
        if "Infinity" not in joined:
            continue
        for i, line in lines:
            if "repeat" not in line or "Infinity" not in line:
                continue
            if rel(p) in allowed:
                # Trong tep duoc phep: chi chap nhan khi gan voi `hover`.
                window = "\n".join(s for n, s in lines if i - 12 <= n < i)
                if "hover" not in window:
                    out.append(
                        f"{rel(p)}:{i}: vong lap vo han KHONG gan voi hover "
                        f"(tu chay khi tai trang)"
                    )
            else:
                out.append(f"{rel(p)}:{i}: vong lap vo han → {line.strip()[:88]}")
    return out


# ── 4. tep dung framer-motion phai xu ly giam chuyen dong ───────────────────


def check_reduced_motion() -> list[str]:
    out: list[str] = []
    for p in iter_tsx():
        text = p.read_text(encoding="utf-8")
        if "framer-motion" not in text:
            continue
        code = "\n".join(s for _, s in code_lines(text))
        # Tep chi dung `motion.` lam lop boc tinh (khong dat initial/animate) thi
        # khong chay chuyen dong nao.
        if "initial" not in code and "animate" not in code:
            continue
        if rel(p) in REDUCED_MOTION_EXEMPT:
            continue
        if "useReducedMotion" not in text and "prefers-reduced-motion" not in text:
            out.append(f"{rel(p)}: dung framer-motion co chuyen dong nhung KHONG xu ly giam chuyen dong")
    return out


# ── 5. chuyen dong 3D (react-three-fiber) ───────────────────────────────────

# Tep 3D duoc phep ghi truc tiep vao `position`/`rotation`/`scale` trong `useFrame`:
# chuyen dong o day la CHUC NANG (xoay theo trang thai, hat di len theo du lieu),
# khong phai chuyen tiep CSS, nen khong the di qua thang nhip.
R3F_ALLOWED_FILES = {
    "ui/experience/quanverse/LivingMap3d.tsx",
    "ui/experience/spatial/SpatialMap3d.tsx",
    "ui/hom-nay/ops-pulse.tsx",
}

# Moc thoi gian tuyet doi dung trong vong ve lam pha nhịp phu thuoc thoi diem mo
# trang. `state.clock.elapsedTime` moi la moc cua chinh khung hinh.
_WALLCLOCK_RE = re.compile(r"(?<![-\w])Date\.now\(\)")
# Vong lap vo han tu chay trong khong gian 3D: xoay lien tuc khong theo du lieu.
#
# Bat dang `rotation.x += delta * <so>` — dang ma loi that da mang. Cach nhan biet:
# toc do la MOT HANG SO viet ngay tai cho, nen khong the phu thuoc du lieu.
#
# GIOI HAN DA BIET: khong bat duoc dang `const s = 0.05; ... += delta * s`. Co gang
# bat no doi hoi phan tich luong du lieu, va se bao dong gia ngay tai
# `LivingMap3d`/`ops-pulse` — noi toc do la `delta * (0.3 + load * 0.7)`, tuc bien
# thien theo trang thai va HOAN TOAN dung. Tha mot cong hep ma khong bao dong gia
# con hon mot cong rong ma khong ai tin. `prove_motion_gate.py` ghi ro gioi han nay
# bang chinh ca kiem `xoay deu (qua bien)`.
_IDLE_SPIN_RE = re.compile(r"rotation\.\w\s*\+=\s*delta\s*\*\s*0?\.\d+")


def check_3d() -> list[str]:
    out: list[str] = []
    for p in iter_tsx():
        text = p.read_text(encoding="utf-8")
        if "useFrame" not in text:
            continue
        lines = code_lines(text)

        # 5a. Đồng hồ tuyệt đối trong vòng vẽ.
        for i, line in lines:
            if _WALLCLOCK_RE.search(line):
                out.append(
                    f"{rel(p)}:{i}: dung `Date.now()` trong vong ve → pha nhịp phu "
                    f"thuoc thoi diem mo trang, dung `state.clock.elapsedTime`"
                )

        # 5b. Vong xoay roi trong `useFrame` = chuyen dong khong ma hoa thong tin.
        #
        # Chi soi cac tep KHONG nam trong danh sach cho phep, de tranh bao dong
        # gia: o `LivingMap3d`/`ops-pulse`, toc do xoay LA du lieu
        # (`delta * (0.3 + load * 0.7)`) nen bien thien theo trang thai — dung.
        if rel(p) in R3F_ALLOWED_FILES:
            continue
        for i, line in lines:
            if _IDLE_SPIN_RE.search(line):
                out.append(
                    f"{rel(p)}:{i}: xoay deu trong `useFrame` voi toc do hang so "
                    f"→ chuyen dong khong ma hoa thong tin"
                )
    return out


def main() -> int:
    sections = [
        ("1. So tran cho thoi luong / duong cong", check_hardcoded()),
        ("2. Du phong trong motion.ts khop globals.css", check_fallbacks()),
        ("3. Vong lap vo han", check_infinite_loops()),
        ("4. Tep chuyen dong phai xu ly giam chuyen dong", check_reduced_motion()),
        ("5. Chuyen dong 3D (react-three-fiber)", check_3d()),
    ]
    total = 0
    for title, problems in sections:
        print(f"=== {title} ===")
        if problems:
            total += len(problems)
            for x in problems:
                print(f"  [X] {x}")
        else:
            print("  [OK] 0 vi pham")
        print()
    print(f"=== TONG: {total} vi pham ===")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
