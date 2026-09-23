# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Gate UI web — `useToasts()` phải đi kèm `<Toasts>`.

Lỗi thật đã xảy ra (260920, trang `/page-quan/dat-ban`): hook `useToasts()` được
gọi và `push()` được dùng ở 5 chỗ, nhưng component `<Toasts>` không hề được
render. Hệ quả: mọi thông báo thành công/lỗi im lặng hoàn toàn — nhân viên bấm
"Vào bàn"/"Hủy" xong không biết thao tác có ăn hay không. Cùng lỗi có ở
`/page-quan`, `/inbox`, `/page-quan/fb-inbox`.

Không có TypeScript nào bắt được lỗi này: `push` là hàm hợp lệ, chỉ là kết quả
của nó không được vẽ ra. Vì vậy phải kiểm bằng phân tích tĩnh trên mã nguồn.

Gate này quét mọi file `.tsx` trong `apps/web/src`:
- Có gọi `useToasts()`  ⇒ phải có `<Toasts ... />`.
- Có `<Toasts>` ⇒ phải có `useToasts()` (tránh render với biến không tồn tại).

Ngoại lệ có lý do nằm trong `MIEN_TRU`.
"""

from __future__ import annotations

import re
from pathlib import Path

WEB_SRC = Path(__file__).resolve().parents[3] / "web" / "src"

# File cố ý không theo cặp gọi-render, kèm lý do.
MIEN_TRU: dict[str, str] = {
    # `kit.tsx` là nơi ĐỊNH NGHĨA hook và component, không phải nơi dùng.
    "ui/kit.tsx": "định nghĩa useToasts/Toasts",
}

_RE_GOI_HOOK = re.compile(r"\buseToasts\s*\(")
_RE_RENDER = re.compile(r"<Toasts\b")


def _cac_file_tsx() -> list[Path]:
    return sorted(WEB_SRC.rglob("*.tsx"))


def test_web_src_ton_tai() -> None:
    """Chốt an toàn: nếu đường dẫn sai thì gate sẽ quét 0 file và báo sạch GIẢ."""
    assert WEB_SRC.is_dir(), f"không thấy thư mục mã nguồn web: {WEB_SRC}"
    assert _cac_file_tsx(), "không tìm thấy file .tsx nào — gate sẽ báo sạch giả"


def test_use_toasts_luon_di_kem_render_toasts() -> None:
    """Gọi `useToasts()` mà không render `<Toasts>` = thông báo bị nuốt."""
    vi_pham: list[str] = []
    for path in _cac_file_tsx():
        rel = path.relative_to(WEB_SRC).as_posix()
        if rel in MIEN_TRU:
            continue
        text = path.read_text(encoding="utf-8")
        co_goi = bool(_RE_GOI_HOOK.search(text))
        co_render = bool(_RE_RENDER.search(text))
        if co_goi and not co_render:
            vi_pham.append(f"{rel}: gọi useToasts() nhưng thiếu <Toasts ... />")
        if co_render and not co_goi:
            vi_pham.append(f"{rel}: render <Toasts> nhưng không gọi useToasts()")
    assert not vi_pham, "Thông báo bị nuốt (thêm <Toasts> hoặc khai báo MIEN_TRU):\n" + "\n".join(
        vi_pham
    )
