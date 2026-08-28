"""CP-SAT weekly roster — hard c01–c06 + soft penalties + minimize max debt."""

from __future__ import annotations

import time
from collections import defaultdict

from ortools.sat.python import cp_model

from ca_solver.constraints import soft as soft_mod
from ca_solver.fairness import AXES, update_debt_from_assignment
from ca_solver.model import LichInput, SolveResult, solve_hard_only

_THU_ORD = {"T2": 0, "T3": 1, "T4": 2, "T5": 3, "T6": 4, "T7": 5, "CN": 6}


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _overlap(a0: str, a1: str, b0: str, b1: str) -> bool:
    return _to_min(a0) < _to_min(b1) and _to_min(b0) < _to_min(a1)


def _duration_h(meta: dict[str, str]) -> float:
    return (_to_min(meta["ket_thuc"]) - _to_min(meta["bat_dau"])) / 60.0


def _abs_min(meta: dict[str, str], moc: str) -> int | None:
    """Phút tuyệt đối trong tuần. None nếu `thu` không nằm trong lịch tuần."""
    thu = meta["thu"]
    if thu not in _THU_ORD:
        return None
    return _THU_ORD[thu] * 24 * 60 + _to_min(meta[moc])


def _vi_pham_khoang_nghi(
    ma: dict[str, str], mb: dict[str, str], khoang_nghi_gio: float
) -> bool:
    """c04 — hai ca có khoảng nghỉ ngắn hơn mức cấu hình.

    Tách thành hàm riêng để mốc thời gian không dùng chung tên biến với
    vòng lặp miền giá trị ở `solve_cpsat`.
    """
    moc = (
        _abs_min(ma, "bat_dau"),
        _abs_min(ma, "ket_thuc"),
        _abs_min(mb, "bat_dau"),
        _abs_min(mb, "ket_thuc"),
    )
    if any(m is None for m in moc):
        return False
    a_dau, a_cuoi, b_dau, b_cuoi = (int(m) for m in moc if m is not None)
    if a_dau > b_dau:
        a_dau, a_cuoi, b_dau, b_cuoi = b_dau, b_cuoi, a_dau, a_cuoi
    gap = b_dau - a_cuoi
    return 0 <= gap < khoang_nghi_gio * 60


def solve_cpsat(data: LichInput, *, time_limit_s: float = 60.0) -> SolveResult:
    if data.tran_gio_tuan <= 0 or data.khoang_nghi_gio <= 0:
        return SolveResult(ok=False, violations=["config:thieu_tham_so_lao_dong"])

    model = cp_model.CpModel()
    nvs = data.nhan_vien_ids
    cas = data.ca_ids
    x: dict[tuple[str, str], cp_model.IntVar] = {}

    # Domain: skill + TKB + leave → only create feasible vars
    for ca in cas:
        meta = data.ca_meta[ca]
        can_ky_nang = data.vi_tri_can.get(ca)
        thu = meta["thu"]
        for nv in nvs:
            if can_ky_nang and can_ky_nang not in data.ky_nang.get(nv, set()):
                continue
            if (nv, thu) in data.nghi_phep:
                continue
            conflict = False
            for block in data.tkb.get(nv, []):
                b_thu, b0, b1 = block
                if b_thu == thu and _overlap(meta["bat_dau"], meta["ket_thuc"], b0, b1):
                    conflict = True
                    break
            if conflict:
                continue
            x[nv, ca] = model.new_bool_var(f"x_{nv}_{ca}")

    # c02 staffing count (exact minimum for tightness)
    for ca in cas:
        need_n = data.so_nguoi_toi_thieu.get(ca, 1)
        vars_ca = [x[nv, ca] for nv in nvs if (nv, ca) in x]
        if len(vars_ca) < need_n:
            return SolveResult(
                ok=False,
                violations=[f"c02:{ca}:khong_du_ung_vien:{len(vars_ca)}<{need_n}"],
                status="INFEASIBLE_DOMAIN",
            )
        model.add(sum(vars_ca) == need_n)

    # c03 no overlap same day; c04 rest gap
    for nv in nvs:
        nv_cas = [ca for ca in cas if (nv, ca) in x]
        for i, a in enumerate(nv_cas):
            ma = data.ca_meta[a]
            for b in nv_cas[i + 1 :]:
                mb = data.ca_meta[b]
                # c03 — cùng ngày, giờ chồng nhau
                if ma["thu"] == mb["thu"] and _overlap(
                    ma["bat_dau"], ma["ket_thuc"], mb["bat_dau"], mb["ket_thuc"]
                ):
                    model.add_bool_or([x[nv, a].Not(), x[nv, b].Not()])
                # c04 — khoảng nghỉ giữa hai ca liền nhau
                if _vi_pham_khoang_nghi(ma, mb, data.khoang_nghi_gio):
                    model.add_bool_or([x[nv, a].Not(), x[nv, b].Not()])

    # c05 weekly hours
    for nv in nvs:
        terms = []
        for ca in cas:
            if (nv, ca) not in x:
                continue
            dur_tenths = int(round(_duration_h(data.ca_meta[ca]) * 10))
            terms.append(x[nv, ca] * dur_tenths)
        if terms:
            base = int(round(data.gio_da_lam.get(nv, 0) * 10))
            model.add(sum(terms) + base <= int(data.tran_gio_tuan * 10))

    # Objective: soft penalties + fairness max-debt
    obj_terms: list[cp_model.LinearExpr] = []
    soft_ids = soft_mod.soft_ids(data.soft_count if data.soft_enabled else 0)

    # s02: penalize weekend/night stacking for high-debt people (proxy)
    if "s02" in soft_ids:
        for nv, ca in x:
            m = data.ca_meta[ca]
            weekend = m["thu"] in {"T7", "CN"}
            night = m.get("khung") == "toi"
            if weekend or night:
                w = soft_mod.W_S02_WEEKEND_NIGHT
                # prefer assigning low cuoi_tuan/dem debt
                bal = data.debt.get(nv, {})
                bias = int(bal.get("cuoi_tuan", 0) + bal.get("dem", 0))
                obj_terms.append(x[nv, ca] * (w + bias))

    # s01: prefer even ids for sang (synthetic nguyện vọng)
    if "s01" in soft_ids:
        for nv, ca in x:
            if data.ca_meta[ca].get("khung") == "sang" and nv.endswith(
                ("0", "2", "4", "6", "8")
            ):
                obj_terms.append(x[nv, ca] * (-soft_mod.W_S01_NGUYEN_VONG))

    # s05: prefer pairing experienced (even) with newbie (odd) on same ca — soft bonus
    if "s05" in soft_ids:
        for ca in cas:
            odds = [x[nv, ca] for nv in nvs if (nv, ca) in x and nv[-1] in "13579"]
            evens = [x[nv, ca] for nv in nvs if (nv, ca) in x and nv[-1] in "02468"]
            if odds and evens:
                both = model.new_bool_var(f"pair_{ca}")
                # both => at least one odd and one even (approx via sum)
                # Maximize both: add negative cost when both active — use hint via sums
                # Simplified: penalize all-odd or all-even via linear proxy skipped for KISS
                _ = both  # reserved for future

    # Fairness: minimize max over axes of (prior + new load) — scaled integers
    scale = 10
    max_d = model.new_int_var(0, 10_000, "max_debt")
    for nv in nvs:
        for axis in AXES:
            prior = int(round(data.debt.get(nv, {}).get(axis, 0) * scale))
            add_terms = []
            for ca in cas:
                if (nv, ca) not in x:
                    continue
                m = data.ca_meta[ca]
                hours = _duration_h(m)
                weekend = m["thu"] in {"T7", "CN"}
                night = m.get("khung") == "toi"
                add = 0
                if axis == "cuoi_tuan" and weekend:
                    add = scale
                elif axis == "dem" and night:
                    add = scale
                elif axis == "gio":
                    add = int(round(hours * scale))
                elif axis == "vun" and hours < 5:
                    add = scale
                if add:
                    add_terms.append(x[nv, ca] * add)
            if add_terms:
                model.add(prior + sum(add_terms) <= max_d)
            else:
                model.add(prior <= max_d)

    # Primary: max_d; secondary: soft
    # CP-SAT single objective: weight max_d heavily
    model.minimize(max_d * 1000 + sum(obj_terms) if obj_terms else max_d * 1000)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers = 8
    t0 = time.perf_counter()
    status = solver.Solve(model)
    elapsed = time.perf_counter() - t0

    status_name = solver.StatusName(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return SolveResult(
            ok=False,
            violations=[f"solver:{status_name}"],
            elapsed_s=elapsed,
            status=status_name,
        )

    phan_cong: dict[str, list[str]] = defaultdict(list)
    for (nv, ca), var in x.items():
        if solver.Value(var) == 1:
            phan_cong[ca].append(nv)
    # ensure all ca keys present
    for ca in cas:
        phan_cong.setdefault(ca, [])

    assigned = LichInput(
        nhan_vien_ids=data.nhan_vien_ids,
        ca_ids=data.ca_ids,
        phan_cong=dict(phan_cong),
        tkb=data.tkb,
        ca_meta=data.ca_meta,
        ky_nang=data.ky_nang,
        vi_tri_can=data.vi_tri_can,
        so_nguoi_toi_thieu=data.so_nguoi_toi_thieu,
        nghi_phep=data.nghi_phep,
        gio_da_lam=data.gio_da_lam,
        tran_gio_tuan=data.tran_gio_tuan,
        khoang_nghi_gio=data.khoang_nghi_gio,
        debt=data.debt,
    )
    check = solve_hard_only(assigned)
    debt_after = update_debt_from_assignment(data.debt, dict(phan_cong), data.ca_meta)
    return SolveResult(
        ok=check.ok,
        violations=check.violations,
        phan_cong=dict(phan_cong),
        elapsed_s=elapsed,
        status=status_name,
        objective=(
            int(solver.ObjectiveValue())
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
            else None
        ),
        debt_after=debt_after,
    )
