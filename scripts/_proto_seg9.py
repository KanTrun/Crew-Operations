"""v9 — chốt thuật toán: GrabCut (rect) + "annex" có kiểm soát.

Trạng thái hiện tại: GrabCut rect-init (pad 0.06) đạt IoU 0.944 với THỪA NỀN = 0%
(hết quầng răng cưa — đúng lỗi người dùng phản ánh), nhưng mất 13% ly ở ca
"garnish vươn ra ngoài bbox" vì GrabCut không thấy pixel đó trong rect.

v9 bù đúng phần đó: sau GrabCut, mở rộng mask vào vành đai hữu hạn nếu pixel có
BẰNG CHỨNG MÀU MẠNH (rất gần màu FG đã học từ chính mask, và rất xa màu nền biên)
— và luôn giữ điều kiện liên thông với mask. Không mở rộng tự do.

Chạy: python scripts/_proto_seg9.py
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
from _proto_seg3 import _clusters_from, _dist_to  # noqa: E402
from _proto_seg4 import make_cases  # noqa: E402

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)

RECT_PAD = 0.06
ANNEX_RING_PX = 30
ANNEX_FG_MAX = 34.0
ANNEX_BG_MIN = 55.0


def rect_from_bbox(bbox, w: int, h: int, pad: float = RECT_PAD) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    rx, ry = int((x1 - pad) * w), int((y1 - pad) * h)
    rw, rh = int((x2 - x1 + 2 * pad) * w), int((y2 - y1 + 2 * pad) * h)
    rx, ry = max(0, min(rx, w - 3)), max(0, min(ry, h - 3))
    return rx, ry, max(3, min(rw, w - rx)), max(3, min(rh, h - ry))


def grabcut_rect(img: np.ndarray, rect, iters: int = 5) -> np.ndarray:
    m = np.zeros(img.shape[:2], dtype=np.uint8)
    cv2.grabCut(img, m, rect, np.zeros((1, 65), np.float64),
                np.zeros((1, 65), np.float64), iters, cv2.GC_INIT_WITH_RECT)
    return (m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)


def annex(img: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, dict]:
    """Mở rộng mask vào vành đai nếu có bằng chứng màu MẠNH."""
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
        return mask, {"annex_px": 0}
    fg_centers = _clusters_from(arr[inner].reshape(-1, 3))
    bg_centers = _clusters_from(arr[bmask].reshape(-1, 3))
    if fg_centers.shape[0] == 0 or bg_centers.shape[0] == 0:
        return mask, {"annex_px": 0}
    d_fg = _dist_to(arr, fg_centers)
    d_bg = _dist_to(arr, bg_centers)

    ring = ndimage.binary_dilation(mask, iterations=ANNEX_RING_PX) & ~mask
    cand = ring & (d_fg < ANNEX_FG_MAX) & (d_bg > ANNEX_BG_MIN)
    if not bool(cand.any()):
        return mask, {"annex_px": 0}
    # Chỉ nhận phần liên thông với mask (tránh nhặt mẩu nền trùng màu ở xa).
    lab, n = ndimage.label(cand | mask)
    anchor_labels = np.unique(lab[mask])
    anchor_labels = anchor_labels[anchor_labels > 0]
    if anchor_labels.size == 0:
        return mask, {"annex_px": 0}
    grown = np.isin(lab, anchor_labels)
    added = int((grown & cand).sum())
    return grown, {"annex_px": added, "ring_px": int(ring.sum())}


def clean(mask: np.ndarray, min_ratio: float = 0.03, max_ratio: float = 0.92):
    b = ndimage.binary_closing(mask, structure=np.ones((3, 3)))
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

    print("── So sánh: GrabCut thuần vs GrabCut + annex ────────────────────")
    print(f"{'ca':22s} {'GrabCut':>18s} {'GrabCut+annex':>18s}")
    plain, with_annex = [], []
    times: list[float] = []
    for name, img, bbox, gt in cases:
        t0 = time.perf_counter()
        base = clean(grabcut_rect(img, rect_from_bbox(bbox, *img.shape[1::-1])))
        t1 = time.perf_counter()
        assert base is not None
        grown, info = annex(img, base)
        grown_clean = clean(grown)
        assert grown_clean is not None
        times.append(time.perf_counter() - t0)
        vp = metrics(base, gt)
        va = metrics(grown_clean, gt)
        plain.append(vp)
        with_annex.append(va)
        print(f"{name:22s} {vp[0]:.2f}/{vp[1] * 100:.0f}%/{vp[2] * 100:.0f}%      "
              f"{va[0]:.2f}/{va[1] * 100:.0f}%/{va[2] * 100:.0f}%   "
              f"annex+{info.get('annex_px', 0)}px  ({(t1 - t0) * 1000:.0f}ms grabcut)")

    print(f"\n{'biến thể':16s} {'IoU TB':>7s} {'ly min':>7s} {'nền max':>8s}")
    for label, vals in (("GrabCut", plain), ("GrabCut+annex", with_annex)):
        print(f"{label:16s} {np.mean([v[0] for v in vals]):7.3f} "
              f"{min(v[1] for v in vals) * 100:6.0f}% {max(v[2] for v in vals) * 100:7.1f}%")

    # ── Ảnh THẬT: kiểm tra không làm hại ca thực ──────────────────────────
    print("\n── Ảnh THẬT (bbox vision giả lập) ──────────────────────────────")
    for src in ("data/menu_images/mon_tra.jpg", "data/menu_images/mon_den.png"):
        p = Path(src)
        img_full = Image.open(p).convert("RGB")
        w0, h0 = img_full.size
        ratio = min(1.0, 640 / max(w0, h0))
        small = img_full.resize((max(2, int(w0 * ratio)), max(2, int(h0 * ratio))),
                                Image.Resampling.LANCZOS)
        img = np.asarray(small)
        for bn, bbox in {"rộng": (0.20, 0.10, 0.80, 0.88),
                         "chật": (0.30, 0.18, 0.70, 0.82)}.items():
            t0 = time.perf_counter()
            base = clean(grabcut_rect(img, rect_from_bbox(bbox, small.width, small.height)))
            dt = time.perf_counter() - t0
            if base is None:
                print(f"  {p.name} bbox {bn}: FAIL-CLOSED")
                continue
            grown, info = annex(img, base)
            gc = clean(grown)
            assert gc is not None
            # Tỷ lệ pixel trong mask mà màu gần màu NỀN biên (chỉ số "bẩn"/quầng).
            arr = np.asarray(small, dtype=np.float32)
            h, w = arr.shape[:2]
            border = max(2, min(h, w) // 120)
            bmask = np.zeros((h, w), dtype=bool)
            bmask[:border, :] = True
            bmask[-border:, :] = True
            bmask[:, :border] = True
            bmask[:, -border:] = True
            bg_c = _clusters_from(arr[bmask].reshape(-1, 3))
            dirty_base = float((_dist_to(arr, bg_c)[base] < 45.0).mean())
            dirty_grown = float((_dist_to(arr, bg_c)[gc] < 45.0).mean())
            print(f"  {p.name} bbox {bn:5s} ratio={gc.mean():.3f} "
                  f"annex+{info.get('annex_px', 0)}px dirty: {dirty_base:.3f}→{dirty_grown:.3f} "
                  f"({dt * 1000:.0f}ms)")
            blue = Image.new("RGBA", small.size, (30, 40, 120, 255))
            rgba = small.convert("RGBA")
            rgba.putalpha(Image.fromarray((gc * 255).astype(np.uint8)))
            blue.alpha_composite(rgba)
            over = np.asarray(small).copy()
            over[gc] = (0.5 * over[gc] + 0.5 * np.array([0, 220, 0])).astype(np.uint8)
            sheet = Image.new("RGB", (small.width * 3 + 20, small.height), (25, 25, 25))
            sheet.paste(small, (0, 0))
            sheet.paste(Image.fromarray(over), (small.width + 10, 0))
            sheet.paste(blue.convert("RGB"), (small.width * 2 + 20, 0))
            sheet.save(OUT / f"v9_{p.stem}_{bn}.png")

    print(f"\n  thời gian TB mỗi mask (ảnh tổng hợp): {np.mean(times) * 1000:.0f} ms")


if __name__ == "__main__":
    main()
