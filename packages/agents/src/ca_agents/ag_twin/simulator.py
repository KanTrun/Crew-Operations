"""AG-TWIN — Digital Twin: mô phỏng "nếu... thì..." (plan mục 2.2, Phase 3).

Dùng math_layer (ADR-002) để tính kết quả mô phỏng. Không gọi LLM/network/DB.
Kịch bản v1.0: tăng/giảm giá, thêm/bớt nhân sự, đổi giờ mở cửa.
"""

from __future__ import annotations

from ca_contracts.ops_predict import TwinScenario, TwinScenarioType

from ca_agents.ag_predict.math_layer import (
    doanh_thu_moi,
    loi_nhuan_them_nhan_su,
    price_elasticity,
)


def _simulate_tang_gia(tham_so: dict[str, object]) -> dict[str, object]:
    """Tăng giá → ước tính doanh thu mới (độ co giãn giá)."""
    gia_cu = float(tham_so.get("gia_cu", 0))
    gia_moi = float(tham_so.get("gia_moi", 0))
    luong_cu = float(tham_so.get("luong_ban_cu", 0))
    chi_phi = float(tham_so.get("chi_phi_bien_doi", 0))
    he_so = float(tham_so.get("he_so_co_gian", -0.5))

    luong_moi = price_elasticity(gia_cu, gia_moi, luong_cu, he_so)
    doanh_thu = doanh_thu_moi(gia_moi, luong_moi, chi_phi)
    doanh_thu_cu = doanh_thu_moi(gia_cu, luong_cu, chi_phi)
    chenh_lech = doanh_thu - doanh_thu_cu
    return {
        "luong_ban_moi": luong_moi,
        "doanh_thu_moi": doanh_thu,
        "doanh_thu_cu": doanh_thu_cu,
        "chenh_lech": chenh_lech,
        "rui_ro": "Có thể mất khách nếu độ co giãn thực tế cao hơn dự kiến",
    }


def _simulate_them_nhan_su(tham_so: dict[str, object]) -> dict[str, object]:
    """Thêm nhân sự → ước tính lợi nhuận ròng."""
    doanh_thu_tang = float(tham_so.get("doanh_thu_tang_them", 0))
    chi_phi = float(tham_so.get("chi_phi_nhan_su", 0))
    loi_nhuan = loi_nhuan_them_nhan_su(doanh_thu_tang, chi_phi)
    return {
        "loi_nhuan_rong": loi_nhuan,
        "doanh_thu_tang_them": doanh_thu_tang,
        "chi_phi_nhan_su": chi_phi,
        "rui_ro": "Nếu doanh thu tăng thêm thấp hơn dự kiến, thêm nhân sự sẽ lỗ",
    }


def _simulate_doi_gio_mo_cua(tham_so: dict[str, object]) -> dict[str, object]:
    """Đổi giờ mở cửa → ước tính doanh thu mất/được."""
    doanh_thu_gio_dong = float(tham_so.get("doanh_thu_gio_dong", 0))
    doanh_thu_gio_mo = float(tham_so.get("doanh_thu_gio_mo", 0))
    chenh_lech = doanh_thu_gio_mo - doanh_thu_gio_dong
    return {
        "chenh_lech": chenh_lech,
        "doanh_thu_gio_dong": doanh_thu_gio_dong,
        "doanh_thu_gio_mo": doanh_thu_gio_mo,
        "rui_ro": "Ước tính dựa trên lịch sử giờ cao điểm, có thể sai lệch",
    }


def simulate_scenario(
    scenario_id: str,
    loai: TwinScenarioType,
    tham_so: dict[str, object],
    baseline: dict[str, object] | None = None,
) -> TwinScenario:
    """Chạy mô phỏng một kịch bản "nếu... thì..." (tất định)."""
    if loai in (TwinScenarioType.TANG_GIA, TwinScenarioType.GIAM_GIA):
        ket_qua = _simulate_tang_gia(tham_so)
    elif loai in (TwinScenarioType.THEM_NHAN_SU, TwinScenarioType.BOT_NHAN_SU):
        ket_qua = _simulate_them_nhan_su(tham_so)
    elif loai == TwinScenarioType.DOI_GIO_MO_CUA:
        ket_qua = _simulate_doi_gio_mo_cua(tham_so)
    else:
        ket_qua = {"rui_ro": "Kịch bản chưa hỗ trợ"}

    rui_ro = str(ket_qua.pop("rui_ro", ""))
    return TwinScenario(
        scenario_id=scenario_id,
        loai=loai,
        tham_so=tham_so,
        baseline=baseline or {},
        ket_qua=ket_qua,
        rui_ro=rui_ro,
    )