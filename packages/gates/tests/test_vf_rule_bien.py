"""Nhánh từ chối (fail-closed) của cổng VF-RULE."""

from __future__ import annotations

from typing import Any

from ca_gates.vf_rule import validate_rule


def _luat_hop_le() -> dict[str, Any]:
    return {
        "loai": "nhu_cau_ca",
        "cau": "Thứ Bảy ca chiều cần 3 người pha chế",
        "dieu_kien": {"thu": "T7", "khung": "chieu", "so_nguoi": 3},
        "bang_chung": ["1", "2", "3"],
    }


def test_vf_rule_loai_khong_hop_le_bi_tu_choi() -> None:
    luat = _luat_hop_le()
    luat["loai"] = "tuy_hung"
    r = validate_rule(luat)
    assert not r.passed
    assert r.reason == "loai_khong_hop_le"


def test_vf_rule_thieu_loai_bi_tu_choi() -> None:
    """Thiếu hẳn trường 'loai' cũng rơi vào nhánh loai_khong_hop_le."""
    luat = _luat_hop_le()
    del luat["loai"]
    r = validate_rule(luat)
    assert not r.passed
    assert r.reason == "loai_khong_hop_le"
    assert r.loai == ""


def test_vf_rule_thieu_bang_chung_duoi_ba_bi_tu_choi() -> None:
    """Chỉ 2 bằng chứng là dưới ngưỡng ≥3 nên phải trượt."""
    luat = _luat_hop_le()
    luat["bang_chung"] = ["1", "2"]
    r = validate_rule(luat)
    assert not r.passed
    assert r.reason == "thieu_bang_chung"


def test_vf_rule_dung_ba_bang_chung_thi_qua() -> None:
    """Đúng biên 3 bằng chứng phải được chấp nhận."""
    r = validate_rule(_luat_hop_le())
    assert r.passed
    assert r.loai == "nhu_cau_ca"


def test_vf_rule_dieu_kien_khong_phai_dict_bi_tu_choi() -> None:
    luat = _luat_hop_le()
    luat["dieu_kien"] = ["thu=T7"]
    r = validate_rule(luat)
    assert not r.passed
    assert r.reason == "dieu_kien_khong_cau_truc"


def test_vf_rule_truong_khong_ton_tai_bi_tu_choi() -> None:
    """Điều kiện dùng trường không có trong schema phải bị chặn và nêu tên trường."""
    luat = _luat_hop_le()
    luat["dieu_kien"] = {"thu": "T7", "diem_thai_do": 5}
    r = validate_rule(luat)
    assert not r.passed
    assert r.reason.startswith("truong_khong_ton_tai:")
    assert "diem_thai_do" in r.reason


def test_vf_rule_fields_tuy_chinh_cho_phep_truong_moi() -> None:
    """Truyền fields tuỳ chỉnh thì trường ngoài DEFAULT_FIELDS vẫn hợp lệ."""
    luat = _luat_hop_le()
    luat["dieu_kien"] = {"ma_kho": "K1"}
    assert not validate_rule(luat).passed
    assert validate_rule(luat, fields={"ma_kho"}).passed
