from __future__ import annotations

from ca_gates import present_conflict, validate_num, validate_rule
from ca_playbook.vong_doi import kiem_chung, tap_su, theo_doi


def test_vf_num_rejects_invented_number() -> None:
    r = validate_num("cần 99 người", {"2", "3"})
    assert not r.passed
    assert "99" in r.missing


def test_vf_conflict() -> None:
    c = present_conflict(
        {"nguoi": "nv_01", "khung": "toi", "claim": "a"},
        {"nguoi": "nv_01", "khung": "toi", "claim": "b"},
    )
    assert c.conflict and c.khong_tu_chon


def test_vf_rule_rejects_person() -> None:
    r = validate_rule(
        {
            "loai": "ghep_ky_nang",
            "cau": "Lan lười không xếp cuối tuần",
            "dieu_kien": {"thu": "T7"},
            "bang_chung": ["1", "2", "3"],
        }
    )
    assert not r.passed
    assert r.reason == "luat_ve_nguoi"


def test_probation_and_autodisable() -> None:
    luat = {
        "cau": "x",
        "loai": "nhu_cau_ca",
        "bang_chung": ["1", "2", "3"],
        "dieu_kien": {"thu": "T7"},
    }
    luat = kiem_chung(luat)
    luat = tap_su(luat, [("x", "x")] * 4 + [("x", "y")])
    assert luat["tap_su_dung"] == 4
    luat["trang_thai"] = "hieu_luc"
    off = theo_doi(luat, dung=3, ghi_de=2)
    assert off["trang_thai"] == "tu_tat"
