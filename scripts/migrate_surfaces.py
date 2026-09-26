"""Chuyen chuoi be mat thu cong sang lop be mat dung chung — NHIP QUAN.

VAN DE: markup lap lai chuoi `border-2 border-[var(--nq-dim)] bg-[var(--nq-surface)]`
o 64 cho/16 file. He qua khong chi la "thua chu": vien 2px KHONG bo goc + khong do
bong o MOI khoi nghia la moi khoi cung mot bac noi — khong phan tang duoc "khoi nay
bam duoc" / "khoi nay chi de doc" / "nhom thong tin". Mat nguoi doc ra mot trang
toan khung vuong phang giong nhau, dung loi phan nan ban dau.

CACH SUA: thay bang lop be mat da co trong `@layer components` cua globals.css —
`nq-surface-row` (dong, elev-1), `nq-surface-block` (khoi doc, elev-1),
`nq-surface-tile` (o bam duoc, elev-2). Ba lop nay da bo goc theo token, do bong
theo vai, va chuyen dong theo nhip chung. Sua o TANG LOP nghia la moi cho dung
sau nay tu dong dung.

BONG LECH CUNG (brutalist): `shadow-[8px_8px_0_var(...)]` la kieu do bong cua ban
dung web tho, khong thuoc he do bong nao. Thay bang `shadow-[var(--nq-elev-2)]`.

Chay:  .venv\\Scripts\\python.exe scripts/migrate_surfaces.py [--dry]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "apps" / "web" / "src"

# (regex, thay the, mo ta). Thu tu QUAN TRONG: dai truoc, ngan sau.
RULES: list[tuple[str, str, str]] = [
    # ── Be mat co vien dim + nen surface ────────────────────────────────────
    # O bam duoc dac trung: co hover doi vien hoac cursor-pointer
    (
        r"border-2 border-\[var\(--nq-dim\)\] bg-\[var\(--nq-surface\)\] transition-colors hover:border-\[var\(--nq-copper\)\]",
        "nq-surface-tile transition-colors hover:border-[var(--nq-copper)]",
        "o bam duoc: vien dim -> tile (elev-2)",
    ),
    (
        r"border-2 border-\[var\(--nq-dim\)\] hover:border-\[var\(--nq-copper\)\]",
        "nq-surface-tile hover:border-[var(--nq-copper)]",
        "o bam duoc (khong nen rieng) -> tile",
    ),
    (
        r"border-2 border-\[var\(--nq-dim\)\] bg-\[var\(--nq-surface\)\]",
        "nq-surface-row",
        "dong/khoi doc: vien dim + surface -> row (elev-1)",
    ),
    (
        r"border-2 border-\[var\(--nq-dim\)\] bg-\[var\(--nq-surface-hi\)\]",
        "nq-surface-block",
        "khoi doc: vien dim + surface-hi -> block (elev-1)",
    ),
    # ── Vien copper: nhan manh, dung cho khoi can chu y ─────────────────────
    (
        r"border-2 border-\[var\(--nq-copper\)\] bg-\[var\(--nq-surface\)\]",
        "nq-surface-block border-[var(--nq-copper)]",
        "khoi nhan manh: vien copper -> block + vien copper",
    ),
    # ── Do bong lech cung (brutalist) ───────────────────────────────────────
    (
        r"shadow-\[-?[\d.]+px_[\d.]+px_0(?:px)?_0(?:px)?_var\(--nq-copper-dim\)\]",
        "shadow-[var(--nq-elev-2)]",
        "bong lech cung -> do bong theo bac (elev-2)",
    ),
    (
        r"shadow-\[-?[\d.]+px_[\d.]+px_0(?:px)?_var\(--nq-copper-dim\)\]",
        "shadow-[var(--nq-elev-2)]",
        "bong lech cung (3 phan) -> elev-2",
    ),
    # ── Vien dim don le, khong nen ──────────────────────────────────────────
    (
        r"\bborder-2 border-\[var\(--nq-dim\)\]\b",
        "border border-[var(--nq-line)]",
        "vien dim don le -> vien 1px theo token duong ke",
    ),
    # ── Vien dim + nen rieng (bg khac surface) ──────────────────────────────
    (
        r"border-2 border-\[var\(--nq-dim\)\] bg-\[var\(--nq-bg\)\]",
        "nq-surface-row bg-[var(--nq-bg)]",
        "o co vien dim tren nen trang -> row",
    ),
    # ── border-2 tran + padding (khong neu mau) ─────────────────────────────
    (
        r"\bborder-2 p-([\d.]+) transition-all rounded\b",
        r"nq-surface-tile p-\1 transition-all",
        "o bam duoc: border-2 tron -> tile",
    ),
    (
        r"\bborder-2 p-([\d.]+) rounded\b",
        r"nq-surface-block p-\1",
        "khoi: border-2 tron -> block",
    ),
    (
        r"\bspace-y-4 border-2 border-\[var\(--nq-dim\)\] p-([\d.]+)\b",
        r"nq-surface-block space-y-4 p-\1",
        "khoi cau hinh -> block",
    ),
    (
        r"\bborder-2 border-\[var\(--nq-dim\)\] p-([\d.]+) rounded\b",
        r"nq-surface-block p-\1",
        "khoi: vien dim -> block",
    ),
    (
        r"\bm-0 border-2 border-\[var\(--nq-dim\)\]\b",
        "m-0 border border-[var(--nq-line)]",
        "o giua vien dim -> vien 1px",
    ),
    # ── Vien dinh huong day 2px ─────────────────────────────────────────────
    # `border-b-2`/`border-t-2`/`border-l-2` la vach ke 2px. Vach ke khong phai
    # be mat — no chi chia khong gian — nen phai mong va theo token duong ke, giong
    # moi vach ke khac trong he. 2px day lam moi duong phan cach nang tri, khong
    # phan tang duoc gi.
    #
    # BAY REGEX: KHONG duoc viet `\bborder-b-2` — `-` khong phai ky tu word, nen
    # `\b` giua dau cach va `b` cua "border" ton tai, nhung y dinh "khong khop
    # giua tu" khong dat duoc theo cach do khi dau la dau gach. Dung `(?<![-\w])`
    # de chan khop vao duoi cua class khac (vd `nq-border-b-2`).
    (
        r"(?<![-\w])border-b-2 border-\[var\(--nq-dim\)\]",
        "border-b border-[var(--nq-line)]",
        "vach ke duoi 2px -> 1px theo token",
    ),
    (
        r"(?<![-\w])border-t-2 border-dashed border-\[var\(--nq-dim\)\]",
        "border-t border-dashed border-[var(--nq-line)]",
        "vach ke tren 2px net dut -> 1px",
    ),
    (
        r"(?<![-\w])border-t-2 border-\[var\(--nq-dim\)\]",
        "border-t border-[var(--nq-line)]",
        "vach ke tren 2px -> 1px theo token",
    ),
]


def main() -> int:
    dry = "--dry" in sys.argv
    grand = 0
    for p in sorted(SRC.rglob("*.tsx")):
        orig = p.read_text(encoding="utf-8")
        t = orig
        applied: list[tuple[str, int]] = []
        for rx, rep, label in RULES:
            t2, n = re.subn(rx, rep, t)
            if n:
                applied.append((f"{label} x{n}", n))
                t = t2
        if t != orig:
            n = sum(c for _, c in applied)
            grand += n
            print(f"\n{p.relative_to(ROOT).as_posix()}  ({n})")
            for label, _c in applied:
                print(f"    {label}")
            if not dry:
                p.write_text(t, encoding="utf-8")

    print(f"\nTONG: {grand} thay the{' (DRY RUN)' if dry else ''}")
    if not dry:
        print("Kiem lai: python scripts/find_square_surfaces.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
