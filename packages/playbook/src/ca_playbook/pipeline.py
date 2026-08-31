"""Trạng thái pipeline cẩm nang — hiển thị UI và API."""

from __future__ import annotations

from typing import Any

from ca_playbook.sua import list_sua
from ca_playbook.vong_doi import list_luat, tim_mau

MIN_SUA = 3


def is_demo_luat(luat: dict[str, Any]) -> bool:
    if luat.get("demo") is True:
        return True
    return str(luat.get("nguon") or "") == "dung_lai_8_tuan"


def count_luat_that_quan(items: list[dict[str, Any]]) -> int:
    ok_status = {
        "de_xuat",
        "qua_vf_rule",
        "du_tap_su",
        "truot_tap_su",
        "cho_chu_quan",
        "hieu_luc",
        "tu_tat",
    }
    return sum(
        1
        for x in items
        if str(x.get("nguon") or "") == "ghi_truc_tiep"
        and str(x.get("trang_thai") or "") in ok_status
    )


def enrich_luat_ui(luat: dict[str, Any]) -> dict[str, Any]:
    out = dict(luat)
    out["mau_minh_hoa"] = is_demo_luat(luat)
    return out


def pipeline_snapshot() -> dict[str, Any]:
    sua_that = list_sua(include_synthetic=False)
    mau_that = tim_mau(sua_that)
    items = list_luat()
    hieu_luc = sum(1 for x in items if x.get("trang_thai") == "hieu_luc")
    cho_chot = sum(1 for x in items if x.get("trang_thai") == "cho_chu_quan")
    demo = sum(1 for x in items if is_demo_luat(x))

    can_chay = len(sua_that) >= MIN_SUA and len(mau_that) > 0
    thieu = max(0, MIN_SUA - len(sua_that))

    if can_chay:
        insight = {
            "severity": "ok",
            "message": (
                f"Đủ {len(sua_that)} lần sửa thật và {len(mau_that)} mẫu — "
                "có thể chạy 8 bước xét luật."
            ),
        }
    elif thieu > 0:
        insight = {
            "severity": "warn",
            "message": (
                f"Cần thêm {thieu} lần sửa thật (nhận/nhả ca, đổi lịch) "
                f"trước khi chạy 8 bước. Hiện có {len(sua_that)}."
            ),
        }
    else:
        insight = {
            "severity": "info",
            "message": "Đã đủ lần sửa nhưng chưa gom được mẫu cùng loại — tiếp tục sửa lịch đồng nhất.",
        }

    next_mau = mau_that[0] if mau_that else None
    return {
        "so_sua_that": len(sua_that),
        "so_mau_san_sang": len(mau_that),
        "so_luat_that_quan": count_luat_that_quan(items),
        "so_hieu_luc": hieu_luc,
        "so_cho_chot": cho_chot,
        "so_mau_minh_hoa": demo,
        "can_chay_8_buoc": can_chay,
        "insight": insight,
        "mau_tiep_theo": next_mau.get("mau") if next_mau else None,
    }
