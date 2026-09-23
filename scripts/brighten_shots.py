"""Tăng sáng ảnh chụp app tối để ĐỌC ĐƯỢC bố cục — NHỊP QUÁN.

App là dark theme: 85-90% điểm ảnh nằm sát đen, nên ảnh chụp thu nhỏ trông như
trống dù thực tế có nội dung. Script này giãn độ sáng (không đổi màu sắc tương
đối) để mắt đọc được tầng bậc bố cục, đồng thời cắt thành các đoạn dọc để xem
từng phần thay vì một ảnh dài bị thu nhỏ mất chi tiết.

Chạy:
  python scripts/brighten_shots.py <thư-mục-ảnh> [--gain 3.2] [--slices 4]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageEnhance


def stretch(img: Image.Image, gain: float) -> Image.Image:
    """Giãn tuyến tính quanh mức sáng thấp nhất, giữ nguyên tỉ lệ màu.

    Không dùng autocontrast mặc định: nó kéo cả kênh sáng nhất lên 255, làm mất
    tương phản giữa các bậc bề mặt (đúng thứ cần nhìn để đánh giá elevation).
    """
    px = img.convert("RGB")
    lo = 8.0            # sàn: coi mọi thứ dưới mức này là đen nền
    return px.point(lambda v: min(255, max(0, (v - lo) * gain)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--gain", type=float, default=3.2)
    ap.add_argument("--slices", type=int, default=1)
    ap.add_argument("--out-suffix", default="-lit")
    args = ap.parse_args()

    folder = Path(args.folder)
    out = folder / "lit"
    out.mkdir(parents=True, exist_ok=True)

    for p in sorted(folder.glob("*.png")):
        img = stretch(Image.open(p), args.gain)
        # Giãn tương phản nhẹ sau khi tăng sáng, để bậc bề mặt tách ra rõ.
        img = ImageEnhance.Contrast(img).enhance(1.15)

        if args.slices > 1:
            w, h = img.size
            step = h // args.slices
            for i in range(args.slices):
                top = i * step
                bottom = h if i == args.slices - 1 else (i + 1) * step
                part = img.crop((0, top, w, bottom))
                # Thu về bề rộng đọc được nhưng không mất chi tiết chữ.
                if part.width > 1500:
                    ratio = 1500 / part.width
                    part = part.resize((1500, int(part.height * ratio)), Image.LANCZOS)
                part.save(out / f"{p.stem}{args.out_suffix}-{i + 1}.png")
        else:
            if img.width > 1500:
                ratio = 1500 / img.width
                img = img.resize((1500, int(img.height * ratio)), Image.LANCZOS)
            img.save(out / f"{p.stem}{args.out_suffix}.png")

    print(f"Đã tạo ảnh tăng sáng trong: {out}")
    for f in sorted(out.glob("*.png")):
        print(f"  {f.name}  {Image.open(f).size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
