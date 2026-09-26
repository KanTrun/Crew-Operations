"""So sánh trực quan mask v1 (production) vs v2 (prototype), zoom ở rìa ly.

Chạy: python scripts/_cmp_seg.py [ảnh]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "agents" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ca_agents import bg_redesign as B  # noqa: E402
from _proto_seg import subject_alpha_v2  # noqa: E402

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)


def cutout(img: Image.Image, alpha: np.ndarray, bg=(30, 40, 120)) -> Image.Image:
    rgba = img.convert("RGBA")
    rgba.putalpha(Image.fromarray((alpha * 255).astype(np.uint8)))
    canvas = Image.new("RGBA", img.size, (*bg, 255))
    canvas.alpha_composite(rgba)
    return canvas.convert("RGB")


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "data/menu_images/mon_tra.jpg")
    img = Image.open(src).convert("RGB")
    w0, h0 = img.size
    ratio = min(1.0, B._MASK_MAX_DIM / max(w0, h0))
    small = img.resize((max(2, int(w0 * ratio)), max(2, int(h0 * ratio))),
                       Image.Resampling.LANCZOS)

    a1 = B._subject_alpha(small, None)
    a2, info = subject_alpha_v2(small, None)
    assert a1 is not None and a2 is not None

    print(f"{src.name}: v1 subject={(a1 > 0.5).mean():.3f}  v2 subject={(a2 > 0.5).mean():.3f}")
    print("v2 info:", {k: v for k, v in info.items() if k != "clusters"})

    # Hợp và giao của hai mask → thấy v2 thêm/bớt cái gì.
    x1, x2 = a1 > 0.5, a2 > 0.5
    print(f"  v1 only = {(x1 & ~x2).mean():.3f}  v2 only = {(x2 & ~x1).mean():.3f}  "
          f"chung = {(x1 & x2).mean():.3f}")

    base = np.asarray(small).copy()
    diff = base.copy()
    diff[x1 & x2] = (0.5 * base[x1 & x2] + 0.5 * np.array([0, 200, 0])).astype(np.uint8)
    diff[x1 & ~x2] = (0.35 * base[x1 & ~x2] + 0.65 * np.array([255, 0, 0])).astype(np.uint8)
    diff[x2 & ~x1] = (0.35 * base[x2 & ~x1] + 0.65 * np.array([0, 90, 255])).astype(np.uint8)

    panels = [small, Image.fromarray(diff), cutout(small, a1), cutout(small, a2)]
    labels = ["gốc", "đỏ=v1 thừa, xanh=v2 thêm", "v1 (cũ)", "v2 (mới)"]
    W = small.width
    H = small.height
    sheet = Image.new("RGB", (W * 4 + 30, H + 22), (20, 20, 20))
    for i, (p, _t) in enumerate(zip(panels, labels)):
        sheet.paste(p, (i * (W + 10), 22))
    sheet.save(OUT / f"cmp_{src.stem}.png")

    # Zoom rìa ly (hộp bao mask v2 + đệm).
    ys, xs = np.nonzero(a2 > 0.05)
    pad = 26
    bx0, bx1 = max(0, int(xs.min()) - pad), min(W, int(xs.max()) + pad)
    by0, by1 = max(0, int(ys.min()) - pad), min(H, int(ys.max()) + pad)
    zoom = sheet.crop((0, 0, sheet.width, sheet.height)).resize((sheet.width, sheet.height))
    crop = Image.new("RGB", ((bx1 - bx0) * 4 + 30, (by1 - by0)), (20, 20, 20))
    for i, p in enumerate(panels):
        crop.paste(p.crop((bx0, by0, bx1, by1)), (i * (bx1 - bx0 + 10), 0))
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.Resampling.LANCZOS)
    crop.save(OUT / f"cmp_{src.stem}_zoom.png")
    del zoom


if __name__ == "__main__":
    main()
