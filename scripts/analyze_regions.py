"""Do mat do noi dung theo O LUOI tren anh chup — tim vung trong / vung khong render.

Vi sao can: phan anh "toan nen den" khong phan biet duoc bang mat. Chia anh
thanh luoi NxM roi do ti le diem anh KHAC mau nen trong tung o: o nao gan 0%
la vung khong co gi. Neu noi dung chi tap trung o MOT goc con phan con lai trong
=> loi viewport/capture. Neu noi dung rai deu nhung thua => loi thiet ke.

Chay:  python scripts/analyze_regions.py <anh> [--grid 8x6] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    print("Can Pillow")
    raise SystemExit(2) from None


def analyse(path: Path, cols: int, rows: int) -> dict:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = img.load()

    counts: Counter[tuple[int, int, int]] = Counter()
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            counts[px[x, y]] += 1
    bg, _ = counts.most_common(1)[0]

    def is_bg(c: tuple[int, int, int]) -> bool:
        return abs(c[0] - bg[0]) + abs(c[1] - bg[1]) + abs(c[2] - bg[2]) <= 24

    cw, ch = w / cols, h / rows
    grid: list[list[float]] = []
    for r in range(rows):
        rowvals: list[float] = []
        for c in range(cols):
            x0, y0 = int(c * cw), int(r * ch)
            x1, y1 = int((c + 1) * cw), int((r + 1) * ch)
            tot = 0
            non = 0
            for y in range(y0, y1, 2):
                for x in range(x0, x1, 2):
                    tot += 1
                    if not is_bg(px[x, y]):
                        non += 1
            rowvals.append(round(non * 100 / tot, 1) if tot else 0.0)
        grid.append(rowvals)

    flat = [v for row in grid for v in row]
    empty_cells = sum(1 for v in flat if v < 2.0)
    dark_px = 0
    tot_px = 0
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            tot_px += 1
            c = px[x, y]
            if (c[0] + c[1] + c[2]) / 3 < 40:
                dark_px += 1

    return {
        "file": path.name,
        "size": f"{w}x{h}",
        "bg": f"#{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}",
        "content_pct": round(sum(1 for v in flat if v > 0) / len(flat) * 100, 1),
        "mean_content_pct": round(sum(flat) / len(flat), 1),
        "empty_cells": empty_cells,
        "grid_cells": len(flat),
        "dark_pct": round(dark_px * 100 / tot_px, 1),
        "grid": grid,
    }


def render(result: dict) -> None:
    print(f"\n{result['file']}  {result['size']}  nen {result['bg']}")
    print(
        f"  o co noi dung: {result['grid_cells'] - result['empty_cells']}/"
        f"{result['grid_cells']}   mat do TB: {result['mean_content_pct']}%   "
        f"diem rat toi: {result['dark_pct']}%"
    )
    print("  luoi (%, moi o = vung man hinh):")
    for row in result["grid"]:
        print("   " + " ".join(f"{v:5.1f}" for v in row))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="*")
    ap.add_argument("--grid", default="8x6")
    ap.add_argument("--json")
    a = ap.parse_args()

    cols, rows = (int(v) for v in a.grid.lower().split("x"))
    files = [Path(p) for p in a.images]
    if not files:
        d = Path("data/out/ui-review")
        files = sorted(d.glob("*.png"))[:6]

    results = []
    for f in files:
        if not f.exists():
            print(f"Thieu: {f}")
            continue
        r = analyse(f, cols, rows)
        results.append(r)
        render(r)

    if a.json:
        Path(a.json).write_text(json.dumps(results, indent=1), encoding="utf-8")
        print(f"\njson -> {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
