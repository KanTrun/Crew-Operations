"""Script tạm: dump mask tách chủ thể của bg_redesign để soi lỗi trên ảnh thật."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "agents" / "src"))

from ca_agents.bg_redesign import (  # noqa: E402
    _MASK_MAX_DIM,
    _edge_color,
    _background_is_usable,
    _subject_alpha,
)

SRC = Path(r"d:\duthi\Crew-Operations\data\menu_images\mon_tra.jpg")
OUT = Path(r"d:\duthi\Crew-Operations\data\menu_images\_debug")
OUT.mkdir(parents=True, exist_ok=True)

img = Image.open(SRC)
img.load()
print("kích thước gốc:", img.size, img.mode)
w0, h0 = img.size

ratio = min(1.0, _MASK_MAX_DIM / max(w0, h0))
small = img.convert("RGB").resize(
    (max(2, int(w0 * ratio)), max(2, int(h0 * ratio))), Image.Resampling.LANCZOS
)
print("kích thước mask:", small.size)

# Lưu ảnh nhỏ để đối chiếu
small.save(OUT / "orig_small.png")

alpha = _subject_alpha(small, None)
if alpha is None:
    print(">>> _subject_alpha trả về None (segment_failed)")
else:
    print(">>> alpha: min=%.3f max=%.3f mean=%.3f" % (alpha.min(), alpha.max(), alpha.mean()))
    # Mask nhị phân: chủ thể = trắng
    mask = (alpha * 255).astype(np.uint8)
    Image.fromarray(mask).save(OUT / "mask.png")
    # Chồng mask lên ảnh gốc để thấy chỗ sai (viền đỏ)
    base = np.asarray(small).copy()
    edge = (alpha > 0.05) & (alpha < 0.95)
    base[..., 0] = np.where(edge, 255, base[..., 0])
    base[..., 1] = np.where(edge, 0, base[..., 1])
    base[..., 2] = np.where(edge, 0, base[..., 2])
    Image.fromarray(base).save(OUT / "mask_overlay.png")
    # Ảnh chủ thể đã tách (nền trong suốt) để soi viền
    rgba = small.convert("RGBA")
    rgba.putalpha(Image.fromarray(mask))
    bg = Image.new("RGBA", rgba.size, (0, 200, 0, 255))
    bg.alpha_composite(rgba)
    bg.convert("RGB").save(OUT / "cutout_on_green.png")

print("màu viền ảnh gốc:", _edge_color(img))
print("đã ghi:", OUT)
