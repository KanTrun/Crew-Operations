"""Kiểm tra ĐƯỜNG THẬT: vision LLM (Gemini) lấy bbox + GrabCut + composite.

Không monkeypatch gì. Chạy trên ảnh thật để xác nhận:
1. bbox mà vision trả về có hợp lý không (in ra + vẽ).
2. mask GrabCut + composite có giữ trọn ly không.
3. So sánh với mask cũ (flood-fill) để thấy cải thiện.

Chạy: python scripts/_diag_real.py [ảnh...]
"""

from __future__ import annotations

import io
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "agents" / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ca_agents import bg_redesign as B  # noqa: E402
from ca_agents.llm import ensure_dotenv  # noqa: E402
from _proto_seg9 import annex, clean, grabcut_rect, metrics, rect_from_bbox  # noqa: E402

OUT = Path("data/menu_images/_debug")
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    ensure_dotenv()
    srcs = sys.argv[1:] or ["data/menu_images/mon_tra.jpg", "data/menu_images/mon_den.png"]
    for src in srcs:
        p = Path(src)
        raw = p.read_bytes()
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
        img = B._decode_original(raw)
        assert img is not None
        w0, h0 = img.size
        ratio = min(1.0, B._MASK_MAX_DIM / max(w0, h0))
        small = img.resize((max(2, int(w0 * ratio)), max(2, int(h0 * ratio))),
                           Image.Resampling.LANCZOS)
        print(f"\n=== {p.name} {w0}x{h0} (mask ở {small.size}) ===")

        t0 = time.perf_counter()
        bbox = B._subject_bbox(raw, mime)
        dt_vision = time.perf_counter() - t0
        print(f"  vision bbox = {bbox}  ({dt_vision:.1f}s)")

        base = clean(grabcut_rect(
            np.asarray(small), rect_from_bbox(bbox, small.width, small.height)
        )) if bbox else None
        if base is None:
            print("  !! GrabCut không cho mask hợp lệ")
            continue
        grown, info = annex(np.asarray(small), base)
        final = clean(grown)
        assert final is not None
        print(f"  GrabCut: ratio={base.mean():.3f} → sau annex={final.mean():.3f} "
              f"(+{info.get('annex_px', 0)}px)")

        # Mask cũ để so sánh.
        old = B._subject_alpha(small, bbox)
        old_ratio = float((old > 0.5).mean()) if old is not None else float("nan")
        print(f"  mask CŨ (flood-fill): ratio={old_ratio:.3f}")

        # Ảnh minh hoạ: gốc | mask cũ | mask mới | composite giả (nền tối)
        panels = []
        vis_old = np.asarray(small).copy()
        if old is not None:
            solid = old > 0.5
            vis_old[solid] = (0.5 * vis_old[solid] + 0.5 * np.array([255, 0, 0])).astype(np.uint8)
        panels.append(Image.fromarray(vis_old))
        vis_new = np.asarray(small).copy()
        vis_new[final] = (0.5 * vis_new[final] + 0.5 * np.array([0, 220, 0])).astype(np.uint8)
        panels.append(Image.fromarray(vis_new))

        for label, mask_bool, alpha in (
            ("cũ", (old > 0.5) if old is not None else None, old),
            ("mới", final, final.astype(np.float32)),
        ):
            if mask_bool is None or alpha is None:
                continue
            rgba = small.convert("RGBA")
            a8 = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
            rgba.putalpha(Image.fromarray(a8))
            canvas = Image.new("RGBA", small.size, (26, 18, 12, 255))
            # Vẽ "bàn" tối để lộ mọi pixel nền cũ còn sót.
            d = ImageDraw.Draw(canvas)
            d.rectangle([0, int(small.height * 0.72), small.width, small.height],
                        fill=(38, 26, 16, 255))
            canvas.alpha_composite(rgba)
            panels.append(canvas.convert("RGB"))
            # Zoom rìa: hộp bao mask + đệm 40px, phóng 2x.
            ys, xs = np.nonzero(mask_bool)
            pad = 40
            x0, x1 = max(0, int(xs.min()) - pad), min(small.width, int(xs.max()) + pad)
            y0, y1 = max(0, int(ys.min()) - pad), min(small.height, int(ys.max()) + pad)
            crop = canvas.convert("RGB").crop((x0, y0, x1, y1))
            crop = crop.resize((crop.width * 2, crop.height * 2), Image.Resampling.LANCZOS)
            crop.save(OUT / f"real_{p.stem}_{label}_zoom.png")

        sheet = Image.new("RGB", (small.width * len(panels) + 10 * (len(panels) - 1),
                                  small.height), (25, 25, 25))
        for i, pan in enumerate(panels):
            sheet.paste(pan, (i * (small.width + 10), 0))
        sheet.save(OUT / f"real_{p.stem}_sheet.png")
        print(f"  → data/menu_images/_debug/real_{p.stem}_sheet.png")


if __name__ == "__main__":
    main()
