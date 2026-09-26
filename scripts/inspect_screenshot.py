"""Đo nội dung thật của một ảnh chụp màn hình.

Vì sao cần: ảnh chụp toàn nền tối (app này là dark theme) rất dễ bị đọc nhầm
thành "ảnh trắng/ảnh hỏng". Đo phân bố điểm ảnh là cách duy nhất biết chắc ảnh
có nội dung hay không — mắt đọc một ảnh 1440x900 thu nhỏ về vài trăm pixel
không phân biệt được "nền tối đồng nhất" với "không render gì".

Chạy:  python scripts/inspect_screenshot.py <ảnh> [<ảnh> ...]
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    print("Cần Pillow: .venv\\Scripts\\python.exe -m pip install pillow")
    raise SystemExit(2) from None


def describe(path: Path) -> None:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = list(img.getdata())
    total = len(px)

    # Màu phổ biến nhất = màu nền. Phần còn lại là nội dung.
    counts = Counter(px)
    top, top_n = counts.most_common(1)[0]
    uniq = len(counts)

    # "Nội dung" = điểm ảnh khác màu nền phổ biến nhất một ngưỡng đủ lớn.
    def far(c: tuple[int, int, int]) -> bool:
        return abs(c[0] - top[0]) + abs(c[1] - top[1]) + abs(c[2] - top[2]) > 24

    content = sum(n for c, n in counts.items() if far(c))

    # Độ sáng trung bình: phân biệt "nền tối có nội dung" với "ảnh trắng".
    avg = tuple(round(sum(c[i] for c in px) / total) for i in range(3))
    bright = sum(1 for c in px if sum(c) / 3 > 200) / total
    dark = sum(1 for c in px if sum(c) / 3 < 40) / total

    print(f"\n{path.name}  {w}x{h}")
    print(f"  nền phổ biến     : rgb{top}  ({top_n * 100 / total:.1f}% điểm ảnh)")
    print(f"  màu khác nhau    : {uniq}")
    print(f"  ĐIỂM ẢNH CÓ NỘI DUNG: {content * 100 / total:.1f}%")
    print(f"  sáng trung bình  : rgb{avg}")
    print(f"  tỉ lệ rất sáng   : {bright * 100:.1f}%   tỉ lệ rất tối: {dark * 100:.1f}%")

    if uniq < 8:
        verdict = "TRỐNG — gần như một màu duy nhất"
    elif content * 100 / total < 2:
        verdict = "GẦN TRỐNG — nội dung dưới 2%"
    elif bright > 0.9:
        verdict = "TRẮNG — có thể chưa render/CSS chưa nạp"
    else:
        verdict = "CÓ NỘI DUNG"
    print(f"  KẾT LUẬN         : {verdict}")


def main() -> int:
    args = sys.argv[1:]
    if not args:
        d = Path("data/out/ui-review")
        args = [str(p) for p in sorted(d.glob("*.png"))]
    if not args:
        print("Không có ảnh nào để đo.")
        return 1
    for a in args:
        p = Path(a)
        if not p.exists():
            print(f"Thiếu file: {p}")
            continue
        describe(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
