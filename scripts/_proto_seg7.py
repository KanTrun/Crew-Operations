"""v7 — GrabCut rect-init với rect NỚI + tinh chỉnh 2 giai đoạn.

Phát hiện từ v6: khởi tạo mask (near_pad là PR_FGD) làm GrabCut "hồi phục" cả
vùng bokeh quanh ly (IoU 0.55). Khởi tạo rect-only thì bokeh hoàn hảo (0.99)
nhưng cắt mất garnish vươn ra ngoài rect (0.84).

v7 đi hướng khác: rect NỚI (bao cả garnish) ở giai đoạn 1, rồi giai đoạn 2 dùng
mask của giai đoạn 1 làm hạt giống FG/BG để cắt bỏ phần "hồi phục quá đà" ở giai
đoạn 1 — giữ lại chỉ phần thực sự liên thông chặt với lõi FG.

Chạy: python scripts/_proto_seg7.py
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


def _rect_from(bbox, w, h, pad: float) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    rx, ry = int((x1 - pad) * w), int((y1 - pad) * h)
    rw = int((x2 - x1 + 2 * pad) * w)
    rh = int((y2 - y1 + 2 * pad) * h)
    rx = max(0, min(rx, w - 3))
    ry = max(0, min(ry, h - 3))
    rw = max(3, min(rw, w - rx))
    rh = max(3, min(rh, h - ry))
    return rx, ry, rw, rh


def grabcut_raw(img: np.ndarray, rect, iters: int = 5) -> np.ndarray:
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    cv2.grabCut(img, mask, rect, np.zeros((1, 65), np.float64),
                np.zeros((1, 65), np.float64), iters, cv2.GC_INIT_WITH_RECT)
    return mask


def refine(img: np.ndarray, mask: np.ndarray, core: np.ndarray,
           border: int, iters: int = 3) -> np.ndarray:
    """Giai đoạn 2: dùng mask giai đoạn 1 làm hạt giống, buộc neo nền ở viền/xa."""
    m = mask.copy()
    # Vùng FG giai đoạn 1 → hạt giống FG; các nhãn khác → BG có thể.
    m = np.where(m == cv2.GC_FGD, cv2.GC_FGD, cv2.GC_PR_BGD).astype(np.uint8)
    m[core] = cv2.GC_FGD
    m[:border, :] = cv2.GC_BGD
    m[-border:, :] = cv2.GC_BGD
    m[:, :border] = cv2.GC_BGD
    m[:, -border:] = cv2.GC_BGD
    if int((m == cv2.GC_FGD).sum()) < 16:
        return mask
    cv2.grabCut(img, m, None, np.zeros((1, 65), np.float64),
                np.zeros((1, 65), np.float64), iters, cv2.GC_INIT_WITH_MASK)
    return m


def clean(mask: np.ndarray, min_ratio: float = 0.03, max_ratio: float = 0.92) -> np.ndarray | None:
    b = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    b = ndimage.binary_closing(b, structure=np.ones((3, 3)))
    b = ndimage.binary_fill_holes(b)
    labels, n = ndimage.label(b)
    if n == 0:
        return None
    if n > 1:
        sizes = ndimage.sum_labels(b.astype(np.int32), labels, index=np.arange(1, n + 1))
        b = labels == (int(np.argmax(sizes)) + 1)
    b = ndimage.binary_opening(b, structure=np.ones((3, 3)))
    ratio = float(b.mean())
    if not (min_ratio <= ratio <= max_ratio):
        return None
    return b


def metrics(mask: np.ndarray, gt: np.ndarray) -> tuple[float, float, float]:
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

    print(f"{'pad1':>5s} {'refine':>7s} | {'IoU TB':>7s} {'ly min':>7s} {'nền max':>8s} "
          f"{'ms/ảnh':>7s} | per-case IoU")
    best = None
    for pad1 in (0.06, 0.10, 0.16):
        for do_refine in (False, True):
            vals = []
            t0 = time.perf_counter()
            for _name, img, bbox, gt in cases:
                h, w = img.shape[:2]
                rect = _rect_from(bbox, w, h, pad1)
                raw = grabcut_raw(img, rect)
                if do_refine:
                    x1, y1, x2, y2 = bbox
                    cw, ch = x2 - x1, y2 - y1
                    core = np.zeros((h, w), dtype=bool)
                    core[
                        int((y1 + ch * 0.14) * h) : int((y1 + ch * 0.86) * h),
                        int((x1 + cw * 0.14) * w) : int((x1 + cw * 0.86) * w),
                    ] = True
                    border = max(2, min(h, w) // 120)
                    raw = refine(img, raw, core, border)
                m = clean(raw)
                vals.append(metrics(m, gt) if m is not None else (0.0, 0.0, 1.0))
            dt = (time.perf_counter() - t0) / len(cases)
            ious = [v[0] for v in vals]
            kepts = [v[1] for v in vals]
            extras = [v[2] for v in vals]
            print(f"{pad1:5.2f} {str(do_refine):>7s} | {np.mean(ious):7.3f} {min(kepts) * 100:6.0f}% "
                  f"{max(extras) * 100:7.1f}% {dt * 1000:7.0f} | "
                  + " ".join(f"{v[0]:.2f}" for v in vals))
            score = (min(kepts), np.mean(ious), -max(extras))
            if best is None or score > best[0]:
                best = (score, (pad1, do_refine), vals, dt)

    assert best is not None
    _s, (pad1, do_refine), vals, dt = best
    print(f"\nTỐT NHẤT: pad1={pad1} refine={do_refine} ({dt * 1000:.0f}ms/ảnh)")
    for c, v in zip(cases, vals, strict=True):
        print(f"  {c[0]:22s} IoU={v[0]:.3f} giữ ly={v[1] * 100:.0f}% thừa nền={v[2] * 100:.0f}%")

    worst = int(np.argmin([v[0] for v in vals]))
    name, img, bbox, gt = cases[worst]
    h, w = img.shape[:2]
    raw = grabcut_raw(img, _rect_from(bbox, w, h, pad1))
    if do_refine:
        x1, y1, x2, y2 = bbox
        cw, ch = x2 - x1, y2 - y1
        core = np.zeros((h, w), dtype=bool)
        core[
            int((y1 + ch * 0.14) * h) : int((y1 + ch * 0.86) * h),
            int((x1 + cw * 0.14) * w) : int((x1 + cw * 0.86) * w),
        ] = True
        raw = refine(img, raw, core, max(2, min(h, w) // 120))
    m = clean(raw)
    assert m is not None
    vis = img.copy()
    vis[m & gt] = (0.5 * vis[m & gt] + 0.5 * np.array([0, 220, 0])).astype(np.uint8)
    vis[m & ~gt] = (0.25 * vis[m & ~gt] + 0.75 * np.array([255, 0, 0])).astype(np.uint8)
    vis[~m & gt] = (0.3 * vis[~m & gt] + 0.7 * np.array([0, 120, 255])).astype(np.uint8)
    Image.fromarray(vis).save(OUT / f"v7_worst_{name.replace(' ', '_')}.png")


if __name__ == "__main__":
    main()
