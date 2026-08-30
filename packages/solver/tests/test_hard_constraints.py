from __future__ import annotations

from typing import TypedDict

from ca_solver.model import LichInput, solve_hard_only


class _BaseParams(TypedDict):
    """Tham số lao động bắt buộc, dùng để unpack vào LichInput."""

    tran_gio_tuan: float
    khoang_nghi_gio: float


BASE: _BaseParams = {
    "tran_gio_tuan": 48.0,
    "khoang_nghi_gio": 12.0,
}


def test_requires_legal_params() -> None:
    r = solve_hard_only(LichInput(nhan_vien_ids=["nv_01"], ca_ids=[], phan_cong={}))
    assert not r.ok
    assert "config:thieu_tham_so_lao_dong" in r.violations


def test_empty_schedule_ok() -> None:
    r = solve_hard_only(LichInput(nhan_vien_ids=["nv_01"], ca_ids=[], phan_cong={}, **BASE))
    assert r.ok


def test_c02_staffing_count() -> None:
    r = solve_hard_only(
        LichInput(
            nhan_vien_ids=["nv_01"],
            ca_ids=["c1"],
            phan_cong={"c1": ["nv_01"]},
            ca_meta={"c1": {"thu": "T2", "bat_dau": "07:00", "ket_thuc": "12:00"}},
            so_nguoi_toi_thieu={"c1": 3},
            ky_nang={"nv_01": {"pha_che"}},
            vi_tri_can={"c1": "pha_che"},
            **BASE,
        )
    )
    assert any("thieu_nguoi" in v for v in r.violations)


def test_c01_tkb_conflict() -> None:
    r = solve_hard_only(
        LichInput(
            nhan_vien_ids=["nv_01"],
            ca_ids=["c1"],
            phan_cong={"c1": ["nv_01"]},
            ca_meta={"c1": {"thu": "T2", "bat_dau": "07:00", "ket_thuc": "12:00"}},
            tkb={"nv_01": [("T2", "08:00", "10:00")]},
            ky_nang={"nv_01": {"pha_che"}},
            vi_tri_can={"c1": "pha_che"},
            so_nguoi_toi_thieu={"c1": 1},
            **BASE,
        )
    )
    assert any(v.startswith("c01:") for v in r.violations)


def test_c03_double_booking() -> None:
    r = solve_hard_only(
        LichInput(
            nhan_vien_ids=["nv_01"],
            ca_ids=["c1", "c2"],
            phan_cong={"c1": ["nv_01"], "c2": ["nv_01"]},
            ca_meta={
                "c1": {"thu": "T2", "bat_dau": "07:00", "ket_thuc": "12:00"},
                "c2": {"thu": "T2", "bat_dau": "10:00", "ket_thuc": "15:00"},
            },
            so_nguoi_toi_thieu={"c1": 1, "c2": 1},
            **BASE,
        )
    )
    assert any(v.startswith("c03:") for v in r.violations)


def test_c04_rest_gap() -> None:
    r = solve_hard_only(
        LichInput(
            nhan_vien_ids=["nv_01"],
            ca_ids=["c1", "c2"],
            phan_cong={"c1": ["nv_01"], "c2": ["nv_01"]},
            ca_meta={
                "c1": {"thu": "T2", "bat_dau": "07:00", "ket_thuc": "22:00"},
                "c2": {"thu": "T3", "bat_dau": "07:00", "ket_thuc": "12:00"},
            },
            so_nguoi_toi_thieu={"c1": 1, "c2": 1},
            **BASE,
        )
    )
    assert any(v.startswith("c04:") for v in r.violations)


def test_c05_weekly_cap() -> None:
    r = solve_hard_only(
        LichInput(
            nhan_vien_ids=["nv_01"],
            ca_ids=["c1"],
            phan_cong={"c1": ["nv_01"]},
            ca_meta={"c1": {"thu": "T2", "bat_dau": "07:00", "ket_thuc": "12:00"}},
            gio_da_lam={"nv_01": 47.0},
            so_nguoi_toi_thieu={"c1": 1},
            **BASE,
        )
    )
    assert any(v.startswith("c05:") for v in r.violations)


def test_c06_leave() -> None:
    r = solve_hard_only(
        LichInput(
            nhan_vien_ids=["nv_01"],
            ca_ids=["c1"],
            phan_cong={"c1": ["nv_01"]},
            ca_meta={"c1": {"thu": "T2", "bat_dau": "07:00", "ket_thuc": "12:00"}},
            nghi_phep={("nv_01", "T2")},
            so_nguoi_toi_thieu={"c1": 1},
            **BASE,
        )
    )
    assert any(v.startswith("c06:") for v in r.violations)
