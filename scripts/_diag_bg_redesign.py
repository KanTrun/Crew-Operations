"""Chẩn đoán nhanh bước tách chủ thể của bg_redesign trên ảnh thật.

Chạy: python scripts/_diag_bg_redesign.py data/menu_images/mon_tra.jpg
Xuất ra data/menu_images/_debug/ các artefact để xem bằng mắt.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "agents" / "src"))

from ca_agents import bg_redesign  # noqa: E402

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)
IMG = Path(sys.argv[1] if len(sys.argv) > 1 else "data/menu_images/mon_tra.jpg")


def main() -> None:
    raw = IMG.read_bytes()
    img = bg_redesign._decode_original(raw)
    assert img is not None
    w0, h0 = img.size
    print(f"original: {w0}x{h0}")

    ratio = min(1.0, bg_redesign._MASK_MAX_DIM / max(w0, h0))
    small = img.convert("RGB").resize(
        (max(2, int(w0 * ratio)), max(2, int(h0 * ratio))), Image.Resampling.LANCZOS
    )
    small.save(OUT / "d1_orig_small.png")

    # Không dùng bbox prior (offline, không gọi LLM).
    alpha = bg_redesign._subject_alpha(small, None)
    if alpha is None:
        print("!! _subject_alpha trả None (segment_failed)")
        arr = np.asarray(small.convert("RGB"), dtype=np.float32)
        h, w = arr.shape[:2]
        border = max(2, min(h, w) // 120)
        seed = np.zeros((h, w), dtype=bool)
        seed[:border, :] = True
        seed[-border:, :] = True
        seed[:, :border] = True
        seed[:, -border:] = True
        bcolor = arr[seed].reshape(-1, 3).mean(axis=0)
        gdist = np.sqrt(((arr - bcolor) ** 2).sum(axis=2))
        print("  border color", bcolor, "gdist p50/p90/p99",
              np.percentile(gdist, [50, 90, 99]))
        allowed = gdist < bg_redesign._BG_GLOBAL_RADIUS
        print("  allowed ratio", allowed.mean())
        bgm = bg_redesign._grow_background(arr, seed, bg_redesign._BG_TOLERANCE_PER_CHANNEL,
                                           allowed=allowed)
        print("  bg ratio", bgm.mean(), "subject ratio", 1 - bgm.mean())
        labels, n = bg_redesign.ndimage.label(~bgm)
        sizes = bg_redesign.ndimage.sum_labels((~bgm).astype(np.int32), labels,
                                               index=np.arange(1, n + 1))
        order = np.argsort(sizes)[::-1][:5]
        print("  top components:", [(int(i + 1), int(sizes[i])) for i in order])
        return

    print(f"alpha: shape={alpha.shape} >0.5 ratio={float((alpha > 0.5).mean()):.3f}")

    # Overlay: xanh = giữ (chủ thể), đỏ = bỏ (nền).
    a = np.asarray(small.convert("RGB")).copy()
    over = a.copy()
    keep = alpha > 0.5
    over[keep] = (0.45 * a[keep] + 0.55 * np.array([0, 200, 0])).astype(np.uint8)
    over[~keep] = (0.55 * a[~keep] + 0.45 * np.array([255, 0, 0])).astype(np.uint8)
    Image.fromarray(over).save(OUT / "d2_overlay.png")

    # Cutout trên nền xanh lá để thấy rõ pixel nào còn lại.
    rgba = small.convert("RGBA")
    rgba.putalpha(Image.fromarray((alpha * 255).astype(np.uint8)))
    green = Image.new("RGBA", small.size, (0, 200, 0, 255))
    green.alpha_composite(rgba)
    green.convert("RGB").save(OUT / "d3_cutout_green.png")

    cropped, ca = bg_redesign._tight_crop(rgba.copy(), alpha)
    print(f"tight crop: {cropped.size} (from {small.size})")
    green2 = Image.new("RGBA", cropped.size, (0, 200, 0, 255))
    green2.alpha_composite(cropped.copy())
    green2.convert("RGB").save(OUT / "d4_crop_green.png")

    # Kiểm tra 4 cạnh của mask: chủ thể có chạm biên crop không (dấu hiệu bị cắt cụt).
    ys, xs = np.nonzero(alpha > 0.05)
    print(f"bbox theo alpha: x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}] "
          f"của {alpha.shape[1]}x{alpha.shape[0]}")
    print(f"chạm biên: left={xs.min() <= 2} right={xs.max() >= alpha.shape[1] - 3} "
          f"top={ys.min() <= 2} bottom={ys.max() >= alpha.shape[0] - 3}")

    # Số mảng rời rạc trong mask sau khi >0.5 (dấu hiệu rò nền vào giữa ly).
    lab, n = bg_redesign.ndimage.label(alpha > 0.5)
    sizes = np.sort(bg_redesign.ndimage.sum_labels((alpha > 0.5).astype(np.int32), lab,
                                                   index=np.arange(1, n + 1)))[::-1]
    print(f"số mảng mask: {n}; 6 lớn nhất: {[int(s) for s in sizes[:6]]}")


if __name__ == "__main__":
    main()
