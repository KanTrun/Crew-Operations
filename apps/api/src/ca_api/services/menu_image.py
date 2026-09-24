"""Sinh ảnh thẻ sản phẩm **tại máy**, tất định (plan 260923-1736).

Vì sao không gọi API ảnh đám mây
--------------------------------
Hai ràng buộc cứng của dự án:

1. **Demo phải chạy trọn khi rút mạng** (§14.9). Phụ thuộc API ảnh là mất hình
   giữa buổi bảo vệ khi mạng chập.
2. `docs/THIRD_PARTY.md` ghi free tier cloud là "dễ thu hồi", ngân sách 0 đồng.

Pillow đã có sẵn trong venv và trong CI (kéo theo bởi `reportlab`), nên không thêm
phụ thuộc mới. ADR-019 ghi lại quyết định này.

Tất định
--------
Mọi tham số hình (màu nhấn, độ nghiêng) suy từ `id` bằng SHA-256 — **cùng id luôn
ra cùng byte**. Nhờ vậy ảnh không nhảy loạn giữa các lần render, và test so byte
được. Không dùng `random` ở bất kỳ đâu.

Vì sao hình học chứ không phải emoji
------------------------------------
Emoji render khác nhau theo hệ điều hành (mất tính tất định) và vi phạm quy ước
icon của dự án (`docs/design-guidelines.md`).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

# Kích thước thẻ sản phẩm. Vuông để lưới menu luôn đều.
KICH_THUOC = 512

# Hệ màu quán (đêm quán / đồng / gỗ cháy) — `docs/design-guidelines.md`.
NEN_TREN = (38, 32, 26)
NEN_DUOI = (22, 19, 16)
COPPER = (196, 165, 116)
CHU = (240, 230, 216)

# Hình đại diện theo nhóm sản phẩm.
HINH_THEO_NHOM: dict[str, str] = {
    "ca_phe": "ly",
    "tra": "ly",
    "sinh_to": "ly",
    "nuoc_dong_chai": "chai",
    "banh": "dia",
    "nguyen_lieu": "goi",
}

# Nền riêng theo nhóm — lệch nhẹ để lưới menu có nhịp, vẫn trong tông quán.
NEN_THEO_NHOM: dict[str, tuple[int, int, int]] = {
    "ca_phe": (42, 30, 20),
    "tra": (28, 40, 26),
    "sinh_to": (44, 34, 20),
    "nuoc_dong_chai": (24, 36, 42),
    "banh": (48, 38, 24),
    "nguyen_lieu": (36, 34, 28),
}

_FONT_UNG_VIEN = (
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)


def _font(co: int) -> Any:
    """Font hệ thống cỡ `co`; không tìm được thì dùng font mặc định của Pillow.

    Không nhúng font vào repo: thiếu font có dấu thì chữ ra ô vuông nhưng ảnh vẫn
    dùng được — không đáng để thêm vài trăm KB nhị phân cho một tấm ảnh thẻ.
    """
    from PIL import ImageFont

    for path in _FONT_UNG_VIEN:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, co)
            except Exception:
                continue
    return ImageFont.load_default()


def hat_giong(mon_id: str) -> int:
    """Số tất định suy từ id — cùng id luôn ra cùng ảnh."""
    return int.from_bytes(hashlib.sha256(mon_id.encode("utf-8")).digest()[:8], "big")


def mau_nen(mon_id: str, nhom: str) -> tuple[int, int, int]:
    """Nền riêng cho món, xoay quanh tông của nhóm."""
    lech = hat_giong(mon_id) % 46 - 23
    nen = NEN_THEO_NHOM.get(nhom, NEN_TREN)
    return tuple(max(0, min(255, c + lech)) for c in nen)  # type: ignore[return-value]


def _ve_nen(img: Any, tren: tuple[int, int, int], duoi: tuple[int, int, int]) -> None:
    """Nền gradient dọc cho có chiều sâu."""
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    for y in range(KICH_THUOC):
        t = y / (KICH_THUOC - 1)
        mau = tuple(int(tren[i] + (duoi[i] - tren[i]) * t) for i in range(3))
        draw.line([(0, y), (KICH_THUOC, y)], fill=mau)


def _ve_bieu_tuong(draw: Any, hinh: str, nhan: tuple[int, int, int], hat: int) -> None:
    """Vẽ khối hình học đại diện nhóm: ly / chai / đĩa bánh / gói."""
    cx, cy = KICH_THUOC // 2, KICH_THUOC // 2 + 8
    sang = tuple(min(255, c + 42) for c in nhan)
    toi = tuple(max(0, c - 18) for c in nhan)

    if hinh == "ly":
        rong_tren, rong_duoi, cao = 96, 74, 150
        draw.polygon(
            [
                (cx - rong_tren, cy - cao // 2),
                (cx + rong_tren, cy - cao // 2),
                (cx + rong_duoi, cy + cao // 2),
                (cx - rong_duoi, cy + cao // 2),
            ],
            fill=nhan,
            outline=COPPER,
        )
        draw.ellipse(
            [cx - rong_tren, cy - cao // 2 - 16, cx + rong_tren, cy - cao // 2 + 16],
            fill=sang,
            outline=COPPER,
        )
        lech = 10 + hat % 16
        draw.line(
            [(cx + lech, cy - cao // 2 - 30), (cx + lech + 22, cy - cao // 2 - 96)],
            fill=COPPER,
            width=9,
        )
    elif hinh == "chai":
        rong, cao = 62, 150
        draw.rounded_rectangle(
            [cx - rong, cy - cao // 2, cx + rong, cy + cao // 2],
            radius=16,
            fill=nhan,
            outline=COPPER,
        )
        draw.rectangle([cx - 22, cy - cao // 2 - 46, cx + 22, cy - cao // 2], fill=nhan, outline=COPPER)
        draw.rounded_rectangle([cx - 26, cy - cao // 2 - 68, cx + 26, cy - cao // 2 - 42], radius=6, fill=COPPER)
        draw.rounded_rectangle([cx - rong + 14, cy - 26, cx + rong - 14, cy + 40], radius=10, fill=toi, outline=COPPER)
    elif hinh == "dia":
        draw.ellipse([cx - 132, cy + 34, cx + 132, cy + 92], fill=(30, 25, 20), outline=COPPER)
        draw.rounded_rectangle([cx - 74, cy - 54, cx + 74, cy + 44], radius=14, fill=nhan, outline=COPPER)
        draw.arc([cx - 74, cy - 96, cx + 74, cy - 12], start=180, end=360, fill=COPPER, width=5)
    else:
        draw.polygon(
            [(cx - 88, cy - 74), (cx + 88, cy - 74), (cx + 104, cy + 88), (cx - 104, cy + 88)],
            fill=nhan,
            outline=COPPER,
        )
        draw.line([(cx - 88, cy - 74), (cx - 104, cy + 88)], fill=COPPER, width=4)
        draw.line([(cx + 88, cy - 74), (cx + 104, cy + 88)], fill=COPPER, width=4)
        draw.line([(cx - 84, cy - 46), (cx + 84, cy - 46)], fill=COPPER, width=4)


def _ngat_dong(draw: Any, text: str, font: Any, rong_toi_da: int) -> list[str]:
    """Ngắt tên món thành tối đa hai dòng vừa bề rộng."""
    dong: list[str] = []
    hien_tai = ""
    for t in str(text).split():
        thu = f"{hien_tai} {t}".strip()
        if draw.textlength(thu, font=font) <= rong_toi_da or not hien_tai:
            hien_tai = thu
        else:
            dong.append(hien_tai)
            hien_tai = t
    if hien_tai:
        dong.append(hien_tai)
    return dong[:2]


def ve_anh(mon: dict[str, Any]) -> Any:
    """Vẽ ảnh thẻ cho một món. Trả đối tượng `PIL.Image` (không ghi đĩa).

    Tách khỏi phần ghi đĩa để tầng HTTP trả thẳng bytes mà không cần thư mục tạm.
    """
    from PIL import Image, ImageDraw

    mon_id = str(mon.get("id") or "").strip()
    if not mon_id:
        raise ValueError("món thiếu id")
    ten = str(mon.get("ten") or mon_id)
    nhom = str(mon.get("nhom") or "")

    img = Image.new("RGB", (KICH_THUOC, KICH_THUOC), NEN_TREN)
    _ve_nen(img, mau_nen(mon_id, nhom), NEN_DUOI)

    draw = ImageDraw.Draw(img)
    _ve_bieu_tuong(draw, HINH_THEO_NHOM.get(nhom, "ly"), mau_nen(mon_id, nhom), hat_giong(mon_id))

    # Dải chân tối để chữ luôn đọc được, kể cả khi hình đè xuống.
    draw.rectangle([0, KICH_THUOC - 130, KICH_THUOC, KICH_THUOC], fill=(16, 14, 12))

    font_ten = _font(30)
    y = KICH_THUOC - 116
    for d in _ngat_dong(draw, ten, font_ten, KICH_THUOC - 56):
        w = draw.textlength(d, font=font_ten)
        draw.text(((KICH_THUOC - w) / 2, y), d, font=font_ten, fill=CHU)
        y += 36

    gia = mon.get("gia")
    if isinstance(gia, int) and gia > 0:
        font_gia = _font(24)
        chu_gia = f"{gia:,}".replace(",", ".") + "đ"
        w = draw.textlength(chu_gia, font=font_gia)
        draw.text(((KICH_THUOC - w) / 2, KICH_THUOC - 54), chu_gia, font=font_gia, fill=COPPER)

    # Vạch nhấn trên đỉnh — dấu nhận dạng thẻ sản phẩm của quán.
    draw.rectangle([KICH_THUOC // 2 - 46, 26, KICH_THUOC // 2 + 46, 31], fill=COPPER)
    return img


def ghi_anh(mon: dict[str, Any], thu_muc: Path) -> Path:
    """Vẽ và ghi ảnh PNG cho món. Trả đường dẫn đã ghi."""
    thu_muc.mkdir(parents=True, exist_ok=True)
    dich = thu_muc / f"{str(mon.get('id')).strip()}.png"
    ve_anh(mon).save(dich, format="PNG", optimize=True)
    return dich


def bytes_anh(mon: dict[str, Any]) -> bytes:
    """Ảnh PNG dạng bytes — cho `Response` của FastAPI."""
    from io import BytesIO

    buf = BytesIO()
    ve_anh(mon).save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def bam_anh(mon: dict[str, Any]) -> str:
    """Băm ngắn của ảnh — dùng cho ETag và để test khẳng định tính tất định."""
    return hashlib.sha256(bytes_anh(mon)).hexdigest()[:16]
