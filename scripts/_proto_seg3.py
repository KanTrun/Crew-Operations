"""Prototype v3 — tách chủ thể bằng TRIMAP hai mô hình màu (FG core / BG ring).

Ý tưởng: flood-fill màu luôn rò ở chỗ ly TIẾP XÚC nền cùng tông (đáy ly trên mặt
bàn tối, vành ly sáng gặp tường sáng). Thay vì lan từ biên, v3 dùng hai mô hình
màu đối kháng:

* FG model: cụm màu lấy từ LÕI bbox (chắc chắn là ly).
* BG model: cụm màu lấy từ viền ảnh + vùng NGOÀI bbox (chắc chắn là nền).
* Vùng "unknown" (giữa hai vùng) được phân loại theo mô hình GẦN HƠN, cộng
  ràng buộc: pixel xa bbox quá ``_BBOX_REACH`` thì không thể là ly.

Nhờ FG model lấy từ chính thân ly, vành ly sáng không bị "trôi" sang nền như
flood-fill, còn đáy ly trên bàn tối vẫn được giữ vì màu đáy ly khớp FG model.

Chạy: python scripts/_proto_seg3.py [ảnh...]
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _proto_seg import border_clusters, min_cluster_dist  # noqa: E402

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)

_QUANT = 16
_CLUSTER_MIN_SHARE = 0.015
_CLUSTER_MERGE = 38.0
_CLUSTER_MAX = 6
_CORE_SHRINK = 0.18      # co bbox bao nhiêu % mỗi chiều để lấy lõi FG
_BBOX_REACH = 0.10       # nới bbox bao nhiêu % để cho phép pixel là ly (garnish)
_DECIDE_MARGIN = 12.0    # FG phải gần hơn BG ít nhất ngần này mới nhận
_MASK_ERODE_PX = 1
_FEATHER_FLOOR = 0.18


def _clusters_from(cols: np.ndarray, min_share: float = _CLUSTER_MIN_SHARE) -> np.ndarray:
    """Gom một tập màu thành vài cụm đại diện (lượng tử + gộp, tất định)."""
    if cols.shape[0] == 0:
        return np.zeros((0, 3), dtype=np.float32)
    if cols.shape[0] > 30000:
        cols = cols[:: max(1, cols.shape[0] // 30000)]
    q = np.clip((cols / _QUANT).astype(np.int32), 0, 255 // _QUANT)
    keys = q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2]
    uniq, counts = np.unique(keys, return_counts=True)
    min_count = max(1, int(min_share * cols.shape[0]))
    centers: list[np.ndarray] = []
    for key, cnt in sorted(zip(uniq.tolist(), counts.tolist()), key=lambda kv: -kv[1]):
        if cnt < min_count and centers:
            break
        sel = keys == key
        centers.append(cols[sel].mean(axis=0).astype(np.float32))
        if len(centers) >= _CLUSTER_MAX:
            break
    merged: list[np.ndarray] = []
    for c in centers:
        for i, m in enumerate(merged):
            if float(np.linalg.norm(c - m)) < _CLUSTER_MERGE:
                merged[i] = (m + c) / 2.0
                break
        else:
            merged.append(c)
    return np.stack(merged) if merged else cols[:1]


def _dist_to(arr: np.ndarray, centers: np.ndarray) -> np.ndarray:
    if centers.shape[0] == 0:
        return np.full(arr.shape[:2], 255.0, dtype=np.float32)
    best = np.full(arr.shape[:2], np.inf, dtype=np.float32)
    for c in centers:
        best = np.minimum(best, np.sqrt(((arr - c) ** 2).sum(axis=2)))
    return best


def subject_alpha_v3(
    img: Image.Image,
    bbox: tuple[float, float, float, float] | None,
    debug: dict | None = None,
) -> np.ndarray | None:
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    h, w = arr.shape[:2]
    border = max(2, min(h, w) // 120)
    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[:border, :] = True
    border_mask[-border:, :] = True
    border_mask[:, :border] = True
    border_mask[:, -border:] = True

    if bbox is None:
        return None  # không có prior → không đủ tin cậy cho v3 (fail-closed)

    x1, y1, x2, y2 = bbox
    bx0 = max(0, int((x1 - _BBOX_REACH) * w))
    bx1 = min(w, int((x2 + _BBOX_REACH) * w))
    by0 = max(0, int((y1 - _BBOX_REACH) * h))
    by1 = min(h, int((y2 + _BBOX_REACH) * h))
    reach = np.zeros((h, w), dtype=bool)
    reach[by0:by1, bx0:bx1] = True

    # Lõi FG: nửa trong của bbox (co mỗi chiều _CORE_SHRINK) — chắc chắn là ly.
    cw, ch = x2 - x1, y2 - y1
    cx0 = max(0, int((x1 + cw * _CORE_SHRINK) * w))
    cx1 = min(w, int((x1 + cw * (1 - _CORE_SHRINK)) * w))
    cy0 = max(0, int((y1 + ch * _CORE_SHRINK) * h))
    cy1 = min(h, int((y1 + ch * (1 - _CORE_SHRINK)) * h))
    if cx1 - cx0 < 4 or cy1 - cy0 < 4:
        return None
    core = np.zeros((h, w), dtype=bool)
    core[cy0:cy1, cx0:cx1] = True

    fg_centers = _clusters_from(arr[core].reshape(-1, 3))
    # BG model: viền ảnh + vùng ngoài vùng-reach (chắc chắn không phải ly).
    bg_zone = border_mask | ~reach
    bg_centers = _clusters_from(arr[bg_zone].reshape(-1, 3))
    if fg_centers.shape[0] == 0 or bg_centers.shape[0] == 0:
        return None

    d_fg = _dist_to(arr, fg_centers)
    d_bg = _dist_to(arr, bg_centers)

    # Sure-FG: lõi (dù màu gì) và mọi pixel trong reach gần FG model rõ rệt.
    sure_fg = core.copy()
    cand = reach & (d_fg + _DECIDE_MARGIN < d_bg)
    fg_mask = sure_fg | cand
    # Làm sạch: đóng lỗ nhỏ rồi giữ cụm lớn nhất chứa lõi.
    fg_mask = ndimage.binary_closing(fg_mask, structure=np.ones((3, 3)))
    labels, n = ndimage.label(fg_mask)
    if n == 0:
        return None
    # Cụm chứa nhiều pixel lõi nhất = cụm chính.
    core_labels = np.unique(labels[core])
    core_labels = core_labels[core_labels > 0]
    if core_labels.size == 0:
        return None
    best, best_overlap = core_labels[0], -1
    for lab in core_labels.tolist():
        overlap = int(((labels == lab) & core).sum())
        if overlap > best_overlap:
            best, best_overlap = lab, overlap
    fg_mask = labels == best
    fg_mask = ndimage.binary_fill_holes(fg_mask)

    ratio = float(fg_mask.mean())
    if debug is not None:
        debug.update(
            fg_clusters=fg_centers.round(1).tolist(),
            bg_clusters=bg_centers.round(1).tolist(),
            ratio=ratio,
            dirty=float((d_bg[fg_mask] < 45.0).mean()) if fg_mask.any() else 0.0,
        )
    if ratio < 0.03 or ratio > 0.92:
        return None

    fg_mask = ndimage.binary_opening(fg_mask, structure=np.ones((3, 3)))
    if _MASK_ERODE_PX:
        er = ndimage.binary_erosion(fg_mask, iterations=_MASK_ERODE_PX)
        if bool(er.any()):
            fg_mask = er
    sigma = max(1.0, min(h, w) / 350.0)
    alpha = ndimage.gaussian_filter(fg_mask.astype(np.float32), sigma=sigma)
    alpha = np.clip(alpha, 0.0, 1.0)
    return np.where(alpha < _FEATHER_FLOOR, 0.0, alpha)


# ── Kiểm thử trên ảnh tổng hợp có GROUND TRUTH ────────────────────────────
def synth_cases() -> list[tuple[str, bytes, tuple[float, float, float, float], np.ndarray]]:
    """(tên, png, bbox chuẩn hoá, mask ground truth)."""
    cases: list[tuple[str, bytes, tuple[float, float, float, float], np.ndarray]] = []

    # 1. Nền trắng + ly chữ nhật nâu (như test hiện có).
    im = Image.new("RGB", (300, 400), (250, 250, 250))
    a = np.asarray(im).copy()
    a[120:340, 90:210] = (90, 45, 20)
    a[110:125, 85:215] = (60, 30, 12)
    gt = np.zeros((400, 300), dtype=bool)
    gt[110:340, 85:215] = True
    buf = io.BytesIO()
    Image.fromarray(a).save(buf, format="PNG")
    cases.append(("trắng+ly nâu", buf.getvalue(), (0.283, 0.275, 0.717, 0.85), gt))

    # 2. Nền gradient ấm (bàn tối → tường sáng) + ly CAM SÁNG: ca rò rỉ điển hình.
    yy, xx = np.mgrid[0:400, 0:300].astype(np.float32)
    a2 = np.zeros((400, 300, 3), dtype=np.float32)
    a2[:, :, 0] = 40 + 170 * (1 - yy / 400)
    a2[:, :, 1] = 28 + 150 * (1 - yy / 400)
    a2[:, :, 2] = 20 + 130 * (1 - yy / 400)
    a2[110:340, 100:200] = (235, 140, 20)   # ly cam sáng
    a2[300:345, 95:205] = (90, 60, 30)      # đáy ly tối (tiếp xúc bàn tối)
    a2 += np.random.default_rng(3).normal(0, 3, a2.shape)
    gt2 = np.zeros((400, 300), dtype=bool)
    gt2[110:345, 95:205] = True
    buf2 = io.BytesIO()
    Image.fromarray(np.clip(a2, 0, 255).astype(np.uint8)).save(buf2, format="PNG")
    cases.append(("gradient+ly cam", buf2.getvalue(), (0.317, 0.275, 0.683, 0.862), gt2))

    # 3. Nền nhiều vùng (bàn tối + cửa sổ sáng) + ly sáng giữa.
    a3 = np.zeros((400, 300, 3), dtype=np.float32)
    a3[:180] = (215, 205, 185)   # tường sáng
    a3[180:] = (55, 42, 30)      # bàn tối
    d = ImageDraw.Draw(Image.fromarray(a3.astype(np.uint8)))
    del d
    a3[120:330, 110:190] = (225, 130, 30)
    gt3 = np.zeros((400, 300), dtype=bool)
    gt3[120:330, 110:190] = True
    buf3 = io.BytesIO()
    Image.fromarray(np.clip(a3, 0, 255).astype(np.uint8)).save(buf3, format="PNG")
    cases.append(("2 vùng + ly", buf3.getvalue(), (0.367, 0.30, 0.633, 0.825), gt3))
    return cases


def iou(mask: np.ndarray, gt: np.ndarray) -> float:
    inter = float((mask & gt).sum())
    union = float((mask | gt).sum())
    return inter / union if union else 0.0


def main() -> None:
    print("── Ảnh TỔNG HỢP có ground truth (IoU càng cao càng tốt) ─────────")
    for name, png, bbox, gt in synth_cases():
        img = Image.open(io.BytesIO(png)).convert("RGB")
        dbg: dict = {}
        alpha = subject_alpha_v3(img, bbox, dbg)
        if alpha is None:
            print(f"  {name:18s} → FAIL-CLOSED")
            continue
        got = alpha > 0.5
        # IoU so với GT ở cùng độ phân giải.
        print(f"  {name:18s} IoU={iou(got, gt):.3f} ratio={got.mean():.3f} "
              f"dirty={dbg.get('dirty', 0):.3f}")
        # Sai số: mất pixel ly (leak ra nền) và lấn nền (halo).
        print(f"      giữ được {100 * (got & gt).sum() / gt.sum():.1f}% ly; "
              f"thừa {100 * (got & ~gt).sum() / max(1, gt.sum()):.1f}% nền")

    print("\n── Ảnh THẬT (không ground truth, đo chỉ số rủi ro) ──────────────")
    for src in ("data/menu_images/mon_tra.jpg", "data/menu_images/mon_den.png"):
        p = Path(src)
        img = Image.open(p).convert("RGB")
        w0, h0 = img.size
        ratio = min(1.0, 640 / max(w0, h0))
        small = img.resize((max(2, int(w0 * ratio)), max(2, int(h0 * ratio))),
                           Image.Resampling.LANCZOS)
        # bbox giả lập vision (đủ rộng, phủ ly + garnish).
        boxes = {
            "bbox rộng": (0.22, 0.12, 0.78, 0.86),
            "bbox chật": (0.30, 0.18, 0.70, 0.80),
        }
        for bn, bbox in boxes.items():
            dbg = {}
            alpha = subject_alpha_v3(small, bbox, dbg)
            if alpha is None:
                print(f"  {p.name} {bn:10s} → FAIL-CLOSED")
                continue
            solid = alpha > 0.5
            ys, xs = np.nonzero(solid)
            fill = solid.sum() / max(1, (ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1))
            print(f"  {p.name} {bn:10s} ratio={solid.mean():.3f} "
                  f"dirty={dbg['dirty']:.3f} fill_bbox={fill:.2f}")
            rgba = small.convert("RGBA")
            rgba.putalpha(Image.fromarray((alpha * 255).astype(np.uint8)))
            blue = Image.new("RGBA", small.size, (30, 40, 120, 255))
            blue.alpha_composite(rgba)
            over = np.asarray(small).copy()
            over[solid] = (0.45 * over[solid] + 0.55 * np.array([0, 220, 0])).astype(np.uint8)
            sheet = Image.new("RGB", (small.width * 3 + 20, small.height), (25, 25, 25))
            sheet.paste(small, (0, 0))
            sheet.paste(Image.fromarray(over), (small.width + 10, 0))
            sheet.paste(blue.convert("RGB"), (small.width * 2 + 20, 0))
            tag = bn.split()[1]
            sheet.save(OUT / f"v3_{p.stem}_{tag}.png")


if __name__ == "__main__":
    main()
