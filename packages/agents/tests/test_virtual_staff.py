# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit test cho Virtual Staff (Generative Agents) — plan 260918 mục 5.

ADR-002: mô phỏng tất định, không LLM.
"""

from __future__ import annotations

from ca_agents.ag_twin import simulate_virtual_staff
from ca_contracts.virtual_staff import VirtualStaffType


def _staff_rows() -> list[dict]:
    return [
        {"id": "nv_01", "ten": "Minh", "loai": "pha_che", "ky_nang": ["pha_che", "latte_art"]},
        {"id": "nv_02", "ten": "Lan", "loai": "phuc_vu", "ky_nang": ["phuc_vu"]},
    ]


def test_simulate_virtual_staff_ok() -> None:
    sim = simulate_virtual_staff(
        simulation_id="sim_1",
        kich_ban="2 người ca tối",
        staff_rows=_staff_rows(),
    )
    assert len(sim.staff) == 2
    assert sim.staff[0].loai == VirtualStaffType.PHA_CHE
    assert len(sim.su_kien) == 2
    assert "ổn định" in sim.ket_luan


def test_simulate_virtual_staff_qua_tai() -> None:
    # 1 nhân viên, 5 việc → quá tải
    sim = simulate_virtual_staff(
        simulation_id="sim_2",
        kich_ban="5 việc ca tối",
        staff_rows=[{"id": "nv_01", "ten": "Minh", "loai": "pha_che"}],
    )
    assert "quá tải" in sim.ket_luan
    assert any("quá tải" in s for s in sim.su_kien)


def test_simulate_virtual_staff_so_lan() -> None:
    sim = simulate_virtual_staff(
        simulation_id="sim_3",
        kich_ban="2 người ca tối",
        staff_rows=_staff_rows(),
        so_lan=3,
    )
    assert len(sim.su_kien) == 6  # 2 nhân viên × 3 lần