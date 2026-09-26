"""Soi các cụm liên thông của mask: cụm lớn nhất bị giữ, các cụm khác bị VỨT.

Nếu cụm thứ 2..n là phần của chính ly nước (đáy ly, quai, lá trang trí, phần bị
vật cản cắt ngang) thì quy tắc "chỉ lấy cụm lớn nhất" chính là lỗi "cắt mất ly".

Chạy: python scripts/_diag_components.py [ảnh]
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
    arr = np.asarray(small, dtype=np.float32)
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
    bg = B._grow_background(arr, seed, B._BG_TOLERANCE_PER_CHANNEL, allowed=allowed)
    subj = ~bg
    labels, n = B.ndimage.label(subj)
    sizes = B.ndimage.sum_labels(subj.astype(np.int32), labels, index=np.arange(1, n + 1))
    order = np.argsort(sizes)[::-1]

    base = np.asarray(small).copy()
    total = int(sizes.sum())
    print(f"{src.name}: {w}x{h}; tổng pixel chủ thể thô = {total} "
          f"({total / (w * h):.3f} ảnh); số cụm = {n}")
    palette = [(255, 0, 0), (0, 255, 0), (0, 128, 255), (255, 255, 0), (255, 0, 255),
               (0, 255, 255), (255, 128, 0)]

    vis = base.copy()
    rows = []
    for rank, idx in enumerate(order[:8]):
        size = int(sizes[idx])
        comp = labels == (idx + 1)
        ys, xs = np.nonzero(comp)
        bb = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
        # Cụm này có "dính" vào cụm lớn nhất trong bán kính 25px không?
        dil = B.ndimage.binary_dilation(comp, iterations=25)
        touches = bool((dil & (labels == (order[0] + 1))).any())
        fill = size / ((bb[2] - bb[0] + 1) * (bb[3] - bb[1] + 1) + 1e-9)
        rows.append((rank, size, size / total, bb, touches, fill))
        if rank < len(palette):
            vis[comp] = (0.35 * base[comp] + 0.65 * np.array(palette[rank])).astype(np.uint8)

    for rank, size, share, bb, touches, fill in rows:
        tag = "GIỮ" if rank == 0 else ("bỏ" if not touches else "bỏ (gần cụm chính!)")
        print(f"  #{rank + 1} size={size:6d} ({share * 100:5.2f}%) bbox={bb} "
              f"lấp kín bbox={fill:.2f} dính cụm#1={touches} → {tag}")

    side = Image.new("RGB", (w * 2 + 10, h), (30, 30, 30))
    side.paste(small, (0, 0))
    side.paste(Image.fromarray(vis), (w + 10, 0))
    side.save(OUT / f"c_{src.stem}_components.png")

    kept = np.zeros((h, w), dtype=bool)
    kept[labels == (order[0] + 1)] = True
    mask_img = Image.fromarray((kept * 255).astype(np.uint8))
    magenta = Image.new("RGBA", (w, h), (255, 0, 255, 255))
    magenta.putalpha(mask_img)
    comp_only = Image.new("RGB", (w, h), (20, 20, 20))
    comp_only.paste(magenta.convert("RGB"), (0, 0), mask_img)
    comp_only.save(OUT / f"c_{src.stem}_keptonly.png")


if __name__ == "__main__":
    main()
