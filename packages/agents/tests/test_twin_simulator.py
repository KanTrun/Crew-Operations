"""Unit test cho AG-TWIN simulator (plan 260918 mục 2.2, Phase 3).

ADR-002: mô phỏng tất định, cùng input → cùng output.
"""

from __future__ import annotations

import math

from ca_agents.ag_twin.simulator import simulate_scenario
from ca_contracts.ops_predict import TwinScenarioType


def test_simulate_tang_gia() -> None:
    sc = simulate_scenario(
        scenario_id="sc_1",
        loai=TwinScenarioType.TANG_GIA,
        tham_so={
            "gia_cu": 25000,
            "gia_moi": 30000,
            "luong_ban_cu": 100,
            "chi_phi_bien_doi": 50000,
            "he_so_co_gian": -0.5,
        },
    )
    # Lượng mới = 100 * (1 + (-0.5)*(0.2)) = 90
    assert math.isclose(sc.ket_qua["luong_ban_moi"], 90.0, rel_tol=1e-6)
    # Doanh thu mới = 30000*90 - 50000 = 2650000
    assert math.isclose(sc.ket_qua["doanh_thu_moi"], 2650000.0, rel_tol=1e-6)
    assert sc.rui_ro != ""


def test_simulate_them_nhan_su() -> None:
    sc = simulate_scenario(
        scenario_id="sc_2",
        loai=TwinScenarioType.THEM_NHAN_SU,
        tham_so={"doanh_thu_tang_them": 200000, "chi_phi_nhan_su": 150000},
    )
    assert math.isclose(sc.ket_qua["loi_nhuan_rong"], 50000.0, rel_tol=1e-6)


def test_simulate_doi_gio_mo_cua() -> None:
    sc = simulate_scenario(
        scenario_id="sc_3",
        loai=TwinScenarioType.DOI_GIO_MO_CUA,
        tham_so={"doanh_thu_gio_dong": 100000, "doanh_thu_gio_mo": 150000},
    )
    assert math.isclose(sc.ket_qua["chenh_lech"], 50000.0, rel_tol=1e-6)


def test_simulate_unsupported() -> None:
    sc = simulate_scenario(
        scenario_id="sc_4",
        loai=TwinScenarioType.GIAM_GIA,
        tham_so={},
    )
    assert "rui_ro" in sc.ket_qua or sc.rui_ro != ""