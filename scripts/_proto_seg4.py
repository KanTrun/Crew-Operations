"""Prototype v4 — mô hình màu LẶP (kiểu ICM/GrabCut) + nhất quán liên thông.

So với v3:
* Mô hình FG/BG được ƯỚC LƯỢNG LẠI 3 vòng từ chính nhãn đã phân loại → phần
  đáy ly tối (màu gần bàn tối) được học ở vòng 2 nhờ các pixel lân cận đã là FG.
* Không vứt "mọi cụm rời không chứa lõi": giữ mọi cụm có GIAO với lõi HOẶC dính
  với cụm chính (dilation) và KHÔNG giống mô hình BG.
* Hạ độ phân giải mask nhưng TINH CHỈNH RÌA ở độ phân giải gốc trong dải ±6px
  quanh biên → hết răng cưa.

Chạy: python scripts/_proto_seg4.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _proto_seg3 import _clusters_from, _dist_to  # noqa: E402

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)

_CORE_SHRINK = 0.16
_BBOX_REACH = 0.12
_DECIDE_MARGIN = 14.0
_ITER = 3
_MIN_COMP_PX = 14
_STICK_DILATE = 22


def segment(arr: np.ndarray, bbox: tuple[float, float, float, float]) -> dict:
    """Tách mask FG ở độ phân giải `arr`. Trả dict có 'mask', 'd_fg', 'd_bg'."""
    h, w = arr.shape[:2]
    border = max(2, min(h, w) // 120)
    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[:border, :] = True
    border_mask[-border:, :] = True
    border_mask[:, :border] = True
    border_mask[:, -border:] = True

    x1, y1, x2, y2 = bbox
    reach = np.zeros((h, w), dtype=bool)
    reach[
        max(0, int((y1 - _BBOX_REACH) * h)) : min(h, int((y2 + _BBOX_REACH) * h)),
        max(0, int((x1 - _BBOX_REACH) * w)) : min(w, int((x2 + _BBOX_REACH) * w)),
    ] = True
    cw, ch = x2 - x1, y2 - y1
    core = np.zeros((h, w), dtype=bool)
    core[
        max(0, int((y1 + ch * _CORE_SHRINK) * h)) : min(h, int((y1 + ch * (1 - _CORE_SHRINK)) * h)),
        max(0, int((x1 + cw * _CORE_SHRINK) * w)) : min(w, int((x1 + cw * (1 - _CORE_SHRINK)) * w)),
    ] = True
    if core.sum() < 16:
        return {"mask": None}

    bg_zone = border_mask | ~reach
    fg_centers = _clusters_from(arr[core].reshape(-1, 3))
    bg_centers = _clusters_from(arr[bg_zone].reshape(-1, 3))

    for it in range(_ITER):
        d_fg = _dist_to(arr, fg_centers)
        d_bg = _dist_to(arr, bg_centers)
        fg_label = core | (reach & (d_fg + _DECIDE_MARGIN < d_bg))
        bg_label = bg_zone | (~fg_label & (d_bg + _DECIDE_MARGIN < d_fg))
        if it < _ITER - 1:
            fg_pts = arr[fg_label]
            bg_pts = arr[bg_label]
            # Cụm màu tối thiểu 0.4% để bắt được vùng nhỏ như đáy ly tối.
            fg_centers = _clusters_from(fg_pts, min_share=0.004)
            bg_centers = _clusters_from(bg_pts, min_share=0.004)
            if fg_centers.shape[0] == 0 or bg_centers.shape[0] == 0:
                return {"mask": None}

    d_fg = _dist_to(arr, fg_centers)
    d_bg = _dist_to(arr, bg_centers)
    fg_label = core | (reach & (d_fg + _DECIDE_MARGIN < d_bg))
    fg_label = ndimage.binary_closing(fg_label, structure=np.ones((3, 3)))

    labels, n = ndimage.label(fg_label)
    if n == 0:
        return {"mask": None}
    # Cụm chính = cụm phủ lõi nhiều nhất.
    core_labels, counts = np.unique(labels[core], return_counts=True)
    keep_ids = {int(core_labels[i]) for i in range(len(core_labels)) if core_labels[i] > 0}
    if not keep_ids:
        return {"mask": None}
    primary = max(keep_ids, key=lambda lab: int(counts[list(core_labels).index(lab)]))
    mask = labels == primary

    # Cụm dính cụm chính và KHÔNG giống BG model → giữ (phần ly bị tách rời).
    near = ndimage.binary_dilation(mask, iterations=_STICK_DILATE)
    for lab in range(1, n + 1):
        if lab == primary:
            continue
        comp = labels == lab
        size = int(comp.sum())
        if size < _MIN_COMP_PX or not bool((comp & near).any()):
            continue
        if float(d_bg[comp].mean()) < 40.0:
            continue
        mask |= comp

    mask = ndimage.binary_fill_holes(mask)
    ratio = float(mask.mean())
    return {"mask": mask, "d_fg": d_fg, "d_bg": d_bg, "ratio": ratio}


def subject_alpha_v4(
    img: Image.Image, bbox: tuple[float, float, float, float] | None, debug: dict | None = None
) -> np.ndarray | None:
    from ca_agents.bg_redesign import _MASK_MAX_DIM, _MASK_ERODE_PX, _MASK_FEATHER_FLOOR

    if bbox is None:
        return None
    w0, h0 = img.size
    ratio_down = min(1.0, _MASK_MAX_DIM / max(w0, h0))
    small = img.convert("RGB").resize(
        (max(2, int(w0 * ratio_down)), max(2, int(h0 * ratio_down))), Image.Resampling.LANCZOS
    )
    arr = np.asarray(small, dtype=np.float32)
    res = segment(arr, bbox)
    if res.get("mask") is None:
        return None
    mask = res["mask"]
    if debug is not None:
        debug.update(ratio=float(mask.mean()))
    if not (0.03 <= mask.mean() <= 0.92):
        return None

    mask = ndimage.binary_opening(mask, structure=np.ones((3, 3)))
    if _MASK_ERODE_PX:
        er = ndimage.binary_erosion(mask, iterations=_MASK_ERODE_PX)
        if bool(er.any()):
            mask = er

    # Đưa mask lên độ phân giải gốc (NEAREST để không trộn nhãn) rồi tinh chỉnh
    # rìa: trong dải ±6px, quyết định lại bằng mô hình màu đã học (full-res).
    full = np.asarray(
        Image.fromarray((mask * 255).astype(np.uint8)).resize((w0, h0), Image.Resampling.NEAREST)
    ) > 127
    full_arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    band = ndimage.binary_dilation(full, iterations=6) & ~ndimage.binary_erosion(
        full, iterations=6
    )
    if band.any():
        d_fg = res.get("d_fg")
        d_bg = res.get("d_bg")
        if d_fg is not None and d_bg is not None:
            d_fg_full = np.asarray(
                Image.fromarray(np.clip(d_fg, 0, 255).astype(np.uint8)).resize(
                    (w0, h0), Image.Resampling.BILINEAR
                ),
                dtype=np.float32,
            )
            d_bg_full = np.asarray(
                Image.fromarray(np.clip(d_bg, 0, 255).astype(np.uint8)).resize(
                    (w0, h0), Image.Resampling.BILINEAR
                ),
                dtype=np.float32,
            )
            closer_fg = d_fg_full < d_bg_full
            full = np.where(band, closer_fg, full)
    del full_arr

    sigma = max(1.0, min(h0, w0) / 900.0)
    alpha = ndimage.gaussian_filter(full.astype(np.float32), sigma=sigma)
    alpha = np.clip(alpha, 0.0, 1.0)
    return np.where(alpha < _MASK_FEATHER_FLOOR, 0.0, alpha)


# ── Harness ───────────────────────────────────────────────────────────────
def make_cases() -> list[tuple[str, bytes, tuple[float, float, float, float], np.ndarray]]:
    cases = []
    rng = np.random.default_rng(11)

    # 1. Nền trắng + ly nâu.
    a = np.full((400, 300, 3), 250, dtype=np.float32)
    a[120:340, 90:210] = (90, 45, 20)
    a[110:125, 85:215] = (60, 30, 12)
    gt = np.zeros((400, 300), dtype=bool)
    gt[110:340, 85:215] = True
    cases.append(("trắng+ly nâu", a, (0.283, 0.275, 0.717, 0.85), gt))

    # 2. Gradient dọc + ly cam sáng + ĐÁY LY TỐI (ca khó nhất).
    yy, xx = np.mgrid[0:400, 0:300].astype(np.float32)
    a = np.zeros((400, 300, 3), dtype=np.float32)
    a[:, :, 0] = 40 + 170 * (1 - yy / 400)
    a[:, :, 1] = 28 + 150 * (1 - yy / 400)
    a[:, :, 2] = 20 + 130 * (1 - yy / 400)
    a[110:300, 100:200] = (235, 140, 20)
    a[300:345, 95:205] = (95, 62, 32)
    a += rng.normal(0, 3, a.shape)
    gt = np.zeros((400, 300), dtype=bool)
    gt[110:345, 95:205] = True
    cases.append(("đáy ly tối", a, (0.317, 0.275, 0.683, 0.862), gt))

    # 3. Hai vùng nền (tường sáng + bàn tối) + ly cam.
    a = np.zeros((400, 300, 3), dtype=np.float32)
    a[:180] = (215, 205, 185)
    a[180:] = (55, 42, 30)
    a[120:330, 110:190] = (225, 130, 30)
    gt = np.zeros((400, 300), dtype=bool)
    gt[120:330, 110:190] = True
    cases.append(("2 vùng nền", a, (0.367, 0.30, 0.633, 0.825), gt))

    # 4. Ly + lá garnish THÒ RA NGOÀI bbox (kiểm tra reach không cắt garnish).
    a = np.full((400, 300, 3), 245, dtype=np.float32)
    a[140:340, 110:190] = (150, 190, 60)
    a[100:145, 60:115] = (90, 170, 45)  # lá vươn sang trái, ngoài bbox
    gt = np.zeros((400, 300), dtype=bool)
    gt[140:340, 110:190] = True
    gt[100:145, 60:115] = True
    cases.append(("garnish ngoài bbox", a, (0.36, 0.34, 0.64, 0.84), gt))

    # 5. Nền bokeh chuyển sắc mạnh (rò rỉ điển hình).
    yy, xx = np.mgrid[0:400, 0:300].astype(np.float32)
    a = np.zeros((400, 300, 3), dtype=np.float32)
    a[:, :, 0] = 120 + 90 * np.sin(xx / 60.0) * np.cos(yy / 80.0)
    a[:, :, 1] = 90 + 70 * np.sin(xx / 45.0 + 1.0)
    a[:, :, 2] = 70 + 50 * np.cos(yy / 55.0)
    a[130:335, 115:195] = (200, 60, 40)
    gt = np.zeros((400, 300), dtype=bool)
    gt[130:335, 115:195] = True
    cases.append(("nền bokeh", a, (0.383, 0.325, 0.65, 0.838), gt))
    return cases


def iou(mask: np.ndarray, gt: np.ndarray) -> float:
    u = float((mask | gt).sum())
    return float((mask & gt).sum()) / u if u else 0.0


def main() -> None:
    print("── IoU vs ground truth ────────────────────────────────────────")
    print(f"{'ca':22s} {'IoU':>6s} {'giữ ly':>8s} {'thừa nền':>9s} {'ratio':>7s}")
    rows = []
    for name, arr, bbox, gt in make_cases():
        png = io.BytesIO()
        Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(png, format="PNG")
        img = Image.open(io.BytesIO(png.getvalue())).convert("RGB")
        dbg: dict = {}
        alpha = subject_alpha_v4(img, bbox, dbg)
        if alpha is None:
            print(f"{name:22s}  FAIL-CLOSED")
            continue
        got = alpha > 0.5
        kept = float((got & gt).sum()) / float(gt.sum())
        extra = float((got & ~gt).sum()) / float(gt.sum())
        rows.append((name, iou(got, gt), kept, extra))
        print(f"{name:22s} {rows[-1][1]:6.3f} {kept * 100:7.1f}% "
              f"{extra * 100:8.1f}% {got.mean():7.3f}")

        cut = got & ~gt
        over = got & gt & ndimage.binary_erosion(gt, iterations=3)
        vis = np.asarray(img).copy()
        vis[over] = (0.5 * vis[over] + 0.5 * np.array([0, 220, 0])).astype(np.uint8)
        vis[cut] = (0.3 * vis[cut] + 0.7 * np.array([255, 0, 0])).astype(np.uint8)
        vis[got & gt & ~ndimage.binary_erosion(gt, iterations=3)] = (
            0.5 * vis[got & gt & ~ndimage.binary_erosion(gt, iterations=3)]
            + 0.5 * np.array([0, 128, 255])
        ).astype(np.uint8)
        Image.fromarray(vis).save(OUT / f"v4_{name.replace(' ', '_')}.png")

    if rows:
        avg = sum(r[1] for r in rows) / len(rows)
        worst_kept = min(r[2] for r in rows)
        worst_extra = max(r[3] for r in rows)
        print(f"\n  IoU trung bình = {avg:.3f}; giữ ly thấp nhất = {worst_kept * 100:.1f}%; "
              f"thừa nền nhiều nhất = {worst_extra * 100:.1f}%")


if __name__ == "__main__":
    main()
