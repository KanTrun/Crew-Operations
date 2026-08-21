"""Property: 8 consecutive weeks — max-debt spread does not explode."""

from __future__ import annotations

from ca_solver import build_lich_input, solve_cpsat
from ca_solver.fairness import debt_spread


def test_fairness_eight_weeks_spread_bounded() -> None:
    data = build_lich_input()
    spreads: list[float] = []
    for _ in range(8):
        r = solve_cpsat(data, time_limit_s=30.0)
        assert r.ok, r.violations[:10]
        spreads.append(debt_spread(r.debt_after))
        data.debt = r.debt_after
    # Spread must not monotonically explode; final <= 3x first (loose bound)
    assert spreads[-1] <= max(spreads[0] * 3, spreads[0] + 20), spreads
