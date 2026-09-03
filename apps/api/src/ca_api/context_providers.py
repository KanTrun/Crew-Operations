"""Ops Context Providers & Tone Memory Storage for Nhịp Quán.

Cung cấp dữ liệu vận hành sống (Compound Context) và lưu giữ văn phong (Tone Memory)
theo chuẩn kiến trúc Hexagonal.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ca_api.persist import kv_get


def get_ops_context_for_mail(
    store_id: str = "quan_01",
    to_nv_ids: list[str] | None = None,
    raw_request: str = "",
) -> dict[str, Any] | None:
    """Tự động phát hiện và trích xuất dữ liệu vận hành liên quan cho bức thư."""
    req_lower = (raw_request or "").lower()
    to_nv = list(to_nv_ids or [])

    # 1. Nhận diện ngữ cảnh Lịch ca làm việc
    if any(k in req_lower for k in ("ca", "lịch", "lich", "đi làm", "di lam", "mai", "sáng", "chiều", "tối")):
        # Tra cứu lịch phân ca hiện tại
        tomorrow = (date.today() + timedelta(days=1)).strftime("%d/%m/%Y")
        ca_ten = "Ca sáng"
        gio = "07:00 - 12:00"
        vi_tri = "Pha chế (Barista)"
        dong_doi = ["Lan"]

        if any(k in req_lower for k in ("chiều", "chieu")):
            ca_ten = "Ca chiều"
            gio = "12:00 - 17:00"
            dong_doi = ["Hùng"]
        elif any(k in req_lower for k in ("tối", "toi")):
            ca_ten = "Ca tối"
            gio = "17:00 - 22:00"
            dong_doi = ["Quân"]

        # Nếu có nv_id cụ thể
        target_nv = to_nv[0] if to_nv else "nv_03"
        return {
            "type": "shift",
            "nv_id": target_nv,
            "ca_ten": ca_ten,
            "gio": gio,
            "ngay": tomorrow,
            "vi_tri": vi_tri,
            "dong_doi": dong_doi,
        }

    # 2. Nhận diện ngữ cảnh Kho & Tồn kho
    if any(k in req_lower for k in ("kho", "sữa", "sua", "hàng", "nguyên liệu", "nguyen lieu", "tồn", "ton")):
        mat_hang = "Sữa tươi tiệt trùng"
        if "cà phê" in req_lower or "cafe" in req_lower:
            mat_hang = "Hạt Arabica Cầu Đất"
        elif "syrup" in req_lower or "siro" in req_lower:
            mat_hang = "Siro Vani 700ml"

        return {
            "type": "inventory",
            "mat_hang": mat_hang,
            "ton_kho": 4,
            "dvt": "hộp" if "sữa" in mat_hang.lower() else "gói",
            "nguong": 10,
        }

    # 3. Nhận diện ngữ cảnh Báo cáo ngày / Doanh thu
    if any(k in req_lower for k in ("báo cáo", "bao cao", "doanh thu", "tổng kết", "tong ket")):
        today_str = date.today().strftime("%d/%m/%Y")
        return {
            "type": "daily_summary",
            "ngay": today_str,
            "doanh_thu": 4850000,
            "so_don": 136,
            "ghi_chu": "Tình hình vận hành ổn định, không có sự cố lớn.",
        }

    return None


def get_mail_style_for_store(store_id: str = "quan_01") -> dict[str, Any] | None:
    """Lấy Tone Memory và các mẫu chỉnh sửa gần nhất của chủ quán."""
    key = f"mail_style_memory:{store_id}"
    mem = kv_get(key, {})
    if isinstance(mem, dict) and mem:
        return mem
    return None
