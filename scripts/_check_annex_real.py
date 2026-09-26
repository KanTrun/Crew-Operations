"""Kiểm tra trực quan cấu hình annex đã chọn trên ảnh THẬT.

Chạy: python scripts/_check_annex_real.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _proto_seg9 import clean, grabcut_rect, rect_from_bbox  # noqa: E402
from _sweep_annex import annex_tuned  # noqa: E402

OUT = Path("data/menu_images/_debug")
FG_MAX, BG_MIN, RING = 70.0, 55.0, 34


def main() -> None:
    for src in ("data/menu_images/mon_tra.jpg", "data/menu_images/mon_den.png"):
        p = Path(src)
        im = Image.open(p).convert("RGB")
        w0, h0 = im.size
        r = min(1.0, 640 / max(w0, h0))
        small = im.resize((max(2, int(w0 * r)), max(2, int(h0 * r))), Image.Resampling.LANCZOS)
        img = np.asarray(small)
        bbox = (0.22, 0.10, 0.80, 0.88)
        base = clean(grabcut_rect(img, rect_from_bbox(bbox, small.width, small.height)))
        assert base is not None
        grew = clean(annex_tuned(img, base, FG_MAX, BG_MIN, RING))
        assert grew is not None
        added = grew & ~base

        # Ảnh: gốc | GrabCut | +annex (cam = thêm) | cutout trên nền tối
        v1 = np.asarray(small).copy()
        v1[base] = (0.5 * v1[base] + 0.5 * np.array([0, 220, 0])).astype(np.uint8)
        v2 = np.asarray(small).copy()
        v2[base] = (0.5 * v2[base] + 0.5 * np.array([0, 220, 0])).astype(np.uint8)
        v2[added] = (0.25 * v2[added] + 0.75 * np.array([255, 140, 0])).astype(np.uint8)

        canvas = Image.new("RGBA", small.size, (26, 18, 12, 255))
        d = ImageDraw.Draw(canvas)
        d.rectangle([0, int(small.height * 0.72), small.width, small.height],
                    fill=(40, 28, 18, 255))
        rgba = small.convert("RGBA")
        rgba.putalpha(Image.fromarray((grew * 255).astype(np.uint8)))
        canvas.alpha_composite(rgba)

        panels = [small, Image.fromarray(v1), Image.fromarray(v2), canvas.convert("RGB")]
        sheet = Image.new("RGB", (small.width * 4 + 30, small.height), (25, 25, 25))
        for i, pan in enumerate(panels):
            sheet.paste(pan, (i * (small.width + 10), 0))
        sheet.save(OUT / f"annex_{p.stem}.png")

        # Zoom vùng có pixel thêm.
        if added.any():
            ys, _xs = np.nonzero(added)
            pad = 50
            y0, y1 = max(0, int(ys.min()) - pad), min(small.height, int(ys.max()) + pad)
            z = sheet.crop((0, y0, sheet.width, y1))
            z = z.resize((z.width * 2, z.height * 2), Image.Resampling.LANCZOS)
            z.save(OUT / f"annex_{p.stem}_zoom.png")
        print(f"{p.name}: base={base.mean():.3f} grew={grew.mean():.3f} "
              f"added={int(added.sum())}px")


if __name__ == "__main__":
    main()
