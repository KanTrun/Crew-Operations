from __future__ import annotations

from dataclasses import dataclass, field

from ca_solver.constraints import c01, c02, c03, c04, c05, c06


@dataclass
class LichInput:
    """Schedule payload for hard checkers + CP-SAT."""

    nhan_vien_ids: list[str]
    ca_ids: list[str]
    phan_cong: dict[str, list[str]]  # ca_id -> nhan_vien_ids
    tkb: dict[str, list[tuple[str, str, str]]] = field(default_factory=dict)
    ca_meta: dict[str, dict[str, str]] = field(default_factory=dict)
    ky_nang: dict[str, set[str]] = field(default_factory=dict)
    vi_tri_can: dict[str, str] = field(default_factory=dict)
    so_nguoi_toi_thieu: dict[str, int] = field(default_factory=dict)
    nghi_phep: set[tuple[str, str]] = field(default_factory=set)
    gio_da_lam: dict[str, float] = field(default_factory=dict)
    tran_gio_tuan: float = 0.0
    khoang_nghi_gio: float = 0.0
    # Fairness debt balances (4 axes) — ADR-005
    debt: dict[str, dict[str, float]] = field(default_factory=dict)
    soft_enabled: bool = True
    soft_count: int = 5  # cut to 3 + ADR if mốc trượt


@dataclass
class SolveResult:
    ok: bool
    violations: list[str] = field(default_factory=list)
    phan_cong: dict[str, list[str]] = field(default_factory=dict)
    elapsed_s: float = 0.0
    status: str = ""
    objective: int | None = None
    debt_after: dict[str, dict[str, float]] = field(default_factory=dict)


HARD = (c01, c02, c03, c04, c05, c06)


def solve_hard_only(data: LichInput) -> SolveResult:
    if data.tran_gio_tuan <= 0 or data.khoang_nghi_gio <= 0:
        return SolveResult(
            ok=False,
            violations=["config:thieu_tham_so_lao_dong"],
        )
    violations: list[str] = []
    for mod in HARD:
        violations.extend(mod.check(data))
    return SolveResult(
        ok=len(violations) == 0,
        violations=violations,
        phan_cong=dict(data.phan_cong),
    )
