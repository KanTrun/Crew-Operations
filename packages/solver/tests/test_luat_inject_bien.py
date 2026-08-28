"""Nhánh bỏ qua của apply_luat: luật thiếu so_nguoi, ca sai vị trí / sai khung."""

from __future__ import annotations

from typing import Any

from ca_solver.luat_inject import apply_luat
from ca_solver.model import LichInput


def _data() -> LichInput:
    return LichInput(
        nhan_vien_ids=["nv_01"],
        ca_ids=["c1"],
        phan_cong={"c1": ["nv_01"]},
        ca_meta={"c1": {"thu": "T7", "khung": "chieu", "bat_dau": "13:00", "ket_thuc": "18:00"}},
        vi_tri_can={"c1": "pha_che"},
        so_nguoi_toi_thieu={"c1": 2},
    )


def test_apply_luat_bo_qua_luat_thieu_so_nguoi() -> None:
    """Luật hiệu lực nhưng điều kiện không có so_nguoi thì không bump được gì."""
    data = _data()
    laws: list[dict[str, Any]] = [
        {"id": "luat_thieu", "trang_thai": "hieu_luc", "tham_so_loi": {"thu": "T7"}}
    ]
    out, applied = apply_luat(data, laws)
    assert applied == []
    assert out is data


def test_apply_luat_bo_qua_ca_sai_vi_tri() -> None:
    """Ca khớp thứ và khung nhưng vị trí cần khác thì không áp luật."""
    data = _data()
    laws: list[dict[str, Any]] = [
        {
            "id": "luat_thu_ngan",
            "trang_thai": "hieu_luc",
            "tham_so_loi": {
                "thu": "T7",
                "khung": "chieu",
                "vi_tri": "thu_ngan",
                "so_nguoi": 4,
            },
        }
    ]
    out, applied = apply_luat(data, laws)
    assert applied == []
    assert out.so_nguoi_toi_thieu == {"c1": 2}


def test_apply_luat_bo_qua_ca_sai_khung() -> None:
    data = _data()
    laws: list[dict[str, Any]] = [
        {
            "id": "luat_sang",
            "trang_thai": "hieu_luc",
            "tham_so_loi": {"thu": "T7", "khung": "sang", "so_nguoi": 4},
        }
    ]
    _, applied = apply_luat(data, laws)
    assert applied == []


def test_apply_luat_khong_ha_muc_toi_thieu_dang_cao_hon() -> None:
    """Luật đòi 2 người trong khi ca đã yêu cầu 2 thì không ghi nhận thay đổi."""
    data = _data()
    laws: list[dict[str, Any]] = [
        {
            "id": "luat_hai_nguoi",
            "trang_thai": "hieu_luc",
            "dieu_kien": {"thu": "T7", "so_nguoi": 2},
        }
    ]
    out, applied = apply_luat(data, laws)
    assert applied == []
    assert out.so_nguoi_toi_thieu == {"c1": 2}


def test_apply_luat_dung_dieu_kien_khi_thieu_tham_so_loi() -> None:
    """Không có tham_so_loi thì rơi về dieu_kien và vẫn bump được."""
    data = _data()
    laws: list[dict[str, Any]] = [
        {"id": "luat_dk", "trang_thai": "hieu_luc", "dieu_kien": {"thu": "T7", "so_nguoi": 5}}
    ]
    out, applied = apply_luat(data, laws)
    assert applied == ["luat_dk:c1:2->5"]
    assert out.so_nguoi_toi_thieu == {"c1": 5}
