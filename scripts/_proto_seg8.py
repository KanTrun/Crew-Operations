"""v8 — thuật toán gần cuối: GrabCut + hạt giống thích ứng + xử lý bbox=None.

Ba việc cần chốt bằng số liệu trước khi port vào production:

1. **Hồi phục garnish vươn ra ngoài rect.** v7 đạt IoU 0.944 nhưng mất 13% ly ở
   ca garnish. Thử: sau GrabCut rect nhỏ, chạy thêm vòng refine TRONG VÀNH ĐAI
   hữu hạn quanh mask (ring), để min-cut quyết định thay vì màu thuần.
2. **bbox=None** (vision LLM lỗi — test `test_llm_outage_still_works` yêu cầu vẫn
   ra ảnh). Cần rect dự phòng: dùng phương pháp màu thô để ĐỀ XUẤT rect, rồi
   GrabCut tinh chỉnh. So sánh với rect cố định giữa ảnh.
3. **Thời gian**: GrabCut ~350ms/mask ở 640px — chấp nhận được.

Chạy: python scripts/_proto_seg8.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _proto_seg3 import _clusters_from, _dist_to  # noqa: E402
from _proto_seg4 import make_cases  # noqa: E402

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)

RECT_PAD = 0.06
CORE_SHRINK = 0.14
RING_PX = 22
ANNEX_MARGIN = 20.0


def rect_from_bbox(bbox, w: int, h: int, pad: float = RECT_PAD) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    rx, ry = int((x1 - pad) * w), int((y1 - pad) * h)
    rw, rh = int((x2 - x1 + 2 * pad) * w), int((y2 - y1 + 2 * pad) * h)
    rx, ry = max(0, min(rx, w - 3)), max(0, min(ry, h - 3))
    return rx, ry, max(3, min(rw, w - rx)), max(3, min(rh, h - ry))


def _raw_grabcut(img: np.ndarray, rect) -> np.ndarray:
    m = np.zeros(img.shape[:2], dtype=np.uint8)
    cv2.grabCut(img, m, rect, np.zeros((1, 65), np.float64),
                np.zeros((1, 65), np.float64), 5, cv2.GC_INIT_WITH_RECT)
    return (m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)


def _refine_ring(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """GrabCut giai đoạn 2: cho phép mở rộng CHỈ trong vành đai RING_PX quanh mask."""
    h, w = img.shape[:2]
    border = max(2, min(h, w) // 120)
    ring = ndimage.binary_dilation(mask, iterations=RING_PX) & ~ndimage.binary_erosion(
        mask, iterations=RING_PX
    )
    m = np.full((h, w), cv2.GC_PR_BGD, dtype=np.uint8)
    m[mask] = cv2.GC_FGD
    m[ring] = cv2.GC_PR_FGD
    m[:border, :] = cv2.GC_BGD
    m[-border:, :] = cv2.GC_BGD
    m[:, :border] = cv2.GC_BGD
    m[:, -border:] = cv2.GC_BGD
    if int((m == cv2.GC_FGD).sum()) < 16:
        return mask
    cv2.grabCut(img, m, None, np.zeros((1, 65), np.float64),
                np.zeros((1, 65), np.float64), 3, cv2.GC_INIT_WITH_MASK)
    out = (m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)
    # Chỉ NHẬN phần mở rộng nằm trong vành đai (không cho nhảy ra xa).
    return mask | (out & ring)


def _clean(mask: np.ndarray, min_ratio: float = 0.03, max_ratio: float = 0.92):
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


def _heuristic_rect(img: np.ndarray) -> tuple[int, int, int, int]:
    """Đề xuất rect khi KHÔNG có bbox: dùng mô hình màu biên để tìm vùng lạ."""
    arr = np.asarray(img, dtype=np.float32)
    h, w = arr.shape[:2]
    border = max(2, min(h, w) // 120)
    bmask = np.zeros((h, w), dtype=bool)
    bmask[:border, :] = True
    bmask[-border:, :] = True
    bmask[:, :border] = True
    bmask[:, -border:] = True
    centers = _clusters_from(arr[bmask].reshape(-1, 3))
    gdist = _dist_to(arr, centers)
    far = gdist > 70.0
    # Bỏ nhiễu: đóng lỗ, lấy cụm lớn nhất, bbox cụm đó.
    far = ndimage.binary_closing(far, structure=np.ones((5, 5)))
    labels, n = ndimage.label(far)
    if n == 0:
        return (int(w * 0.15), int(h * 0.08), int(w * 0.7), int(h * 0.84))
    sizes = ndimage.sum_labels(far.astype(np.int32), labels, index=np.arange(1, n + 1))
    comp = labels == (int(np.argmax(sizes)) + 1)
    ys, xs = np.nonzero(comp)
    if ys.size < 16:
        return (int(w * 0.15), int(h * 0.08), int(w * 0.7), int(h * 0.84))
    pad = int(0.04 * max(w, h))
    x0, x1 = max(0, int(xs.min()) - pad), min(w, int(xs.max()) + pad)
    y0, y1 = max(0, int(ys.min()) - pad), min(h, int(ys.max()) + pad)
    return (x0, y0, max(3, x1 - x0), max(3, y1 - y0))


def _fixed_rect(w: int, h: int) -> tuple[int, int, int, int]:
    return (int(w * 0.15), int(h * 0.08), int(w * 0.7), int(h * 0.84))


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

    variants = {
        "rect nhỏ": lambda img, bbox: _raw_grabcut(img, rect_from_bbox(bbox, *img.shape[1::-1])),
        "rect nhỏ+ring": lambda img, bbox: _refine_ring(
            img, _raw_grabcut(img, rect_from_bbox(bbox, *img.shape[1::-1]))
        ),
        "rect vừa+ring": lambda img, bbox: _refine_ring(
            img, _raw_grabcut(img, rect_from_bbox(bbox, *img.shape[1::-1], pad=0.10))
        ),
    }
    print(f"{'ca':22s} " + " ".join(f"{v:>16s}" for v in variants))
    store: dict[str, list] = {k: [] for k in variants}
    times: dict[str, list] = {k: [] for k in variants}
    for name, img, bbox, gt in cases:
        row = []
        for vname, fn in variants.items():
            t0 = time.perf_counter()
            m = _clean(fn(img, bbox))
            times[vname].append(time.perf_counter() - t0)
            v = metrics(m, gt) if m is not None else (0.0, 0.0, 1.0)
            store[vname].append(v)
            row.append(f"{v[0]:.2f}/{v[1] * 100:.0f}%/{v[2] * 100:.0f}%")
        print(f"{name:22s} " + " ".join(f"{c:>16s}" for c in row))

    print("\n(iou / giữ-ly% / thừa-nền%)")
    print(f"\n{'biến thể':16s} {'IoU TB':>7s} {'ly min':>7s} {'nền max':>8s} {'ms':>6s}")
    for vname, vals in store.items():
        ious = [v[0] for v in vals]
        print(f"{vname:16s} {np.mean(ious):7.3f} {min(v[1] for v in vals) * 100:6.0f}% "
              f"{max(v[2] for v in vals) * 100:7.1f}% {np.mean(times[vname]) * 1000:6.0f}")

    # ── bbox=None: so sánh rect heuristic vs rect cố định ──────────────────
    print("\n── KHÔNG có bbox (vision LLM lỗi) ──────────────────────────────")
    print(f"{'ca':22s} {'heuristic':>18s} {'cố định':>18s}")
    h_store, f_store = [], []
    for name, img, _bbox, gt in cases:
        h, w = img.shape[:2]
        t0 = time.perf_counter()
        mh = _clean(_refine_ring(img, _raw_grabcut(img, _heuristic_rect(img))))
        dt_h = time.perf_counter() - t0
        t0 = time.perf_counter()
        mf = _clean(_refine_ring(img, _raw_grabcut(img, _fixed_rect(w, h))))
        dt_f = time.perf_counter() - t0
        vh = metrics(mh, gt) if mh is not None else (0.0, 0.0, 1.0)
        vf = metrics(mf, gt) if mf is not None else (0.0, 0.0, 1.0)
        h_store.append(vh)
        f_store.append(vf)
        print(f"{name:22s} {vh[0]:.2f}/{vh[1] * 100:.0f}%/{vh[2] * 100:.0f}% "
              f"({dt_h * 1000:.0f}ms) {vf[0]:.2f}/{vf[1] * 100:.0f}%/{vf[2] * 100:.0f}% "
              f"({dt_f * 1000:.0f}ms)")
    print(f"  TB: heuristic IoU={np.mean([v[0] for v in h_store]):.3f} "
          f"ly min={min(v[1] for v in h_store) * 100:.0f}% "
          f"nền max={max(v[2] for v in h_store) * 100:.0f}%")
    print(f"      cố định  IoU={np.mean([v[0] for v in f_store]):.3f} "
          f"ly min={min(v[1] for v in f_store) * 100:.0f}% "
          f"nền max={max(v[2] for v in f_store) * 100:.0f}%")


if __name__ == "__main__":
    main()
