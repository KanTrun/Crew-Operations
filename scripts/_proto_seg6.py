"""v6 — GrabCut với khởi tạo MASK cho phép hồi phục pixel ngoài bbox.

v5 (thống kê màu) thua GrabCut ở ca "nền bokeh" (IoU 0.44 vs 1.00, thừa nền 127%).
GrabCut thua v5 ở ca "garnish ngoài bbox" (84% vs 100%) vì khởi tạo mask coi mọi
pixel ngoài bbox là nền CHẮC CHẮN.

v6 sửa đúng điểm đó: pixel ngoài bbox nhưng gần bbox → GC_PR_BGD (nền *có thể*),
không phải GC_BGD (nền chắc chắn) → GrabCut được phép hồi phục nếu mạnh FG.
Pixel ở viền ảnh và ở xa bbox vẫn là GC_BGD (neo nền chắc chắn).

Chạy: python scripts/_proto_seg6.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _proto_seg4 import make_cases  # noqa: E402

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)


def grabcut_v6(
    img: np.ndarray,
    bbox: tuple[float, float, float, float],
    *,
    core_shrink: float = 0.14,
    near_pad: float = 0.16,
    sure_bg_dist: float = 0.30,
    iters: int = 5,
) -> np.ndarray | None:
    """Mask FG. None nếu khởi tạo/hội tụ không tin cậy."""
    h, w = img.shape[:2]
    x1, y1, x2, y2 = bbox
    cw, ch = x2 - x1, y2 - y1

    m = np.full((h, w), cv2.GC_PR_BGD, dtype=np.uint8)
    # Viền ảnh: nền CHẮC CHẮN.
    border = max(2, min(h, w) // 120)
    m[:border, :] = cv2.GC_BGD
    m[-border:, :] = cv2.GC_BGD
    m[:, :border] = cv2.GC_BGD
    m[:, -border:] = cv2.GC_BGD
    # Xa bbox: nền chắc chắn (không cho hồi phục ở đó).
    fy0, fy1 = int((y1 - sure_bg_dist) * h), int((y2 + sure_bg_dist) * h)
    fx0, fx1 = int((x1 - sure_bg_dist) * w), int((x2 + sure_bg_dist) * w)
    far = np.ones((h, w), dtype=bool)
    far[max(0, fy0) : min(h, fy1), max(0, fx0) : min(w, fx1)] = False
    far[border:h - border, border:w - border] &= True
    m[far] = cv2.GC_BGD
    # Lõi bbox: FG chắc chắn.
    cy0, cy1 = int((y1 + ch * core_shrink) * h), int((y1 + ch * (1 - core_shrink)) * h)
    cx0, cx1 = int((x1 + cw * core_shrink) * w), int((x1 + cw * (1 - core_shrink)) * w)
    if cy1 - cy0 < 4 or cx1 - cx0 < 4:
        return None
    m[cy0:cy1, cx0:cx1] = cv2.GC_FGD
    # Vòng đệm gần bbox: PR_FGD (có thể là FG, ví dụ garnish vươn ra).
    ny0, ny1 = int((y1 - near_pad) * h), int((y2 + near_pad) * h)
    nx0, nx1 = int((x1 - near_pad) * w), int((x2 + near_pad) * w)
    near = np.zeros((h, w), dtype=bool)
    near[max(0, ny0) : min(h, ny1), max(0, nx0) : min(w, nx1)] = True
    near[cy0:cy1, cx0:cx1] = False
    m[near & (m == cv2.GC_PR_BGD)] = cv2.GC_PR_FGD

    fg_count = int((m == cv2.GC_FGD).sum())
    bg_count = int((m == cv2.GC_BGD).sum())
    if fg_count < 16 or bg_count < 16:
        return None

    try:
        cv2.grabCut(img, m, None, np.zeros((1, 65), np.float64),
                    np.zeros((1, 65), np.float64), iters, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        return None
    mask = (m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)
    return mask


def clean(mask: np.ndarray, min_ratio: float = 0.03, max_ratio: float = 0.92) -> np.ndarray | None:
    mask = ndimage.binary_closing(mask, structure=np.ones((3, 3)))
    mask = ndimage.binary_fill_holes(mask)
    labels, n = ndimage.label(mask)
    if n == 0:
        return None
    sizes = ndimage.sum_labels(mask.astype(np.int32), labels, index=np.arange(1, n + 1))
    mask = labels == (int(np.argmax(sizes)) + 1)
    mask = ndimage.binary_opening(mask, structure=np.ones((3, 3)))
    ratio = float(mask.mean())
    if not (min_ratio <= ratio <= max_ratio):
        return None
    return mask


def iou_kept_extra(mask: np.ndarray, gt: np.ndarray) -> tuple[float, float, float]:
    u = float((mask | gt).sum())
    return (
        float((mask & gt).sum()) / u if u else 0.0,
        float((mask & gt).sum()) / float(gt.sum()),
        float((mask & ~gt).sum()) / float(gt.sum()),
    )


def main() -> None:
    cases = []
    for name, arr, bbox, gt in make_cases():
        cases.append((name, np.clip(arr, 0, 255).astype(np.uint8), bbox, gt))

    print(f"{'ca':22s} {'core':>5s} {'near':>5s} {'far':>5s} | {'IoU':>5s} {'ly':>5s} {'nền':>5s}")
    best = None
    for core_shrink in (0.10, 0.14, 0.18):
        for near_pad in (0.12, 0.20):
            for sure_bg_dist in (0.24, 0.34):
                vals = []
                t0 = time.perf_counter()
                for _name, img, bbox, gt in cases:
                    mask = grabcut_v6(
                        img, bbox, core_shrink=core_shrink, near_pad=near_pad,
                        sure_bg_dist=sure_bg_dist,
                    )
                    if mask is None:
                        vals.append((0.0, 0.0, 1.0))
                        continue
                    mask = clean(mask)
                    if mask is None:
                        vals.append((0.0, 0.0, 1.0))
                        continue
                    vals.append(iou_kept_extra(mask, gt))
                dt = (time.perf_counter() - t0) / len(cases)
                ious = [v[0] for v in vals]
                kepts = [v[1] for v in vals]
                extras = [v[2] for v in vals]
                print(f"{' ':22s} {core_shrink:5.2f} {near_pad:5.2f} {sure_bg_dist:5.2f} | "
                      f"{np.mean(ious):5.3f} {min(kepts) * 100:4.0f}% {max(extras) * 100:4.0f}%"
                      f"   ({dt * 1000:.0f}ms/ảnh)  {[round(v[0], 2) for v in vals]}")
                score = (min(kepts), np.mean(ious), -max(extras))
                if best is None or score > best[0]:
                    best = (score, (core_shrink, near_pad, sure_bg_dist), vals, dt)

    assert best is not None
    _s, params, vals, dt = best
    print(f"\nTỐT NHẤT: core_shrink={params[0]} near_pad={params[1]} sure_bg={params[2]} "
          f"({dt * 1000:.0f}ms/ảnh)")
    for c, v in zip(cases, vals, strict=True):
        print(f"  {c[0]:22s} IoU={v[0]:.3f} giữ ly={v[1] * 100:.0f}% thừa nền={v[2] * 100:.0f}%")

    # Ảnh minh hoạ ca tệ nhất.
    worst = int(np.argmin([v[0] for v in vals]))
    name, img, bbox, gt = cases[worst]
    mask = grabcut_v6(img, bbox, core_shrink=params[0], near_pad=params[1],
                      sure_bg_dist=params[2])
    assert mask is not None
    mask = clean(mask)
    assert mask is not None
    vis = img.copy()
    vis[mask & gt] = (0.5 * vis[mask & gt] + 0.5 * np.array([0, 220, 0])).astype(np.uint8)
    vis[mask & ~gt] = (0.25 * vis[mask & ~gt] + 0.75 * np.array([255, 0, 0])).astype(np.uint8)
    vis[~mask & gt] = (0.3 * vis[~mask & gt] + 0.7 * np.array([0, 120, 255])).astype(np.uint8)
    Image.fromarray(vis).save(OUT / f"v6_worst_{name.replace(' ', '_')}.png")


if __name__ == "__main__":
    main()
