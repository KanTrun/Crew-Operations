"""Agent mẹ–con cho hao hụt — AG-COPILOT điều phối, AG-WASTE tính (plan 260923-1736).

Khẳng định:

1. Mẹ gọi hàm thuần của con qua nguồn được inject — không tự sinh số.
2. Mẹ và bề mặt HTTP dùng **cùng** hàm, nên không thể lệch số.
3. Chưa cấu hình nguồn ⇒ trả lời trung thực, không sập, không bịa.
4. Câu hỏi định lượng thật của người quán vào đúng intent ANALYZE_WASTE.
"""

from __future__ import annotations

from typing import Any

import pytest
from ca_agents.ag_copilot import tool_registry as tr
from ca_agents.ag_waste import ngay_hom_nay, tinh_tu_nguon


@pytest.fixture
def giu_nguon() -> Any:
    """Giữ và phục hồi nguồn được inject — `_SOURCES` là trạng thái toàn cục."""
    cu = dict(tr._SOURCES)
    yield
    tr._SOURCES.clear()
    tr._SOURCES.update(cu)


def _nguon_that(*, co_du_lieu: bool = True) -> dict[str, Any]:
    # Phải dùng ngày VN (+7) — cùng khóa với tinh_tu_nguon(ky="hom_nay").
    # date.today() trên CI (UTC) lệch sau 17:00 UTC → lọc hết dữ liệu.
    hom_nay = ngay_hom_nay()
    kiem_ke = (
        [{
            "ngay": hom_nay,
            "muc": [{"mat_hang": "ca_phe_hat", "dau_ca": 500, "nhap_trong_ca": 0, "cuoi_ca": 300, "hao_hut_ghi": 0}],
        }]
        if co_du_lieu
        else []
    )
    return {
        "kv_get": lambda key, default: {
            "kiem_ke": kiem_ke,
            "waste_notes": [
                {"nguyen_nhan": "roi_do", "mat_hang": "ca_phe_hat", "ghi_chu": "Đổ 2 ly", "luc": f"{hom_nay}T09:00:00"},
                {"nguyen_nhan": "roi_do", "mat_hang": "ca_phe_hat", "ghi_chu": "Rơi hộp sữa", "luc": f"{hom_nay}T10:00:00"},
            ],
        }.get(key, default),
        "menu_list": lambda **_: [{"id": "latte", "ten": "Latte", "an": False, "bom": {"cafe_g": 18}}],
        "don_list": lambda **_: [
            {"id": "d1", "trang_thai": "xong", "luc": f"{hom_nay}T08:00:00", "dong": [{"mon_id": "latte", "so_luong": 10}]}
        ],
        "waste_cluster": None,
        "loss_engine": tinh_tu_nguon,
    }


# ── Con tính, mẹ diễn giải ────────────────────────────────────────────────────


def test_me_tra_ve_so_that_tu_con(giu_nguon: None) -> None:
    """Mẹ không tự sinh số: mọi con số phải khớp kết quả hàm thuần của con."""
    tr.configure_data_sources(**_nguon_that())
    r = tr.tool_get_waste_summary(store_id="quan_01", khoang_ngay="hom_nay")

    assert r.success is True
    assert r.intent == "ANALYZE_WASTE"
    assert r.data["co_du_lieu"] is True
    assert r.data["tong_dong"] == 1

    dong = r.data["dong"][0]
    assert dong["mat_hang"] == "ca_phe_hat"
    assert dong["ly_thuyet"] == 180.0  # 18g × 10 phần
    assert dong["thuc_te"] == 200.0    # 500 − 300
    assert dong["lech"] == 20.0


def test_me_khong_tu_dien_giai_lai_so(giu_nguon: None) -> None:
    """Số trong câu trả lời phải là số con trả về, không phải số mẹ nghĩ ra.

    Gọi mẹ hai lần với cùng dữ liệu ⇒ cùng kết quả (tất định).
    """
    tr.configure_data_sources(**_nguon_that())
    a = tr.tool_get_waste_summary(khoang_ngay="hom_nay")
    b = tr.tool_get_waste_summary(khoang_ngay="hom_nay")
    assert a.summary == b.summary
    assert a.explanation == b.explanation


def test_tom_tat_neu_so_va_nguyen_nhan(giu_nguon: None) -> None:
    """Câu tóm tắt phải đọc lên hiểu được: có số lượng, có nguyên nhân hàng đầu."""
    tr.configure_data_sources(**_nguon_that())
    r = tr.tool_get_waste_summary(khoang_ngay="hom_nay")

    assert "Hao hụt" in r.summary
    assert "Rơi đổ khi làm" in r.summary
    assert "2 lần" in r.summary


def test_giai_thich_neu_nguon_so(giu_nguon: None) -> None:
    """Người đọc phải biết số này ở đâu ra để biết mức tin."""
    tr.configure_data_sources(**_nguon_that())
    r = tr.tool_get_waste_summary(khoang_ngay="hom_nay")

    assert "định mức công thức" in r.explanation
    assert "kiểm kê" in r.explanation


# ── Thiếu dữ liệu: trung thực ─────────────────────────────────────────────────


def test_chua_co_du_lieu_thi_noi_that(giu_nguon: None) -> None:
    """Không có phiếu kiểm kê lẫn đơn ⇒ nói chưa có dữ liệu, không bịa số 0."""
    tr.configure_data_sources(**_nguon_that(co_du_lieu=False))
    # Bỏ hẳn waste_notes để không còn dòng nào ở vế thực tế.
    tr.configure_data_sources(
        kv_get=lambda key, default: default,
        menu_list=lambda **_: [],
        don_list=lambda **_: [],
        waste_cluster=None,
        loss_engine=tinh_tu_nguon,
    )
    r = tr.tool_get_waste_summary(khoang_ngay="hom_nay")

    assert r.success is True
    assert r.data["co_du_lieu"] is False
    assert "Chưa có dữ liệu" in r.summary


def test_thieu_mot_ve_thi_me_noi_ro(giu_nguon: None) -> None:
    """Có kiểm kê mà chưa có đơn ⇒ mẹ phải nói thiếu vế, không nói 'đạt'."""
    hom_nay = ngay_hom_nay()
    tr.configure_data_sources(
        kv_get=lambda key, default: {
            "kiem_ke": [{"ngay": hom_nay, "muc": [{"mat_hang": "sua_tuoi", "dau_ca": 25, "nhap_trong_ca": 8, "cuoi_ca": 26, "hao_hut_ghi": 0}]}],
            "waste_notes": [],
        }.get(key, default),
        menu_list=lambda **_: [],
        don_list=lambda **_: [],
        waste_cluster=None,
        loss_engine=tinh_tu_nguon,
    )
    r = tr.tool_get_waste_summary(khoang_ngay="hom_nay")

    assert r.data["so_thieu_du_lieu"] == 1
    assert "chưa đủ dữ liệu" in r.summary
    assert r.data["dong"][0]["thieu_ve"] == ["ly_thuyet"]


def test_danh_dau_du_lieu_mau_trong_cau_tra_loi(giu_nguon: None) -> None:
    """Số từ bộ mẫu phải được nói rõ, không để nhầm là số thật của quán."""
    hom_nay = ngay_hom_nay()
    tr.configure_data_sources(
        kv_get=lambda key, default: {
            "kiem_ke": [{
                "id": "fx_kk_01",
                "nguon": "mo_phong_fixture",
                "ngay": hom_nay,
                "muc": [{"mat_hang": "da", "dau_ca": 10, "nhap_trong_ca": 0, "cuoi_ca": 4, "hao_hut_ghi": 0}],
            }],
            "waste_notes": [],
        }.get(key, default),
        menu_list=lambda **_: [],
        don_list=lambda **_: [],
        waste_cluster=None,
        loss_engine=tinh_tu_nguon,
    )
    r = tr.tool_get_waste_summary(khoang_ngay="hom_nay")

    assert r.data["co_du_lieu_mau"] is True
    assert "bộ mẫu" in r.explanation


# ── Chưa cấu hình nguồn ───────────────────────────────────────────────────────


def test_chua_cau_hinh_nguon_thi_lui_ve_gom_cum(giu_nguon: None) -> None:
    """Môi trường không có tầng API vẫn trả lời được, không sập."""
    tr.configure_data_sources(**_nguon_that())
    tr._SOURCES.pop("loss_engine", None)
    r = tr.tool_get_waste_summary(khoang_ngay="hom_nay")

    assert r.success is True
    assert r.data["so_ghi_nhan"] == 2
    assert "ghi chú" in r.summary


def test_chua_cau_hinh_nguon_va_rong_thi_that(giu_nguon: None) -> None:
    tr.configure_data_sources(
        kv_get=lambda key, default: default,
        waste_cluster=None,
    )
    tr._SOURCES.pop("loss_engine", None)
    r = tr.tool_get_waste_summary(khoang_ngay="hom_nay")

    assert r.success is True
    assert r.data["co_du_lieu"] is False
    assert "Chưa có ghi chú" in r.summary


def test_nguon_loi_khong_lam_sap_tool(giu_nguon: None) -> None:
    """`menu_list`/`don_list` ném lỗi ⇒ vẫn trả kết quả, không 500."""

    def _no(*_a: Any, **_k: Any) -> list[Any]:
        raise RuntimeError("db down")

    tr.configure_data_sources(
        kv_get=lambda key, default: {"waste_notes": []}.get(key, default),
        menu_list=_no,
        don_list=_no,
        waste_cluster=None,
        loss_engine=tinh_tu_nguon,
    )
    r = tr.tool_get_waste_summary(khoang_ngay="hom_nay")
    assert r.success is True


# ── Không tự sinh số ──────────────────────────────────────────────────────────


def test_tool_khong_import_ca_api_hay_agent_khac() -> None:
    """Cổng kiến trúc: tool registry chỉ nhận dữ liệu qua inject.

    Soi đúng câu lệnh import (không soi chuỗi con trong cả file) để bắt được vi
    phạm thật mà không báo sai vì tài liệu có nhắc tên module.
    """
    import ast
    import inspect

    cay = ast.parse(inspect.getsource(tr))
    cam = ("ca_api", "ca_playbook", "ca_gates", "ca_agents.ag_waste")
    for node in ast.walk(cay):
        ten = ""
        if isinstance(node, ast.Import):
            ten = " ".join(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            ten = node.module or ""
        for x in cam:
            assert not ten.startswith(x), f"tool_registry không được import {ten}"


def test_khong_bia_so_khi_hai_ve_rong(giu_nguon: None) -> None:
    """Hai vế rỗng ⇒ không có dòng nào, không có số nào được sinh ra."""
    tr.configure_data_sources(
        kv_get=lambda key, default: default,
        menu_list=lambda **_: [],
        don_list=lambda **_: [],
        waste_cluster=None,
        loss_engine=tinh_tu_nguon,
    )
    r = tr.tool_get_waste_summary(khoang_ngay="hom_nay")
    assert "dong" not in r.data or not r.data.get("dong")
    assert r.data.get("ty_le_trung_binh") is None or r.data.get("co_du_lieu") is False
