"""Kiem chung tuong phan bang DIEM ANH that trong vung chu.

Vi sao can: bo quet tuong phan tinh toan tu CSS co the sai khi nen duoc ve bang
pseudo-element, gradient nhieu diem, hoac hoa tron lop. Cach duy nhat chac chan
la dem diem anh: trong vung chu phai co NHIEU diem sang (mau chu) va NHIEU diem
toi (mau nen). Neu ca vung chi mot mau => chu khong hien ra.

Chay: python scripts/verify_contrast_pixels.py <anh> [...]
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    print("Can Pillow")
    raise SystemExit(2)


def lum(c: tuple[int, int, int]) -> float:
    def f(v: float) -> float:
        x = v / 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4

    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    l1, l2 = lum(a), lum(b)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def describe(path: Path) -> None:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = list(img.getdata())
    counts = Counter(px)
    total = len(px)

    print(f"\n{path.name}  {w}x{h}")
    top5 = counts.most_common(5)
    for c, n in top5:
        print(f"    rgb{c}  {n * 100 / total:5.1f}%  do sang {lum(c):.4f}")

    # Mau nen = mau pho bien nhat. Mau chu = mau THUONG GAP NHAT trong so cac mau
    # CACH XA mau nen — khong phai mau pho bien thu hai.
    # Vi sao: o co gradient/bo goc thi mau pho bien thu hai chi la mot sac do khac
    # cua chinh cai nen (vd #d4a017 va #d9aa31), so sanh hai mau do cho ra "1.10:1"
    # nghe nhu loi trong khi thuc te chu van doc duoc. Phai tim diem anh KHAC HAN nen.
    bg, _ = top5[0]

    def far(c: tuple[int, int, int]) -> bool:
        return abs(c[0] - bg[0]) + abs(c[1] - bg[1]) + abs(c[2] - bg[2]) > 60

    cand = [(c, n) for c, n in counts.items() if far(c)]
    if cand:
        fg, fgn = max(cand, key=lambda kv: kv[1])
        r = ratio(bg, fg)
        print(
            f"  -> nen rgb{bg} vs chu rgb{fg} ({fgn * 100 / total:.2f}% diem anh)"
            f"  tuong phan {r:.2f}:1  {'DAT' if r >= 4.5 else 'DUOI 4.5'}"
        )
    else:
        print("  -> CHI MOT MAU: khong co diem anh tuong phan => chu khong hien ra")

    # Bien do sang: vung chu that phai trai rong.
    ls = sorted(lum(c) for c in px)
    lo, hi = ls[int(len(ls) * 0.02)], ls[int(len(ls) * 0.98)]
    print(f"  do sang: p2={lo:.4f}  p98={hi:.4f}  bien do={hi - lo:.4f}")
    print(
        f"  so mau khac nhau: {len(counts)}"
        + ("   => GAN NHU MOT MAU (chu khong hien?)" if len(counts) < 12 else "")
    )


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("Can duong dan anh.")
        return 1
    for a in args:
        p = Path(a)
        if p.exists():
            describe(p)
        else:
            print(f"Thieu: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
