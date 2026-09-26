"""Đo khoảng cách màu giữa từng cụm nền biên và các vùng quan trọng trong ảnh.

Mục đích: chọn bán kính toàn cục (global radius) SAO CHO:
  - mọi vùng nền thật nằm TRONG bán kính tới một cụm biên nào đó;
  - màu ly nước (đặc biệt là phần dung dịch sáng màu) nằm NGOÀI bán kính.

Chạy: python scripts/_diag_colors.py data/menu_images/mon_tra.jpg
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _proto_seg import border_clusters, min_cluster_dist  # noqa: E402


def main() -> None:
    src = Path(sys.argv[1])
    img = Image.open(src).convert("RGB")
    w0, h0 = img.size
    ratio = min(1.0, 640 / max(w0, h0))
    small = img.resize((max(2, int(w0 * ratio)), max(2, int(h0 * ratio))),
                       Image.Resampling.LANCZOS)
    arr = np.asarray(small, dtype=np.float32)
    h, w = arr.shape[:2]
    border = max(2, min(h, w) // 120)
    seed = np.zeros((h, w), dtype=bool)
    seed[:border, :] = True
    seed[-border:, :] = True
    seed[:, :border] = True
    seed[:, -border:] = True

    centers = border_clusters(arr, seed)
    print(f"=== {src.name} {w}x{h} ===")
    for i, c in enumerate(centers):
        share = float((min_cluster_dist(arr, centers[i:i + 1]) < 20).mean())
        print(f"  cụm#{i}: RGB={c.round(1)} ~{share * 100:.1f}% ảnh")

    gdist = min_cluster_dist(arr, centers)
    print("\nBán kính (percentile của gdist toàn ảnh):")
    for p in (50, 60, 70, 75, 80, 85, 90, 95, 99):
        print(f"  p{p} = {np.percentile(gdist, p):.1f}")

    # Chia ảnh thành lưới 6x6 để biết vùng nào "xa nền" (ứng viên chủ thể).
    print("\nBản đồ gdist theo lưới 6x6 (số = khoảng cách TB tới cụm biên gần nhất):")
    gh, gw = h // 6, w // 6
    for r in range(6):
        row = []
        for c in range(6):
            blk = gdist[r * gh:(r + 1) * gh, c * gw:(c + 1) * gw]
            row.append(f"{blk.mean():6.0f}")
        print("   " + " ".join(row))

    print("\nMàu đại diện của từng ô lưới (để nhận diện ô nào là ly):")
    for r in range(6):
        row = []
        for c in range(6):
            blk = arr[r * gh:(r + 1) * gh, c * gw:(c + 1) * gw].reshape(-1, 3).mean(axis=0)
            row.append(f"({blk[0]:3.0f},{blk[1]:3.0f},{blk[2]:3.0f})")
        print("   " + " ".join(row))

    for radius in (55, 65, 75, 85, 100):
        inside = gdist < radius
        print(f"\nradius={radius}: allowed={inside.mean():.3f} "
              f"subject(raw)={1 - inside.mean():.3f}")
        # Cụm liên thông của "không cho phép làm nền" để xem nó có gồm ly không.
        from scipy import ndimage
        lab, n = ndimage.label(~inside)
        if n:
            sizes = ndimage.sum_labels((~inside).astype(np.int32), lab,
                                       index=np.arange(1, n + 1))
            order = np.argsort(sizes)[::-1][:4]
            for k in order:
                m = lab == (k + 1)
                ys, xs = np.nonzero(m)
                print(f"    cụm {int(sizes[k]):6d}px bbox=({xs.min()},{ys.min()})-"
                      f"({xs.max()},{ys.max()})")


if __name__ == "__main__":
    main()
