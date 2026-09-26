"""Prototype thuật toán tách chủ thể v2 — đo lường trước khi đưa vào production.

Ba thay đổi so với bản hiện tại:
1. Mô hình nền = NHIỀU cụm màu biên (quantize + merge, tất định) thay vì 1 màu
   trung bình → ảnh có biên nhiều vùng (bàn tối + cửa sổ sáng) vẫn tách được.
2. flood-fill hai ngưỡng (hysteresis): ngưỡng mạnh để "neo", ngưỡng yếu để lan
   qua vùng chuyển sắc — có trần khoảng cách màu nên không rò vào ly.
3. bbox của vision chỉ dùng để CHỌN cụm chính, không cắt cụt mask; các cụm rời
   gần cụm chính được giữ lại nếu màu của chúng KHÔNG giống màu biên (tức là
   phần của ly, không phải mảng nền cũ).

Chạy: python scripts/_proto_seg.py [ảnh...]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)

# ── Tham số ───────────────────────────────────────────────────────────────
_QUANT = 16           # mức lượng tử mỗi kênh khi gom cụm màu biên
_CLUSTER_MIN_SHARE = 0.02   # cụm màu biên phải chiếm ≥2% số pixel biên
_CLUSTER_MERGE = 42.0       # gộp hai cụm gần nhau (khoảng cách RGB euclide)
_CLUSTER_MAX = 5
_RADIUS_STRONG = 62.0  # pixel trong bán kính này coi là nền chắc chắn
_RADIUS_WEAK = 118.0   # trần tuyệt đối: xa hơn thì không bao giờ là nền
_TOL_PER_CHANNEL = 24.0  # tương đồng CỤC BỘ khi lan
_NEAR_PRIMARY_PX = 26    # bán kính gom cụm rời quanh cụm chính
_LEAK_MIN_DIST = 70.0    # cụm rời phải KHÁC màu biên ≥ ngần này mới giữ
_MASK_ERODE_PX = 1
_FEATHER_FLOOR = 0.18


def border_clusters(arr: np.ndarray, seed: np.ndarray) -> np.ndarray:
    """Gom màu pixel biên thành vài cụm đại diện (tất định, không random)."""
    cols = arr[seed].reshape(-1, 3)
    if cols.shape[0] > 20000:
        cols = cols[:: max(1, cols.shape[0] // 20000)]
    q = np.clip((cols / _QUANT).astype(np.int32), 0, 255 // _QUANT)
    keys = q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2]
    uniq, counts = np.unique(keys, return_counts=True)
    centers = []
    min_count = max(1, int(_CLUSTER_MIN_SHARE * cols.shape[0]))
    for key, cnt in sorted(zip(uniq.tolist(), counts.tolist()), key=lambda kv: -kv[1]):
        if cnt < min_count and centers:
            break
        qk = np.array([key // 4096, (key // 64) % 64, key % 64], dtype=np.float32)
        center = (qk + 0.5) * _QUANT
        # Tinh chỉnh về trung bình thật của các pixel trong bin này.
        sel = keys == key
        if sel.any():
            center = cols[sel].mean(axis=0)
        centers.append(center)
        if len(centers) >= _CLUSTER_MAX:
            break
    # Gộp cụm gần nhau (bokeh của cùng một vùng nền thường thành nhiều bin).
    merged: list[np.ndarray] = []
    for c in centers:
        for i, m in enumerate(merged):
            if float(np.linalg.norm(c - m)) < _CLUSTER_MERGE:
                merged[i] = (m + c) / 2.0
                break
        else:
            merged.append(np.asarray(c, dtype=np.float32))
    return np.stack(merged) if merged else arr[seed].reshape(-1, 3)[:1]


def min_cluster_dist(arr: np.ndarray, centers: np.ndarray) -> np.ndarray:
    """Khoảng cách RGB euclide tới cụm màu biên GẦN NHẤT (mỗi pixel)."""
    best = np.full(arr.shape[:2], np.inf, dtype=np.float32)
    for c in centers:
        d = np.sqrt(((arr - c) ** 2).sum(axis=2))
        best = np.minimum(best, d)
    return best


def grow_hysteresis(
    arr: np.ndarray, seed: np.ndarray, strong: np.ndarray, weak: np.ndarray, tol: float
) -> np.ndarray:
    """Flood-fill có neo: chỉ lan vào pixel ``weak`` và cần pixel kề đã là nền.

    ``strong`` chỉ dùng để chọn seed ban đầu (neo chắc chắn); sau đó lan qua
    ``weak`` với tương đồng màu cục bộ — cho phép vượt vùng chuyển sắc mềm mà
    không cần nới ngưỡng toàn cục (nguồn gốc của rò rỉ).
    """
    h, w = arr.shape[:2]
    bg = seed & strong
    threshold = tol * 3.0
    frontier = np.argwhere(bg)
    offsets = ((1, 0), (-1, 0), (0, 1), (0, -1))
    while frontier.shape[0]:
        cy = np.concatenate([frontier[:, 0] + o[0] for o in offsets])
        cx = np.concatenate([frontier[:, 1] + o[1] for o in offsets])
        inb = (cy >= 0) & (cy < h) & (cx >= 0) & (cx < w)
        cy, cx = cy[inb], cx[inb]
        fresh = ~bg[cy, cx]
        cy, cx = cy[fresh], cx[fresh]
        if cy.size == 0:
            break
        okw = weak[cy, cx]
        cy, cx = cy[okw], cx[okw]
        if cy.size == 0:
            break
        dists = np.full(cy.shape, np.inf)
        for dy, dx in offsets:
            py, px = cy + dy, cx + dx
            ok = (py >= 0) & (py < h) & (px >= 0) & (px < w) & bg[
                py.clip(0, h - 1), px.clip(0, w - 1)
            ]
            d = np.abs(arr[cy, cx] - arr[py.clip(0, h - 1), px.clip(0, w - 1)]).sum(axis=1)
            dists = np.where(ok, np.minimum(dists, d), dists)
        acc = dists < threshold
        ny, nx = cy[acc], cx[acc]
        if ny.size == 0:
            break
        add = np.zeros((h, w), dtype=bool)
        add[ny, nx] = True
        add &= ~bg
        if not bool(add.any()):
            break
        bg |= add
        fy, fx = np.nonzero(add)
        frontier = np.stack([fy, fx], axis=1)
    return bg


def subject_alpha_v2(
    img: Image.Image, bbox: tuple[float, float, float, float] | None
) -> tuple[np.ndarray | None, dict]:
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    h, w = arr.shape[:2]
    border = max(2, min(h, w) // 120)
    seed = np.zeros((h, w), dtype=bool)
    seed[:border, :] = True
    seed[-border:, :] = True
    seed[:, :border] = True
    seed[:, -border:] = True

    centers = border_clusters(arr, seed)
    gdist = min_cluster_dist(arr, centers)
    strong = gdist < _RADIUS_STRONG
    weak = gdist < _RADIUS_WEAK
    # Vùng biên: chắc chắn là nền (bất kể màu gì) — neo khởi đầu.
    anchor = np.zeros((h, w), dtype=bool)
    anchor[:border + 2, :] = True
    anchor[-(border + 2):, :] = True
    anchor[:, :border + 2] = True
    anchor[:, -(border + 2):] = True

    bg = grow_hysteresis(arr, anchor, strong, weak, _TOL_PER_CHANNEL)
    subj = ~bg

    info: dict = {
        "clusters": centers.round(1).tolist(),
        "strong_ratio": float(strong.mean()),
        "weak_ratio": float(weak.mean()),
        "bg_ratio": float(bg.mean()),
    }

    if bbox is not None:
        x1, y1, x2, y2 = bbox
        margin = 0.10
        box = np.zeros((h, w), dtype=bool)
        box[
            max(0, int((y1 - margin) * h)) : min(h, int((y2 + margin) * h)),
            max(0, int((x1 - margin) * w)) : min(w, int((x2 + margin) * w)),
        ] = True
    else:
        box = np.ones((h, w), dtype=bool)

    labels, n = ndimage.label(subj)
    if n == 0:
        return None, info
    sizes = ndimage.sum_labels(subj.astype(np.int32), labels, index=np.arange(1, n + 1))
    # Cụm CHÍNH: ưu tiên cụm nằm trong bbox (prior mềm), nếu không có thì lớn nhất.
    inside = np.zeros(n, dtype=np.float32)
    for i in range(1, n + 1):
        ys, xs = np.nonzero(labels == i)
        inside[i - 1] = float(box[ys, xs].mean())
    cand = np.where(inside > 0.35)[0]
    if cand.size:
        primary = int(cand[np.argmax(sizes[cand])]) + 1
    else:
        primary = int(np.argmax(sizes)) + 1
    info["n_components"] = int(n)
    info["primary_share"] = float(sizes[primary - 1] / sizes.sum())

    # Gom các cụm RỜI gần cụm chính, chỉ khi màu chúng KHÁC màu biên (là phần ly,
    # không phải mảng nền cũ quanh ly).
    primary_mask = labels == primary
    near = ndimage.binary_dilation(primary_mask, iterations=_NEAR_PRIMARY_PX)
    keep = primary_mask.copy()
    kept_extra: list[tuple[int, float]] = []
    for i in range(1, n + 1):
        if i == primary:
            continue
        comp = labels == i
        if not bool((comp & near).any()):
            continue
        if int(sizes[i - 1]) < 12:
            continue
        d = float(gdist[comp].mean())
        if d < _LEAK_MIN_DIST:
            continue  # màu giống nền cũ → mảng nền, bỏ
        keep |= comp
        kept_extra.append((int(sizes[i - 1]), round(d, 1)))
    info["kept_extra"] = kept_extra
    info["dropped_share"] = float((sizes.sum() - keep.sum()) / max(1, sizes.sum()))

    keep = ndimage.binary_fill_holes(keep)
    ratio = float(keep.mean())
    info["subject_ratio"] = ratio
    if ratio < 0.03 or ratio > 0.92:
        return None, info

    keep = ndimage.binary_closing(keep, structure=np.ones((3, 3)))
    keep = ndimage.binary_opening(keep, structure=np.ones((3, 3)))
    if _MASK_ERODE_PX:
        er = ndimage.binary_erosion(keep, iterations=_MASK_ERODE_PX)
        if bool(er.any()):
            keep = er
    sigma = max(1.0, min(h, w) / 350.0)
    alpha = ndimage.gaussian_filter(keep.astype(np.float32), sigma=sigma)
    alpha = np.clip(alpha, 0.0, 1.0)
    alpha = np.where(alpha < _FEATHER_FLOOR, 0.0, alpha)
    # Đo "bẩn": pixel trong mask mà màu vẫn gần màu biên → khả năng là nền cũ.
    solid = alpha > 0.5
    info["dirty_ratio"] = float((gdist[solid] < 45.0).mean()) if solid.any() else 0.0
    info["mask_bbox_fill"] = 0.0
    ys, xs = np.nonzero(solid)
    if ys.size:
        info["mask_bbox_fill"] = float(
            solid.sum() / ((ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1))
        )
    return alpha, info


def main() -> None:
    srcs = sys.argv[1:] or [
        "data/menu_images/mon_tra.jpg",
        "data/menu_images/mon_den.png",
    ]
    for src in srcs:
        p = Path(src)
        img = Image.open(p).convert("RGB")
        w0, h0 = img.size
        ratio = min(1.0, 640 / max(w0, h0))
        small = img.resize((max(2, int(w0 * ratio)), max(2, int(h0 * ratio))),
                           Image.Resampling.LANCZOS)
        alpha, info = subject_alpha_v2(small, None)
        print(f"=== {p.name} ({w0}x{h0}) ===")
        print("  clusters:", info["clusters"])
        print(f"  strong={info['strong_ratio']:.3f} weak={info['weak_ratio']:.3f} "
              f"bg={info['bg_ratio']:.3f}")
        if alpha is None:
            print("  !! FAIL-CLOSED (ratio ngoài khoảng tin cậy):", info.get("subject_ratio"))
            continue
        print(f"  n_components={info['n_components']} primary_share={info['primary_share']:.3f} "
              f"kept_extra={info['kept_extra']}")
        print(f"  subject_ratio={info['subject_ratio']:.3f} "
              f"dirty_ratio={info['dirty_ratio']:.3f} "
              f"bbox_fill={info['mask_bbox_fill']:.2f} dropped={info['dropped_share']:.3f}")

        rgba = small.convert("RGBA")
        rgba.putalpha(Image.fromarray((alpha * 255).astype(np.uint8)))
        over = np.asarray(small).copy()
        solid = alpha > 0.5
        over[solid] = (0.45 * over[solid] + 0.55 * np.array([0, 220, 0])).astype(np.uint8)
        over[~solid] = (0.6 * over[~solid] + 0.4 * np.array([255, 0, 0])).astype(np.uint8)
        blue = Image.new("RGBA", small.size, (30, 40, 120, 255))
        blue.alpha_composite(rgba)
        side = Image.new("RGB", (small.width * 3 + 20, small.height), (25, 25, 25))
        side.paste(small, (0, 0))
        side.paste(Image.fromarray(over), (small.width + 10, 0))
        side.paste(blue.convert("RGB"), (small.width * 2 + 20, 0))
        side.save(OUT / f"v2_{p.stem}.png")


if __name__ == "__main__":
    main()
