"""Nguồn nhân viên hợp nhất (users thật + seed tùy chọn) cho solver và API.

Mặc định production: `NHIPQUAN_LOI_GIAI_SEED` TẮT — pool chỉ chứa users thật.
Dev/test/demo bật env để có lịch sử công bằng từ seed ADR-012.
"""

from __future__ import annotations

import pytest
from ca_api.nhan_vien import list_nhan_vien_ops
from ca_api.persist import register
from ca_solver.load_fixture import build_lich_input


@pytest.fixture(autouse=True)
def _seed_bat(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hầu hết test ở đây cần seed bật — test chế độ mặc định tự override."""
    monkeypatch.setenv("NHIPQUAN_LOI_GIAI_SEED", "1")


def test_mac_dinh_chi_users_that(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env tắt (mặc định production): pool chỉ có users, không seed."""
    monkeypatch.delenv("NHIPQUAN_LOI_GIAI_SEED", raising=False)
    nvs = list_nhan_vien_ops()
    nguon = {x["nguon"] for x in nvs}
    assert nguon == {"users"}, "mặc định phải chỉ dùng users thật"
    ids = {x["id"] for x in nvs}
    assert "nv_12" not in ids


def test_users_win_trung_seed() -> None:
    """Bật seed: users thắng trùng id; seed chỉ bổ sung id còn thiếu."""
    nvs = list_nhan_vien_ops()
    ids = [x["id"] for x in nvs]
    assert len(ids) == len(set(ids)), "id nhân viên bị lặp"
    assert "nv_01" in ids and "nv_02" in ids and "nv_03" in ids
    # NV seed (không trùng) vẫn đủ cho lịch sử công bằng
    assert "nv_12" in ids and "nv_25" in ids


def test_nhan_vien_dang_ky_xuat_hien_ngay() -> None:
    """Đăng ký mới → có mặt trong pool xếp lịch cùng lượt (không cần restart)."""
    before = {x["id"] for x in list_nhan_vien_ops()}
    register("testnv_moi", "matkhautot123", "Test NV Mới")
    after = {x["id"] for x in list_nhan_vien_ops()}
    new_ids = after - before
    assert new_ids, "nhân viên đăng ký không vào pool"
    moi = next(x for x in list_nhan_vien_ops() if x["id"] in new_ids)
    assert moi["nguon"] == "users"
    assert moi["ten"] == "Test NV Mới"


def test_solver_nhan_nv_that() -> None:
    """build_lich_input hợp nhất: NV ngoài + seed, không trùng, kỹ năng đủ."""
    nv_moi = {"id": "nv_99", "ten": "T", "ky_nang": ["da_nang"], "la_sinh_vien": False}
    inp = build_lich_input(nhan_vien_ngoai=[nv_moi])
    assert "nv_99" in inp.nhan_vien_ids
    assert "nv_99" in inp.ky_nang
    assert "nv_12" in inp.nhan_vien_ids
    inp2 = build_lich_input()
    assert "nv_99" not in inp2.nhan_vien_ids
