"""AG-BRIEF — bản tin sáng tối đa 5 câu, mọi số phải truy được."""

from __future__ import annotations

from ca_agents.ag_brief import MAX_CAU, UU_TIEN_LOAI, Fact, viet_ban_tin
from ca_gates import validate_num


def _f(loai: str, cau: str, so: list[str] | None = None, uu: int | None = None) -> Fact:
    return Fact(loai=loai, cau=cau, so_lieu=so or [], uu_tien=uu)


# ── Trần 5 câu ────────────────────────────────────────────────────────────


def test_tran_mac_dinh_la_nam() -> None:
    assert MAX_CAU == 5


def test_cat_con_nam_cau() -> None:
    facts = [_f("phieu_chua_xong", f"Câu {i}", [str(i)]) for i in range(1, 9)]
    r = viet_ban_tin(facts)
    assert len(r.cac_cau) == 5
    assert sum("vuot_tran" in b for b in r.bi_loai) == 3


def test_tran_tuy_chinh() -> None:
    facts = [_f("phieu_chua_xong", f"Câu {i}", [str(i)]) for i in range(1, 5)]
    assert len(viet_ban_tin(facts, max_cau=2).cac_cau) == 2


def test_duoi_tran_giu_nguyen() -> None:
    r = viet_ban_tin([_f("ve_sinh", "Quán sạch"), _f("thiet_bi", "Máy ổn")])
    assert len(r.cac_cau) == 2


# ── Không có dữ kiện ──────────────────────────────────────────────────────


def test_khong_du_kien_tra_cau_trung_tinh() -> None:
    r = viet_ban_tin([])
    assert r.cac_cau == ["Sáng nay không có việc nào cần chủ quán để ý."]
    assert r.nguon_loai == ["khong_co_du_kien"]


def test_cau_rong_bi_loai() -> None:
    r = viet_ban_tin([_f("ve_sinh", "   ")])
    assert "ve_sinh:cau_rong" in r.bi_loai
    assert r.nguon_loai == ["khong_co_du_kien"]


# ── Ưu tiên ───────────────────────────────────────────────────────────────


def test_viec_treo_qua_han_len_dau() -> None:
    r = viet_ban_tin(
        [
            _f("phieu_chua_xong", "Phiếu chưa xong"),
            _f("viec_treo_qua_han", "Việc treo quá hạn"),
        ]
    )
    assert r.nguon_loai[0] == "viec_treo_qua_han"


def test_dau_hieu_bat_thuong_truoc_ton_kho() -> None:
    r = viet_ban_tin([_f("ton_duoi_nguong", "Sữa ít"), _f("dau_hieu_bat_thuong", "Có dấu hiệu")])
    assert r.nguon_loai == ["dau_hieu_bat_thuong", "ton_duoi_nguong"]


def test_uu_tien_tu_khai_thang_bang_mac_dinh() -> None:
    r = viet_ban_tin([_f("viec_treo_qua_han", "Treo"), _f("phieu_chua_xong", "Phiếu", uu=1)])
    assert r.nguon_loai[0] == "phieu_chua_xong"


def test_loai_la_xuong_cuoi() -> None:
    r = viet_ban_tin([_f("loai_khong_biet", "Lạ"), _f("viec_treo_qua_han", "Treo")])
    assert r.nguon_loai[-1] == "loai_khong_biet"


def test_bang_uu_tien_day_du() -> None:
    assert UU_TIEN_LOAI["viec_treo_qua_han"] < UU_TIEN_LOAI["luat_cho_duyet"]


# ── VF-NUM ────────────────────────────────────────────────────────────────


def test_loai_cau_co_so_khong_chung_minh_duoc() -> None:
    r = viet_ban_tin([_f("ton_duoi_nguong", "Sữa còn 4 hộp", [])])
    assert r.cac_cau == ["Sáng nay không có việc nào cần chủ quán để ý."]
    assert any("so_khong_co_trong_du_lieu" in b for b in r.bi_loai)


def test_giu_cau_khi_so_chung_minh_duoc() -> None:
    r = viet_ban_tin([_f("ton_duoi_nguong", "Sữa còn 4 hộp", ["4"])])
    assert "Sữa còn 4 hộp." in r.cac_cau


def test_vf_num_qua_tren_toan_ban_tin() -> None:
    facts = [
        _f("viec_treo_qua_han", "Có 3 việc treo quá hạn", ["3"]),
        _f("ton_duoi_nguong", "Sữa còn 4 hộp", ["4"]),
    ]
    r = viet_ban_tin(facts)
    assert validate_num(r.van_ban, {"3", "4"}).passed


def test_so_thap_phan_dung_dau_phay() -> None:
    r = viet_ban_tin([_f("ton_duoi_nguong", "Còn 4,5 kg", ["4.5"])])
    assert "4,5" in r.van_ban


# ── Định dạng ─────────────────────────────────────────────────────────────


def test_tu_them_dau_cham() -> None:
    r = viet_ban_tin([_f("ve_sinh", "Quán sạch")])
    assert r.cac_cau == ["Quán sạch."]


def test_giu_dau_cau_da_co() -> None:
    r = viet_ban_tin([_f("ve_sinh", "Quán sạch!")])
    assert r.cac_cau == ["Quán sạch!"]


def test_van_ban_noi_bang_khoang_trang() -> None:
    r = viet_ban_tin([_f("viec_treo_qua_han", "A"), _f("dau_hieu_bat_thuong", "B")])
    assert r.van_ban == "A. B."


def test_cung_uu_tien_thi_tie_break_theo_ten_loai() -> None:
    """Hai loại lạ cùng ưu tiên 99 — xếp theo tên loại để kết quả tất định."""
    r = viet_ban_tin([_f("ve_sinh", "A"), _f("thiet_bi", "B")])
    assert r.nguon_loai == ["thiet_bi", "ve_sinh"]
    assert r.van_ban == "B. A."


def test_loai_mac_dinh() -> None:
    assert viet_ban_tin([]).loai == "ban_tin_sang"


# ── Tất định ──────────────────────────────────────────────────────────────


def test_tat_dinh_cung_dau_vao_cung_ban_tin() -> None:
    facts = [_f("ton_duoi_nguong", "Sữa 4", ["4"]), _f("ve_sinh", "Sạch")]
    assert viet_ban_tin(facts).cac_cau == viet_ban_tin(facts).cac_cau


def test_thu_tu_dau_vao_khong_doi_ket_qua() -> None:
    a = _f("ton_duoi_nguong", "Sữa 4", ["4"])
    b = _f("viec_treo_qua_han", "Treo")
    assert viet_ban_tin([a, b]).cac_cau == viet_ban_tin([b, a]).cac_cau
