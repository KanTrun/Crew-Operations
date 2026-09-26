"""Dump từng bước của pipeline bg_redesign (offline, nền giả) để soi artefact.

Chạy: python scripts/_diag_pipeline.py [ảnh] [tỷ lệ]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "agents" / "src"))

from ca_agents import bg_redesign as B  # noqa: E402
from ca_agents.image_gen import ASPECT_DIMS  # noqa: E402

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)

# Màu nền kiểm tra: xanh dương đậm (khác hoàn toàn nền sáng) để lộ pixel cũ còn sót.
TEST_BG = (30, 40, 120)


def on_bg(rgba: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    canvas = Image.new("RGBA", rgba.size, (*color, 255))
    canvas.alpha_composite(rgba.copy())
    return canvas.convert("RGB")


def diag_mask_internals(arr: np.ndarray, label: str) -> None:
    """Soi _subject_alpha từng bước: seed, allowed, grow, largest, fill/closing."""
    h, w = arr.shape[:2]
    border = max(2, min(h, w) // 120)
    seed = np.zeros((h, w), dtype=bool)
    seed[:border, :] = True
    seed[-border:, :] = True
    seed[:, :border] = True
    seed[:, -border:] = True
    bcolor = arr[seed].reshape(-1, 3).mean(axis=0)
    gdist = np.sqrt(((arr - bcolor) ** 2).sum(axis=2))
    allowed = gdist < B._BG_GLOBAL_RADIUS
    print(f"[{label}] border mean RGB = {bcolor.round(1)}")
    print(f"[{label}] gdist percentiles 50/75/90/95/99 = "
          f"{np.percentile(gdist, [50, 75, 90, 95, 99]).round(1)}")
    print(f"[{label}] allowed ratio = {allowed.mean():.3f}")

    bg = B._grow_background(arr, seed, B._BG_TOLERANCE_PER_CHANNEL, allowed=allowed)
    print(f"[{label}] bg ratio = {bg.mean():.3f}; subject(raw) = {(~bg).mean():.3f}")
    labels, n = B.ndimage.label(~bg)
    sizes = B.ndimage.sum_labels((~bg).astype(np.int32), labels, index=np.arange(1, n + 1))
    order = np.argsort(sizes)[::-1][:6]
    print(f"[{label}] cụm chủ thể (raw): {[(int(i + 1), int(sizes[i])) for i in order]}")

    # Cụm nào là "chủ thể thật" (theo thuật toán hiện tại: lớn nhất)?
    if n:
        largest = int(np.argmax(sizes)) + 1
        subj = labels == largest
        subj_f = B.ndimage.binary_fill_holes(subj)
        print(f"[{label}] sau fill_holes: ratio = {subj_f.mean():.3f}")
        # Xuất phần "được nạp thêm" bởi fill_holes để xem nó lấp cái gì.
        added = subj_f & ~subj
        vis = np.asarray(Image.fromarray(arr.astype(np.uint8))).copy()
        vis[added] = (255, 0, 255)
        Image.fromarray(vis).save(OUT / f"p_{label}_fillholes_added.png")
        print(f"[{label}] fill_holes thêm {int(added.sum())} px (tô magenta)")


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "data/menu_images/mon_tra.jpg")
    aspect = sys.argv[2] if len(sys.argv) > 2 else "4:5"
    width, height = ASPECT_DIMS[aspect]

    raw = src.read_bytes()
    img = B._decode_original(raw)
    assert img is not None
    w0, h0 = img.size
    print(f"original {w0}x{h0} → canvas {width}x{height}")

    ratio = min(1.0, B._MASK_MAX_DIM / max(w0, h0))
    small = img.convert("RGB").resize(
        (max(2, int(w0 * ratio)), max(2, int(h0 * ratio))), Image.Resampling.LANCZOS
    )
    small.save(OUT / "p1_small.png")
    arr = np.asarray(small, dtype=np.float32)

    diag_mask_internals(arr, "nobox")

    # bbox giả lập từ vision (sát ly) để xem prior có cắt cụt ly không.
    h, w = arr.shape[:2]
    for name, box in {
        "tight": (0.10, 0.05, 0.75, 0.98),
        "lệch": (0.15, 0.12, 0.70, 0.90),
    }.items():
        bbox = box
        a = B._subject_alpha(small, bbox)
        print(f"bbox={name} {box} → alpha {'None (fail-closed)' if a is None else f'ratio>0.5 = {(a > 0.5).mean():.3f}'}")
        if a is not None:
            rgba = small.convert("RGBA")
            rgba.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
            on_bg(rgba, TEST_BG).save(OUT / f"p2_cutout_{name}.png")

    # Alpha không bbox + vẽ lên nền xanh đậm.
    alpha = B._subject_alpha(small, None)
    assert alpha is not None
    rgba = small.convert("RGBA")
    rgba.putalpha(Image.fromarray((alpha * 255).astype(np.uint8)))
    on_bg(rgba, TEST_BG).save(OUT / "p3_cutout_nobox.png")

    # Chạy nốt pipeline composite với nền giả.
    def fake_bg(prompt: str, w: int, h: int, seed: int | None, timeout_s: float,
                old_bg_color: np.ndarray) -> tuple[Image.Image | None, str, str]:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        base = np.zeros((h, w, 3), dtype=np.float32)
        base[:, :, 0] = 28 + 40 * (1 - yy / h)
        base[:, :, 1] = 18 + 26 * (1 - yy / h)
        base[:, :, 2] = 14 + 18 * (1 - yy / h)
        im = Image.fromarray(base.astype(np.uint8))
        d = ImageDraw.Draw(im, "RGBA")
        rng = np.random.default_rng(7)
        for _ in range(26):
            cx, cy = rng.integers(0, w), rng.integers(0, h)
            r = int(rng.integers(10, 46))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 208, 130, 42))
        return im.filter(ImageFilter.GaussianBlur(radius=max(4, w // 90))), "", "fake"

    orig = B._generate_background
    B._generate_background = fake_bg  # type: ignore[assignment]
    try:
        res = B.generate_background_redesign(
            raw,
            "iced peach tea on wooden table, warm cafe, professional food photography",
            original_mime="image/jpeg",
            aspect_ratio=aspect,
            seed=None,
        )
    finally:
        B._generate_background = orig  # type: ignore[assignment]
    print("composite:", res.ok, res.error)
    if res.ok:
        (OUT / "p4_final.png").write_bytes(res.image_bytes)

    # Soi phần subject đem đi composite: dump RGBA cutout đúng như _composite nhận.
    bbox = None
    alpha_full = (
        np.asarray(
            Image.fromarray((alpha * 255.0).astype(np.uint8)).resize((w0, h0),
                                                                     Image.Resampling.BILINEAR),
            dtype=np.float32,
        )
        / 255.0
    )
    subject = img.convert("RGBA")
    subject.putalpha(Image.fromarray((alpha_full * 255.0).astype(np.uint8)))
    cropped, alpha_crop = B._tight_crop(subject, alpha_full)
    cropped = cropped.copy()
    cropped.putalpha(Image.fromarray((alpha_crop * 255.0).astype(np.uint8)))
    print(f"tight crop {cropped.size} / original {w0}x{h0}")
    on_bg(cropped, TEST_BG).save(OUT / "p5_subject_on_blue.png")
    print("bbox dùng cho cutout trên:", bbox)

    # Kiểm tra: cạnh trên/dưới của crop có cắt vào ly không?
    ys, xs = np.nonzero(np.asarray(cropped.getchannel("A")) > 128)
    print(f"subject bbox trong crop: y[{ys.min()},{ys.max()}] / {cropped.size[1]}")


if __name__ == "__main__":
    main()
