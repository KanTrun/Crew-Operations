"""Sweep ngưỡng "annex" để hồi phục garnish mà không làm quầng nền quay lại.

v9 dùng `ANNEX_FG_MAX=34` quá chặt: màu lá garnish (90,170,45) cách màu ly
(150,190,60) ~65 đơn vị RGB → không đủ điều kiện. Sweep để chọn ngưỡng tốt nhất
trên bộ ca ground truth, ràng buộc "thừa nền" phải giữ ở 0%.

Chạy: python scripts/_sweep_annex.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _proto_seg3 import _clusters_from, _dist_to  # noqa: E402
from _proto_seg4 import make_cases  # noqa: E402
from _proto_seg9 import clean, grabcut_rect, metrics, rect_from_bbox  # noqa: E402


def annex_tuned(
    img: np.ndarray, mask: np.ndarray, fg_max: float, bg_min: float, ring_px: int
) -> np.ndarray:
    arr = np.asarray(img, dtype=np.float32)
    h, w = arr.shape[:2]
    border = max(2, min(h, w) // 120)
    bmask = np.zeros((h, w), dtype=bool)
    bmask[:border, :] = True
    bmask[-border:, :] = True
    bmask[:, :border] = True
    bmask[:, -border:] = True
    inner = ndimage.binary_erosion(mask, iterations=3)
    if int(inner.sum()) < 16:
        return mask
    fg_centers = _clusters_from(arr[inner].reshape(-1, 3))
    bg_centers = _clusters_from(arr[bmask].reshape(-1, 3))
    if fg_centers.shape[0] == 0 or bg_centers.shape[0] == 0:
        return mask
    d_fg = _dist_to(arr, fg_centers)
    d_bg = _dist_to(arr, bg_centers)
    ring = ndimage.binary_dilation(mask, iterations=ring_px) & ~mask
    cand = ring & (d_fg < fg_max) & (d_bg > bg_min) & (d_fg < d_bg)
    if not bool(cand.any()):
        return mask
    lab, _n = ndimage.label(cand | mask)
    anchors = np.unique(lab[mask])
    anchors = anchors[anchors > 0]
    if anchors.size == 0:
        return mask
    grown = np.isin(lab, anchors)
    return grown if int((grown & cand).sum()) > 0 else mask


def main() -> None:
    cases = []
    for name, arr, bbox, gt in make_cases():
        cases.append((name, np.clip(arr, 0, 255).astype(np.uint8), bbox, gt))

    print(f"{'fg_max':>6s} {'bg_min':>6s} {'ring':>5s} | {'IoU TB':>7s} {'ly min':>7s} "
          f"{'nền max':>8s} | per-case IoU")
    best = None
    for fg_max in (34.0, 50.0, 70.0, 90.0):
        for bg_min in (40.0, 55.0, 75.0):
            for ring_px in (20, 34):
                vals = []
                for _name, img, bbox, gt in cases:
                    base = clean(grabcut_rect(img, rect_from_bbox(bbox, *img.shape[1::-1])))
                    if base is None:
                        vals.append((0.0, 0.0, 1.0))
                        continue
                    last = clean(annex_tuned(img, base, fg_max, bg_min, ring_px))
                    vals.append(metrics(last, gt) if last is not None else (0.0, 0.0, 1.0))
                ious = [v[0] for v in vals]
                kepts = [v[1] for v in vals]
                extras = [v[2] for v in vals]
                print(f"{fg_max:6.0f} {bg_min:6.0f} {ring_px:5d} | {np.mean(ious):7.3f} "
                      f"{min(kepts) * 100:6.0f}% {max(extras) * 100:7.1f}% | "
                      + " ".join(f"{v[0]:.2f}" for v in vals))
                score = (min(kepts), np.mean(ious), -max(extras))
                if best is None or score > best[0]:
                    best = (score, (fg_max, bg_min, ring_px), vals)

    assert best is not None
    _s, params, vals = best
    print(f"\nTỐT NHẤT: fg_max={params[0]} bg_min={params[1]} ring={params[2]}")
    print(f"  IoU TB={np.mean([v[0] for v in vals]):.3f} "
          f"giữ ly min={min(v[1] for v in vals) * 100:.0f}% "
          f"thừa nền max={max(v[2] for v in vals) * 100:.1f}%")

    # Kiểm tra trên ảnh THẬT: annex có gây hại không?
    print("\n  Kiểm tra ảnh thật (không ground truth — chỉ xem tỷ lệ mask thay đổi):")
    from PIL import Image

    for src in ("data/menu_images/mon_tra.jpg", "data/menu_images/mon_den.png"):
        p = Path(src)
        im = Image.open(p).convert("RGB")
        w0, h0 = im.size
        r = min(1.0, 640 / max(w0, h0))
        small = im.resize((max(2, int(w0 * r)), max(2, int(h0 * r))), Image.Resampling.LANCZOS)
        img = np.asarray(small)
        base = clean(grabcut_rect(img, rect_from_bbox((0.22, 0.10, 0.80, 0.88),
                                                      small.width, small.height)))
        assert base is not None
        grew = clean(annex_tuned(img, base, params[0], params[1], params[2]))
        assert grew is not None
        print(f"    {p.name}: ratio {base.mean():.3f} → {grew.mean():.3f} "
              f"({'+' if grew.sum() > base.sum() else ''}"
              f"{int(grew.sum() - base.sum())} px)")


if __name__ == "__main__":
    main()
