"""Soi mask cuối cùng: cutout ở ĐỘ PHÂN GIẢI GỐC trên nền tím, cạnh ảnh gốc.

Chạy: python scripts/_diag_mask_hires.py [ảnh]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "agents" / "src"))

from ca_agents import bg_redesign as B  # noqa: E402

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "data/menu_images/mon_tra.jpg")
    raw = src.read_bytes()
    img = B._decode_original(raw)
    assert img is not None
    w0, h0 = img.size
    ratio = min(1.0, B._MASK_MAX_DIM / max(w0, h0))
    small = img.convert("RGB").resize(
        (max(2, int(w0 * ratio)), max(2, int(h0 * ratio))), Image.Resampling.LANCZOS
    )
    alpha_small = B._subject_alpha(small, None)
    assert alpha_small is not None
    alpha_full = (
        np.asarray(
            Image.fromarray((alpha_small * 255.0).astype(np.uint8)).resize(
                (w0, h0), Image.Resampling.BILINEAR
            ),
            dtype=np.float32,
        )
        / 255.0
    )
    subj = img.convert("RGBA")
    subj.putalpha(Image.fromarray((alpha_full * 255.0).astype(np.uint8)))

    magenta = Image.new("RGBA", (w0, h0), (255, 0, 255, 255))
    magenta.alpha_composite(subj.copy())
    cut = magenta.convert("RGB")

    side = Image.new("RGB", (w0 * 2 + 12, h0), (40, 40, 40))
    side.paste(img.convert("RGB"), (0, 0))
    side.paste(cut, (w0 + 12, 0))
    side.save(OUT / f"m_{src.stem}_side.png")

    # Zoom 2x quanh hộp bao alpha để soi rìa.
    ys, xs = np.nonzero(alpha_full > 0.05)
    pad = 20
    x0, x1 = max(0, int(xs.min()) - pad), min(w0, int(xs.max()) + pad)
    y0, y1 = max(0, int(ys.min()) - pad), min(h0, int(ys.max()) + pad)
    print(f"alpha bbox: x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}] in {w0}x{h0}")
    zoom = side.crop((x0, y0, x1, y1))
    zoom = zoom.resize((zoom.width * 2, zoom.height * 2), Image.Resampling.NEAREST)
    zoom.save(OUT / f"m_{src.stem}_zoom.png")

    # Đo: bao nhiêu pixel alpha vừa phải (0.05..0.95) — dải feather, và độ dày.
    band = ((alpha_full > 0.05) & (alpha_full < 0.95)).sum()
    print(f"dải feather: {int(band)} px ({(alpha_full > 0.05).sum()} px vùng ly)")

    # Kiểm tra chạm biên ảnh gốc (dấu hiệu cắt cụt do subject chạm biên).
    print(f"chạm biên ảnh: left={xs.min() <= 1} right={xs.max() >= w0 - 2} "
          f"top={ys.min() <= 1} bottom={ys.max() >= h0 - 2}")


if __name__ == "__main__":
    main()
