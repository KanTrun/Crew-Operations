"""Public Context Provider for Customer-Facing Bots & Interfaces.

Provides sanitized, public-safe DTOs for Menu, Store Profile, and Active Promotions.
Strictly isolates all internal store data (BOM quantities, raw material cost, user accounts, shifts).
"""

from __future__ import annotations

from typing import Any

from ca_api.persist import _conn, init_db, kv_get, kv_set

DEFAULT_STORE_PROFILE = {
    "ten_quan": "Nhịp Quán",
    "dia_chi": "123 Đường Cà Phê, Phường 5, Quận 3, TP. Hồ Chí Minh",
    "hotline": "0901234567",
    "gio_mo_cua": "07:00 - 22:30 (Mở cửa tất cả các ngày trong tuần)",
    "wifi_ssid": "NhipQuan_Guest",
    "wifi_pass": "nhipquan2026",
    "mo_ta": "Cà phê sạch, không gian yên tĩnh làm việc và gặp gỡ bạn bè.",
    "chinh_sach_dat_ban": "Nhận đặt bàn trước qua hotline hoặc tin nhắn fanpage cho nhóm từ 4 người trở lên.",
}

DEFAULT_PROMOTIONS = [
    {
        "id": "km_01",
        "tieu_de": "Combo Sáng Tỉnh Táo",
        "chi_tiet": "Giảm 10% khi mua Cà phê sữa + Bánh mì trước 09:00",
        "hieu_luc": "07:00 - 09:00 hàng ngày",
    },
    {
        "id": "km_02",
        "tieu_de": "Ưu đãi Đi Nhóm",
        "chi_tiet": "Mua 4 ly tặng 1 ly cùng loại cho hóa đơn từ 120.000đ",
        "hieu_luc": "Thứ 2 đến Thứ 6",
    },
]


def get_public_menu() -> list[dict[str, Any]]:
    """Retrieve active menu items with public details only (ten, gia). BOM and costs are hidden."""
    init_db()
    with _conn() as cx:
        rows = cx.execute(
            "SELECT id, ten, gia FROM menu_mon WHERE an = 0 ORDER BY ten ASC"
        ).fetchall()
    return [
        {"id": str(r[0]), "ten": str(r[1]), "gia": int(r[2]), "gia_formatted": f"{int(r[2]):,}đ"}
        for r in rows
    ]


def get_store_profile() -> dict[str, Any]:
    """Retrieve public store contact, operating hours, and location."""
    res = kv_get("store_profile", DEFAULT_STORE_PROFILE)
    if isinstance(res, dict):
        merged = DEFAULT_STORE_PROFILE.copy()
        merged.update(res)
        return merged
    return DEFAULT_STORE_PROFILE.copy()


def set_store_profile(profile: dict[str, Any]) -> None:
    """Update store profile configuration."""
    current = get_store_profile()
    current.update(profile)
    kv_set("store_profile", current)


def get_active_promotions() -> list[dict[str, Any]]:
    """Retrieve ongoing promotional campaigns."""
    res = kv_get("store_promotions", DEFAULT_PROMOTIONS)
    if isinstance(res, list):
        return res
    return DEFAULT_PROMOTIONS.copy()


def set_active_promotions(promotions: list[dict[str, Any]]) -> None:
    """Update active promotional campaigns."""
    kv_set("store_promotions", promotions)


def format_public_context_for_prompt() -> str:
    """Assemble formatted summary string for prompt context injection."""
    profile = get_store_profile()
    menu = get_public_menu()
    promos = get_active_promotions()

    menu_lines = [f"- {item['ten']}: {item['gia_formatted']}" for item in menu]
    promo_lines = [
        f"- {p['tieu_de']}: {p['chi_tiet']} (Hiệu lực: {p.get('hieu_luc', 'Đang áp dụng')})"
        for p in promos
    ]

    return f"""=== THÔNG TIN QUÁN (CÔNG KHAI) ===
Tên quán: {profile.get("ten_quan")}
Địa chỉ: {profile.get("dia_chi")}
Hotline: {profile.get("hotline")}
Giờ mở cửa: {profile.get("gio_mo_cua")}
Wifi: {profile.get("wifi_ssid")} (Mật khẩu: {profile.get("wifi_pass")})
Chính sách đặt bàn: {profile.get("chinh_sach_dat_ban")}

=== MENU ĐỒ UỐNG HIỆN HÀNH ===
{chr(10).join(menu_lines) if menu_lines else "Đang cập nhật"}

=== CHƯƠNG TRÌNH KHUYẾN MÃI ===
{chr(10).join(promo_lines) if promo_lines else "Hiện chưa có khuyến mãi mới"}
"""
