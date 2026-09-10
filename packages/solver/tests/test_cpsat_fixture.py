"""CP-SAT smoke on fixture."""

from __future__ import annotations

from ca_solver import build_lich_input, solve_cpsat, solve_hard_only


def test_cpsat_fixture_zero_hard() -> None:
    data = build_lich_input()
    r = solve_cpsat(data, time_limit_s=60.0)
    assert r.status in {"OPTIMAL", "FEASIBLE"}, r.status
    assert r.elapsed_s < 60.0
    check = solve_hard_only(
        type(data)(
            **{
                **data.__dict__,
                "phan_cong": r.phan_cong,
            }
        )
    )
    assert check.ok, check.violations


def test_cpsat_enforces_pinned_shift() -> None:
    data = build_lich_input()
    # nv_02 is Thu Ngan, free on T2 morning (nv_01 has TKB conflict on T2 morning)
    data.phan_cong["w1_c01"] = ["nv_02"]
    r = solve_cpsat(data, time_limit_s=60.0)
    assert r.ok is True
    assert "nv_02" in r.phan_cong["w1_c01"]

