"""Chạy thử bước composite của bg_redesign với nền GIẢ (offline) để soi artefact.

Nền giả = gradient tối + vài đốm bokeh, cố ý tối để mọi mảng nền cũ còn sót
trong mask lộ ra thành vệt sáng.

Chạy: python scripts/_diag_composite.py data/menu_images/mon_tra.jpg [out.png]
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "agents" / "src"))

from ca_agents import bg_redesign  # noqa: E402
from ca_agents.image_gen import ASPECT_DIMS  # noqa: E402

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)


def fake_background(width: int, height: int) -> Image.Image:
    """Nền tối kiểu quán bar: gradient nâu đen + bokeh vàng."""
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    base = np.zeros((height, width, 3), dtype=np.float32)
    base[:, :, 0] = 28 + 40 * (1 - yy / height)
    base[:, :, 1] = 18 + 26 * (1 - yy / height)
    base[:, :, 2] = 14 + 18 * (1 - yy / height)
    img = Image.fromarray(base.astype(np.uint8))
    draw = ImageDraw.Draw(img, "RGBA")
    rng = np.random.default_rng(7)
    for _ in range(26):
        cx, cy = rng.integers(0, width), rng.integers(0, height)
        r = int(rng.integers(10, 46))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 208, 130, 42))
    return img.filter(ImageFilter.GaussianBlur(radius=max(4, width // 90)))


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "data/menu_images/mon_tra.jpg")
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT / "d5_composite.png"
    aspect = sys.argv[3] if len(sys.argv) > 3 else "4:5"
    width, height = ASPECT_DIMS[aspect]

    raw = src.read_bytes()
    img = bg_redesign._decode_original(raw)
    assert img is not None
    w0, h0 = img.size
    print(f"original: {w0}x{h0}  canvas: {width}x{height}  aspect={aspect}")

    # Thay sinh nền bằng nền giả (không cần mạng) — giữ nguyên mọi bước còn lại.
    def fake_generate(
        prompt: str,
        w: int,
        h: int,
        seed: int | None,
        timeout_s: float,
        old_bg_color: np.ndarray,
    ) -> tuple[Image.Image | None, str, str]:
        return fake_background(w, h), "", "fake"

    orig_gen = bg_redesign._generate_background
    bg_redesign._generate_background = fake_generate  # type: ignore[assignment]
    try:
        result = bg_redesign.generate_background_redesign(
            raw,
            "iced peach tea on a wooden table, warm cafe, professional food photography",
            original_mime="image/jpeg",
            aspect_ratio=aspect,
            seed=None,
        )
    finally:
        bg_redesign._generate_background = orig_gen  # type: ignore[assignment]

    print("ok:", result.ok, "error:", result.error)
    if result.ok:
        out_path.write_bytes(result.image_bytes)
        print("wrote", out_path)
        with Image.open(io.BytesIO(result.image_bytes)) as im:
            print("output size", im.size)


if __name__ == "__main__":
    main()
