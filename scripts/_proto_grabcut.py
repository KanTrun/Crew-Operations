"""So sánh GrabCut (OpenCV) với phương pháp thống kê màu (v4/v5) trên bộ ca GT.

GrabCut là thuật toán chuẩn cho "tách vật thể khi biết hộp bao" (min-cut trên
đồ thị màu). Đánh giá định lượng trước khi quyết định đưa vào production.

Chạy: python scripts/_proto_grabcut.py
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
from _sweep_seg import segment as segment_v5  # noqa: E402

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)


def grabcut_rect(img: np.ndarray, bbox, iters: int = 5) -> np.ndarray:
    """GrabCut khởi tạo bằng hộp bao (GC_INIT_WITH_RECT)."""
    h, w = img.shape[:2]
    x1, y1, x2, y2 = bbox
    rx, ry = int(x1 * w), int(y1 * h)
    rw, rh = max(3, int((x2 - x1) * w)), max(3, int((y2 - y1) * h))
    rx = min(rx, w - rw - 1) if rx + rw >= w else rx
    ry = min(ry, h - rh - 1) if ry + rh >= h else ry
    mask = np.zeros((h, w), dtype=np.uint8)
    bgd = np.zeros((1, 65), dtype=np.float64)
    fgd = np.zeros((1, 65), dtype=np.float64)
    cv2.grabCut(img, mask, (rx, ry, rw, rh), bgd, fgd, iters, cv2.GC_INIT_WITH_RECT)
    return (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)


def grabcut_masked(img: np.ndarray, bbox, core_shrink: float = 0.16, iters: int = 5) -> np.ndarray:
    """GrabCut khởi tạo bằng MASK: lõi bbox = chắc chắn FG, viền ảnh = chắc chắn BG.

    Khởi tạo giàu thông tin hơn rect-only, đặc biệt khi nền nhiều màu.
    """
    h, w = img.shape[:2]
    x1, y1, x2, y2 = bbox
    m = np.full((h, w), cv2.GC_PR_BGD, dtype=np.uint8)
    border = max(2, min(h, w) // 120)
    m[:border, :] = cv2.GC_BGD
    m[-border:, :] = cv2.GC_BGD
    m[:, :border] = cv2.GC_BGD
    m[:, -border:] = cv2.GC_BGD
    cw, ch = x2 - x1, y2 - y1
    cy0, cy1 = int((y1 + ch * core_shrink) * h), int((y1 + ch * (1 - core_shrink)) * h)
    cx0, cx1 = int((x1 + cw * core_shrink) * w), int((x1 + cw * (1 - core_shrink)) * w)
    m[cy0:cy1, cx0:cx1] = cv2.GC_FGD
    # Vùng ngoài bbox (nới 8%) = chắc chắn nền.
    ry0, ry1 = max(0, int((y1 - 0.08) * h)), min(h, int((y2 + 0.08) * h))
    rx0, rx1 = max(0, int((x1 - 0.08) * w)), min(w, int((x2 + 0.08) * w))
    outside = np.ones((h, w), dtype=bool)
    outside[ry0:ry1, rx0:rx1] = False
    m[outside] = cv2.GC_BGD
    bgd = np.zeros((1, 65), dtype=np.float64)
    fgd = np.zeros((1, 65), dtype=np.float64)
    cv2.grabCut(img, m, None, bgd, fgd, iters, cv2.GC_INIT_WITH_MASK)
    return (m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)


def clean(mask: np.ndarray) -> np.ndarray:
    mask = ndimage.binary_closing(mask, structure=np.ones((3, 3)))
    mask = ndimage.binary_fill_holes(mask)
    mask = ndimage.binary_opening(mask, structure=np.ones((3, 3)))
    # Giữ cụm lớn nhất (nếu GrabCut tạo đảo rác).
    labels, n = ndimage.label(mask)
    if n > 1:
        sizes = ndimage.sum_labels(mask.astype(np.int32), labels, index=np.arange(1, n + 1))
        mask = labels == (int(np.argmax(sizes)) + 1)
    return mask


def main() -> None:
    cases = []
    for name, arr, bbox, gt in make_cases():
        cases.append((name, np.clip(arr, 0, 255).astype(np.uint8), bbox, gt))

    methods = {
        "v5 màu": lambda img, bbox: clean(
            segment_v5(
                img.astype(np.float32), bbox,
                core_shrink=0.16, reach_pad=0.18, decide_margin=10.0,
                abs_cap=78.0, stick_dilate=22,
            )
            if segment_v5(
                img.astype(np.float32), bbox,
                core_shrink=0.16, reach_pad=0.18, decide_margin=10.0,
                abs_cap=78.0, stick_dilate=22,
            ) is not None else np.zeros(img.shape[:2], bool)
        ),
        "GrabCut rect": lambda img, bbox: clean(grabcut_rect(img, bbox)),
        "GrabCut mask": lambda img, bbox: clean(grabcut_masked(img, bbox)),
    }

    print(f"{'ca':22s} " + " ".join(f"{m:>14s}" for m in methods))
    summary: dict[str, list] = {m: [] for m in methods}
    timings: dict[str, list] = {m: [] for m in methods}
    for name, img, bbox, gt in cases:
        row = []
        for mname, fn in methods.items():
            t0 = time.perf_counter()
            mask = fn(img, bbox)
            dt = time.perf_counter() - t0
            timings[mname].append(dt)
            u = float((mask | gt).sum())
            iou = float((mask & gt).sum()) / u if u else 0.0
            kept = float((mask & gt).sum()) / float(gt.sum())
            extra = float((mask & ~gt).sum()) / float(gt.sum())
            summary[mname].append((iou, kept, extra, mask.mean()))
            row.append(f"{iou:.2f}/{kept * 100:.0f}%/{extra * 100:.0f}%")
        print(f"{name:22s} " + " ".join(f"{c:>14s}" for c in row))

    print("\n(iou / giữ-ly% / thừa-nền%)")
    print(f"\n{'phương pháp':16s} {'IoU TB':>7s} {'IoU min':>8s} {'ly min':>7s} "
          f"{'nền max':>8s} {'thời gian TB':>13s}")
    for mname, vals in summary.items():
        ious = [v[0] for v in vals]
        kepts = [v[1] for v in vals]
        extras = [v[2] for v in vals]
        print(f"{mname:16s} {np.mean(ious):7.3f} {min(ious):8.3f} {min(kepts) * 100:6.1f}% "
              f"{max(extras) * 100:7.1f}% {np.mean(timings[mname]) * 1000:10.0f} ms")

    # Lưu ảnh so sánh cho ca tệ nhất của mỗi phương pháp.
    for mname, fn in methods.items():
        vals = summary[mname]
        worst = int(np.argmin([v[0] for v in vals]))
        name, img, bbox, gt = cases[worst]
        mask = fn(img, bbox)
        vis = img.copy()
        vis[mask & gt] = (0.5 * vis[mask & gt] + 0.5 * np.array([0, 220, 0])).astype(np.uint8)
        vis[mask & ~gt] = (0.25 * vis[mask & ~gt] + 0.75 * np.array([255, 0, 0])).astype(np.uint8)
        vis[~mask & gt] = (0.3 * vis[~mask & gt] + 0.7 * np.array([0, 120, 255])).astype(np.uint8)
        Image.fromarray(vis).save(OUT / f"gc_{mname.replace(' ', '_')}_{name.replace(' ', '_')}.png")
        print(f"  ca tệ nhất {mname}: {name} (IoU {vals[worst][0]:.3f})")


if __name__ == "__main__":
    main()
