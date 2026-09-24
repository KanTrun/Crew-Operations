"""Thay chuỗi bề mặt vuông bằng lớp bề mặt của hệ thống — NHỊP QUÁN.

Vì sao làm bằng script chứ không sửa tay: cùng một chuỗi Tailwind trần
(`border-2 border-[var(--nq-dim)]`, `bg-[var(--nq-surface)]`) lặp lại ở hàng
chục trang với nhiều biến thể thứ tự thuộc tính. Sửa tay từng chỗ vừa chậm vừa
dễ sót và dễ tạo khác biệt mới giữa các trang — trong khi mục tiêu là làm chúng
GIỐNG nhau.

Nguyên tắc thay:
  - bỏ `border-2 border-[var(--nq-dim)]`  → dùng `.nq-surface-*` (có bo góc + bậc nổi)
  - bỏ `bg-[var(--nq-surface)]` trần khi đã có lớp bề mặt  → tránh chồng nền
  - giữ nguyên mọi thuộc tính bố cục (padding, grid, flex, gap)

Chạy:  python scripts/patch_square_surfaces.py [--dry]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "apps" / "web" / "src"

# Mỗi quy tắc: (mẫu regex, thay thế, mô tả). Áp theo thứ tự.
RULES: list[tuple[str, str, str]] = [
    # ── Bề mặt có viền + nền của hệ → lớp bề mặt chung (đã bo góc + đổ bóng) ──
    (
        r"bg-\[var\(--nq-surface-hi\)\]\s+border-2\s+border-\[var\(--nq-dim\)\]",
        "nq-surface-block",
        "nền surface-hi + viền 2px → nq-surface-block",
    ),
    (
        r"border-2\s+border-\[var\(--nq-dim\)\]\s+bg-\[var\(--nq-surface-hi\)\]",
        "nq-surface-block",
        "viền 2px + nền surface-hi → nq-surface-block",
    ),
    (
        r"bg-\[var\(--nq-surface\)\]\s+border-2\s+border-\[var\(--nq-dim\)\]",
        "nq-surface-block",
        "nền surface + viền 2px → nq-surface-block",
    ),
    (
        r"border-2\s+border-\[var\(--nq-dim\)\]\s+bg-\[var\(--nq-surface\)\]",
        "nq-surface-block",
        "viền 2px + nền surface → nq-surface-block",
    ),
    (
        r"bg-\[var\(--nq-surface-hi\)\]\s+border-2\s+border-\[var\(--nq-dim\)\]/50",
        "nq-surface-block",
        "nền surface-hi + viền 2px/50 → nq-surface-block",
    ),
    # ── Viền 2px màu copper (khối được nhấn) → bề mặt có viền accent mềm ──
    (
        r"border-2\s+border-\[var\(--nq-copper\)\]",
        "nq-surface-accent",
        "viền 2px copper → nq-surface-accent",
    ),
    (
        r"border-2\s+border-\[var\(--nq-dim\)\]/50",
        "nq-surface-hairline",
        "viền 2px dim/50 → viền mảnh",
    ),
    # ── Còn lại: viền 2px trơn, kèm nền tuỳ biến ──
    (
        r"border-2\s+border-\[var\(--nq-dim\)\]",
        "nq-surface-hairline",
        "viền 2px dim → viền mảnh có nền",
    ),
    (
        r"border-2\s+border-\[var\(--nq-line\)\]",
        "nq-surface-hairline",
        "viền 2px line → viền mảnh có nền",
    ),
]


def patch(text: str) -> tuple[str, int]:
    n = 0
    for pat, repl, _label in RULES:
        text, k = re.subn(pat, repl, text)
        n += k
    # Dọn khoảng trắng đôi do thay thế để lại.
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r'"\s+', '"', text, count=0)
    return text, n


def main() -> int:
    dry = "--dry" in sys.argv
    total = 0
    changed: list[str] = []
    for p in sorted(SRC.rglob("*.tsx")):
        original = open(p, encoding="utf-8").read()
        patched, n = patch(original)
        if n and patched != original:
            total += n
            changed.append(f"{p.relative_to(SRC).as_posix()}  ({n} chỗ)")
            if not dry:
                open(p, "w", encoding="utf-8", newline="\n").write(patched)
    print(f"{'[DRY] ' if dry else ''}Đã thay {total} chuỗi trong {len(changed)} file:")
    for c in changed:
        print("   ", c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
