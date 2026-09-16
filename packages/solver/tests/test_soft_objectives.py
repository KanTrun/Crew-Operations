from __future__ import annotations

from ca_solver import LichInput, solve_cpsat
from ca_solver.fairness import zero_debt


def _input(days: list[str], employees: list[str], *, need: int = 1) -> LichInput:
    shifts = [f"ca_{index}" for index in range(len(days))]
    return LichInput(
        nhan_vien_ids=employees,
        ca_ids=shifts,
        phan_cong={},
        ca_meta={
            shift: {
                "thu": day,
                "khung": "chieu",
                "bat_dau": "12:00",
                "ket_thuc": "17:00",
            }
            for shift, day in zip(shifts, days, strict=True)
        },
        so_nguoi_toi_thieu={shift: need for shift in shifts},
        tran_gio_tuan=48,
        khoang_nghi_gio=12,
        debt=zero_debt(employees),
    )


def test_s03_prefers_consecutive_work_days() -> None:
    data = _input(["T2", "T3", "T4", "T5"], ["alpha", "beta"])
    result = solve_cpsat(data)
    assert result.ok

    days_by_employee: dict[str, list[int]] = {"alpha": [], "beta": []}
    for index, shift in enumerate(data.ca_ids):
        days_by_employee[result.phan_cong[shift][0]].append(index)
    assert all(len(days) == 2 for days in days_by_employee.values())
    assert all(days[1] - days[0] == 1 for days in days_by_employee.values())


def test_s04_prefers_previous_assignment() -> None:
    data = _input(["T4"], ["alpha", "beta"])
    data.phan_cong_tuan_truoc = {"ca_0": ["beta"]}
    result = solve_cpsat(data)
    assert result.ok
    assert result.phan_cong["ca_0"] == ["beta"]


def test_s05_pairs_experienced_and_new_staff() -> None:
    data = _input(["T4"], ["senior_a", "senior_b", "new_a", "new_b"], need=2)
    data.nhan_vien_kinh_nghiem = {"senior_a", "senior_b"}
    result = solve_cpsat(data)
    assert result.ok
    assigned = set(result.phan_cong["ca_0"])
    assert assigned & data.nhan_vien_kinh_nghiem
    assert assigned - data.nhan_vien_kinh_nghiem
