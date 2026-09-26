"""Tinh chỉnh tham số v5: thêm TRẦN KHOẢNG CÁCH TUYỆT ĐỐI cho FG + reach rộng hơn.

Vấn đề của v4 phát hiện qua bộ ca ground truth:
* "nền bokeh": vùng reach quanh ly có màu nền tình cờ gần FG model → mask loang ra
  thành quầng (thừa 162% nền). Cần TRẦN TUYỆT ĐỐI, không chỉ so sánh tương đối.
* "garnish ngoài bbox": lá vươn ra ngoài reach 0.12 → mất 13% ly. Cần reach rộng
  hơn, nhưng bù lại phải siết trần tuyệt đối.

Script này sweep tham số và in bảng IoU để chọn bộ tốt nhất (tất định, offline).

Chạy: python scripts/_sweep_seg.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _proto_seg3 import _clusters_from, _dist_to  # noqa: E402
from _proto_seg4 import make_cases  # noqa: E402

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)


def segment(
    arr: np.ndarray,
    bbox: tuple[float, float, float, float],
    *,
    core_shrink: float,
    reach_pad: float,
    decide_margin: float,
    abs_cap: float,
    stick_dilate: int,
    iterations: int = 3,
    abs_cap_ring: float | None = None,
) -> np.ndarray | None:
    """Trả mask bool. ``abs_cap`` áp cho pixel TRONG reach; ``abs_cap_ring`` áp cho
    pixel ngoài bbox nhưng trong reach (vùng garnish) — có thể siết chặt hơn."""
    h, w = arr.shape[:2]
    border = max(2, min(h, w) // 120)
    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[:border, :] = True
    border_mask[-border:, :] = True
    border_mask[:, :border] = True
    border_mask[:, -border:] = True

    x1, y1, x2, y2 = bbox
    inner = np.zeros((h, w), dtype=bool)
    inner[
        max(0, int(y1 * h)) : min(h, int(y2 * h)),
        max(0, int(x1 * w)) : min(w, int(x2 * w)),
    ] = True
    reach = np.zeros((h, w), dtype=bool)
    reach[
        max(0, int((y1 - reach_pad) * h)) : min(h, int((y2 + reach_pad) * h)),
        max(0, int((x1 - reach_pad) * w)) : min(w, int((x2 + reach_pad) * w)),
    ] = True
    cw, ch = x2 - x1, y2 - y1
    core = np.zeros((h, w), dtype=bool)
    core[
        max(0, int((y1 + ch * core_shrink) * h)) : min(h, int((y1 + ch * (1 - core_shrink)) * h)),
        max(0, int((x1 + cw * core_shrink) * w)) : min(w, int((x1 + cw * (1 - core_shrink)) * w)),
    ] = True
    if core.sum() < 16:
        return None

    bg_zone = border_mask | ~reach
    fg_centers = _clusters_from(arr[core].reshape(-1, 3))
    bg_centers = _clusters_from(arr[bg_zone].reshape(-1, 3))
    if fg_centers.shape[0] == 0 or bg_centers.shape[0] == 0:
        return None

    for it in range(iterations):
        d_fg = _dist_to(arr, fg_centers)
        d_bg = _dist_to(arr, bg_centers)
        cap = np.full((h, w), abs_cap, dtype=np.float32)
        if abs_cap_ring is not None:
            cap = np.where(inner, abs_cap, abs_cap_ring).astype(np.float32)
        fg_label = core | (reach & (d_fg < cap) & (d_fg + decide_margin < d_bg))
        if it < iterations - 1:
            bg_label = bg_zone | (~fg_label & (d_bg + decide_margin < d_fg))
            fg_centers = _clusters_from(arr[fg_label], min_share=0.004)
            bg_centers = _clusters_from(arr[bg_label], min_share=0.004)
            if fg_centers.shape[0] == 0 or bg_centers.shape[0] == 0:
                return None

    d_fg = _dist_to(arr, fg_centers)
    d_bg = _dist_to(arr, bg_centers)
    cap = np.full((h, w), abs_cap, dtype=np.float32)
    if abs_cap_ring is not None:
        cap = np.where(inner, abs_cap, abs_cap_ring).astype(np.float32)
    fg_label = core | (reach & (d_fg < cap) & (d_fg + decide_margin < d_bg))
    fg_label = ndimage.binary_closing(fg_label, structure=np.ones((3, 3)))

    labels, n = ndimage.label(fg_label)
    if n == 0:
        return None
    core_labels = [lab for lab in np.unique(labels[core]).tolist() if lab > 0]
    if not core_labels:
        return None
    primary = max(core_labels, key=lambda lab: int(((labels == lab) & core).sum()))
    mask = labels == primary
    if stick_dilate:
        near = ndimage.binary_dilation(mask, iterations=stick_dilate)
        for lab in range(1, n + 1):
            if lab == primary:
                continue
            comp = labels == lab
            if int(comp.sum()) < 14 or not bool((comp & near).any()):
                continue
            if float(d_bg[comp].mean()) < 40.0:
                continue
            mask |= comp
    return ndimage.binary_fill_holes(mask)


def run_case(arr: np.ndarray, bbox, gt: np.ndarray, **kw) -> tuple[float, float, float]:
    mask = segment(arr, bbox, **kw)
    if mask is None:
        return 0.0, 0.0, 0.0
    u = float((mask | gt).sum())
    iou = float((mask & gt).sum()) / u if u else 0.0
    kept = float((mask & gt).sum()) / float(gt.sum())
    extra = float((mask & ~gt).sum()) / float(gt.sum())
    return iou, kept, extra


def main() -> None:
    cases = []
    for name, arr, bbox, gt in make_cases():
        cases.append((name, np.clip(arr, 0, 255).astype(np.float32), bbox, gt))

    grid = []
    for reach_pad in (0.12, 0.18, 0.25):
        for abs_cap in (48.0, 62.0, 78.0):
            for decide_margin in (10.0, 18.0):
                grid.append((reach_pad, abs_cap, decide_margin))

    print(f"{'reach':>6s} {'cap':>5s} {'margin':>7s} | {'IoU TB':>7s} {'ly min':>7s} {'nền max':>8s} | per-case IoU")
    best = None
    for reach_pad, abs_cap, decide_margin in grid:
        kw = dict(
            core_shrink=0.16,
            reach_pad=reach_pad,
            decide_margin=decide_margin,
            abs_cap=abs_cap,
            stick_dilate=22,
        )
        ious, kepts, extras = [], [], []
        for _name, arr, bbox, gt in cases:
            iou, kept, extra = run_case(arr, bbox, gt, **kw)
            ious.append(iou)
            kepts.append(kept)
            extras.append(extra)
        avg = sum(ious) / len(ious)
        line = (f"{reach_pad:6.2f} {abs_cap:5.0f} {decide_margin:7.0f} | {avg:7.3f} "
                f"{min(kepts) * 100:6.1f}% {max(extras) * 100:7.1f}% | "
                + " ".join(f"{v:.2f}" for v in ious))
        print(line)
        # Hàm mục tiêu: KHÔNG được mất ly (min kept ≥ 95%) rồi mới tối đa IoU.
        score = (min(kepts), avg, -max(extras))
        if best is None or score > best[0]:
            best = (score, kw, avg, min(kepts), max(extras), ious)

    assert best is not None
    _s, kw, avg, mn, mx, ious = best
    print(f"\nTỐT NHẤT: {kw}\n  IoU TB={avg:.3f} giữ ly min={mn * 100:.1f}% thừa nền max={mx * 100:.1f}%")
    print("  per-case:", {c[0]: round(v, 3) for c, v in zip(cases, ious, strict=True)})


if __name__ == "__main__":
    main()
