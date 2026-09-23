"""Thay chuỗi bề mặt cũ trong kit.tsx bằng lớp bề mặt của hệ thống.

Chuỗi `bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)]` lặp 25 lần
trong kit.tsx — viền 2px không bo góc, không đổ bóng. Đó là nguồn của cảm giác
"toàn khung vuông". Script này thay bằng `.nq-surface-*` (có bo góc + bậc nổi).

Chạy một lần: python scripts/patch_kit_surfaces.py
"""

from __future__ import annotations

import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "apps" / "web" / "src" / "ui" / "kit.tsx"

PAIRS: list[tuple[str, str]] = [
    # Khung xương tải (skeleton) — dùng chính lớp skeleton của hệ.
    (
        'className="w-full bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)]" aria-hidden="true"',
        'className="nq-skeleton nq-skeleton--block w-full" aria-hidden="true"',
    ),
    # Thanh tiến trình — hệ đã có `.nq-progress`.
    (
        "`w-full h-4 bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] overflow-hidden ${className}`",
        "`nq-progress w-full ${className}`",
    ),
    # Ô khoá/mã dùng chung.
    (
        ': "bg-[var(--nq-surface-hi)] text-[var(--nq-fg)] border-2 border-[var(--nq-dim)]";',
        ': "nq-surface-row text-[var(--nq-fg)]";',
    ),
    # Thẻ bấm được trong lưới.
    (
        "`flex flex-col p-4 shadow-[4px_4px_0px_0px_var(--nq-copper-dim)] ${bg}`",
        "`nq-surface-tile flex flex-col p-4 ${bg}`",
    ),
    (
        'className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6 md:p-8 mt-12 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]"',
        'className="nq-surface-block p-6 md:p-8 mt-12"',
    ),
    (
        'className="mb-10 w-full border-2 border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] p-6 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]"',
        'className="nq-surface-block mb-10 w-full p-6"',
    ),
    (
        'className="flex items-center justify-between p-4 bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] text-[var(--nq-fg)]"',
        'className="nq-surface-row nq-surface-row--between"',
    ),
    # Thẻ liên kết — bỏ viền 2px và hover đổi viền, dùng bậc nổi.
    (
        "`bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6 hover:border-[var(--nq-copper)] ",
        "`nq-surface-tile p-6 ",
    ),
    (
        "`nq-summary-cell flex min-w-[140px] flex-1 flex-col p-4 shadow-[4px_4px_0px_0px_var(--nq-copper-dim)] ${bg}`",
        "`nq-summary-cell nq-surface-tile flex min-w-[140px] flex-1 flex-col p-4 ${bg}`",
    ),
    (
        'className="w-full text-left bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]',
        'className="nq-surface-tile w-full p-6 text-left',
    ),
    # Khung bảng cuộn.
    (
        'className="overflow-x-auto bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]"',
        'className="nq-surface-frame overflow-x-auto"',
    ),
]


def main() -> int:
    text = io.open(TARGET, encoding="utf-8").read()
    applied = 0
    for old, new in PAIRS:
        if old in text:
            text = text.replace(old, new)
            applied += 1
        else:
            print("KHÔNG KHỚP:", old[:88])
    io.open(TARGET, "w", encoding="utf-8", newline="\n").write(text)
    print(f"Đã thay {applied}/{len(PAIRS)} chuỗi trong {TARGET.name}")
    return 0 if applied == len(PAIRS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
