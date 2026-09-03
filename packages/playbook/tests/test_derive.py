"""Tests for derive_rule_from_edits."""

from __future__ import annotations

from ca_playbook.derive import derive_rule_from_edits, sua_rows_for_mau


def _nhan_ca_rows(n: int = 3) -> list[dict]:
    rows = []
    for i in range(n):
        rows.append(
            {
                "loai": "nhan_ca",
                "truoc": {"ca_id": "w1_c10", "nv": []},
                "sau": {"ca_id": "w1_c10", "nv": [f"nv_{i + 10:02d}"]},
            }
        )
    return rows


def test_derive_from_nhan_ca() -> None:
    mau = {
        "mau": "nhan_ca",
        "loai_luat": "nhu_cau_ca",
        "n": 3,
        "bang_chung": ["0", "1", "2"],
        "nguon": "ghi_truc_tiep",
    }
    rows = _nhan_ca_rows(3)
    out = derive_rule_from_edits(mau, rows)
    assert out is not None
    assert out["dieu_kien"]["so_nguoi"] == 1
    assert "khung" in out["dieu_kien"]
    assert len(out["cau"]) > 10


def test_derive_insufficient_rows() -> None:
    mau = {"mau": "nhan_ca", "loai_luat": "nhu_cau_ca", "bang_chung": ["0", "1"]}
    assert derive_rule_from_edits(mau, _nhan_ca_rows(2)) is None


def test_sua_rows_for_mau_filters() -> None:
    rows = _nhan_ca_rows(2) + [{"loai": "nha_ca", "truoc": {}, "sau": {}}]
    mau = {"mau": "nhan_ca"}
    assert len(sua_rows_for_mau(mau, rows)) == 2
