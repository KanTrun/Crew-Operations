from __future__ import annotations

from ca_solver import build_lich_input
from ca_solver.luat_inject import apply_luat


def test_apply_luat_bumps_staffing() -> None:
    data = build_lich_input()
    laws = [
        {
            "id": "luat_t7_chieu_thu_ngan",
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
    assert applied
    assert out.so_nguoi_toi_thieu.get("w1_c17", 1) >= 4


def test_skip_non_hieu_luc() -> None:
    data = build_lich_input()
    before = dict(data.so_nguoi_toi_thieu)
    luat = [{"id": "x", "trang_thai": "loai", "dieu_kien": {"so_nguoi": 9}}]
    out, applied = apply_luat(data, luat)
    assert applied == []
    assert out.so_nguoi_toi_thieu == before
