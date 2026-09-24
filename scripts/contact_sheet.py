"""Ghep nhieu anh chup thanh MOT bang lien lac (contact sheet) de nhin toan bo he thong.

Vi sao: 44 trang, moi lan mo mot anh la 44 luot. Ghep lai thi thay duoc CA he thong
trong mot khung va de phat hien "trang nao lech tong" — thu ma nhin tung anh roi roi
se bo sot. Anh goc KHONG bi sua (chi thu nho de ghep).

Chay:  python scripts/contact_sheet.py <thu_muc> [--cols 4] [--w 420] [--out file.png] [--only a,b,c]
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    print("Can Pillow")
    raise SystemExit(2) from None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--w", type=int, default=420)
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default=None, help="danh sach slug cach nhau dau phay")
    a = ap.parse_args()

    folder = Path(a.folder)
    files = sorted(p for p in folder.glob("*.png") if "__full" not in p.name)
    if a.only:
        want = {s.strip() for s in a.only.split(",")}
        files = [f for f in files if f.stem in want]

    if not files:
        print("Khong co anh.")
        return 1

    tw = a.w
    thumbs = []
    for f in files:
        im = Image.open(f).convert("RGB")
        th = int(im.height * tw / im.width)
        thumbs.append((f.stem, im.resize((tw, th), Image.LANCZOS)))

    cols = a.cols
    rows = (len(thumbs) + cols - 1) // cols
    label_h = 22
    cell_h = max(t.height for _, t in thumbs) + label_h
    pad = 8

    W = cols * (tw + pad) + pad
    H = rows * (cell_h + pad) + pad
    sheet = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(sheet)

    for i, (name, t) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = pad + r * (cell_h + pad)
        d.text((x + 2, y + 4), name[:52], fill=(230, 230, 230))
        sheet.paste(t, (x, y + label_h))

    out = Path(a.out) if a.out else folder / "_contact-sheet.png"
    sheet.save(out)
    print(f"{len(thumbs)} anh -> {out}  ({W}x{H})")
    print("  thu tu: " + ", ".join(n for n, _ in thumbs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
