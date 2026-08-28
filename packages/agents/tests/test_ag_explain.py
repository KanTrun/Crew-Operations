"""AG-EXPLAIN — soạn câu tiếng Việt từ mã lý do, VF-NUM phải luôn qua."""

from __future__ import annotations

from ca_agents.ag_explain import MAX_MENH_DE, dien_giai
from ca_gates import validate_num
from ca_solver.explain import MA_LY_DO

CUM = MA_LY_DO


# ── Soạn câu ──────────────────────────────────────────────────────────────


def test_mot_ma_thanh_mot_menh_de() -> None:
    r = dien_giai(["KY_NANG_KHOP"], CUM)
    assert r.cau == "Người này vào ca vì có kỹ năng vị trí ca này cần."
    assert r.nguon_ma == ["KY_NANG_KHOP"]


def test_hai_ma_noi_bang_va() -> None:
    r = dien_giai(["KY_NANG_KHOP", "KHONG_TRUNG_TKB"], CUM)
    assert " và " in r.cau
    assert r.cau.count(",") == 0


def test_ba_ma_dung_phay_va_va() -> None:
    r = dien_giai(["KY_NANG_KHOP", "KHONG_TRUNG_TKB", "KHONG_NGHI_PHEP"], CUM)
    assert r.cau.count(",") == 1
    assert " và " in r.cau


def test_cat_o_max_menh_de() -> None:
    ma = ["KY_NANG_KHOP", "KHONG_TRUNG_TKB", "KHONG_NGHI_PHEP", "CON_TRAN_GIO"]
    r = dien_giai(ma, CUM, {"CON_TRAN_GIO": ["20", "48"]})
    assert len(r.nguon_ma) == MAX_MENH_DE
    assert any("vuot_max_menh_de" in b for b in r.bi_loai)


def test_khong_ma_nao_dung_duoc() -> None:
    r = dien_giai([], CUM)
    assert r.cau == "Chưa có căn cứ để diễn giải phân công này."
    assert r.nguon_ma == []


def test_ma_khong_co_cum_tu_bi_loai() -> None:
    r = dien_giai(["MA_LA"], CUM)
    assert "MA_LA:khong_co_cum_tu" in r.bi_loai
    assert r.nguon_ma == []


def test_cau_luon_ket_thuc_bang_dau_cham() -> None:
    r = dien_giai(["KY_NANG_KHOP"], CUM)
    assert r.cau.endswith(".")


def test_loai_mac_dinh() -> None:
    assert dien_giai(["KY_NANG_KHOP"], CUM).loai == "dien_giai_phan_cong"


# ── Số liệu và VF-NUM ─────────────────────────────────────────────────────


def test_gan_so_khi_duoc_phep() -> None:
    r = dien_giai(["CON_TRAN_GIO"], CUM, {"CON_TRAN_GIO": ["20", "48"]})
    assert "20/48 giờ" in r.cau


def test_bo_so_khi_khong_duoc_phep() -> None:
    r = dien_giai(
        ["CON_TRAN_GIO"],
        CUM,
        {"CON_TRAN_GIO": ["20", "48"]},
        so_lieu_cho_phep={"20"},
    )
    assert "48" not in r.cau
    assert r.nguon_ma == ["CON_TRAN_GIO"]


def test_thieu_so_thi_khong_gan_duoi() -> None:
    r = dien_giai(["CON_TRAN_GIO"], CUM, {"CON_TRAN_GIO": ["20"]})
    assert "(" not in r.cau


def test_khong_co_so_lieu_thi_cau_sach_so() -> None:
    r = dien_giai(["DU_KHOANG_NGHI"], CUM)
    assert not any(c.isdigit() for c in r.cau)


def test_vf_num_qua_khi_so_nam_trong_tap_cho_phep() -> None:
    so = {"CON_TRAN_GIO": ["20", "48"], "CA_CAN_THEM_NGUOI": ["3"]}
    r = dien_giai(["CON_TRAN_GIO", "CA_CAN_THEM_NGUOI"], CUM, so)
    g = validate_num(r.cau, {"20", "48", "3"})
    assert g.passed, g.missing


def test_vf_num_qua_ca_khi_khong_co_so() -> None:
    r = dien_giai(["KY_NANG_KHOP"], CUM)
    assert validate_num(r.cau, set()).passed


def test_moi_so_trong_cau_deu_truy_duoc() -> None:
    so = {"NO_CONG_BANG_THAP": ["7"], "DU_KHOANG_NGHI": ["12"]}
    r = dien_giai(["NO_CONG_BANG_THAP", "DU_KHOANG_NGHI"], CUM, so)
    cho_phep = {s for v in so.values() for s in v}
    assert set(r.so_lieu_dung) <= cho_phep


def test_cum_tu_co_so_bi_loai() -> None:
    """Cụm từ gốc chứa số là lỗi hợp đồng — agent phải loại, không tin."""
    r = dien_giai(["KY_NANG_KHOP"], {"KY_NANG_KHOP": "cần 2 người"})
    assert "KY_NANG_KHOP:cum_tu_co_so" in r.bi_loai
    assert r.nguon_ma == []


# ── Tất định ──────────────────────────────────────────────────────────────


def test_tat_dinh() -> None:
    ma = ["KY_NANG_KHOP", "CON_TRAN_GIO"]
    so = {"CON_TRAN_GIO": ["20", "48"]}
    assert dien_giai(ma, CUM, so).cau == dien_giai(ma, CUM, so).cau


def test_thu_tu_ma_quyet_dinh_thu_tu_menh_de() -> None:
    a = dien_giai(["KY_NANG_KHOP", "KHONG_NGHI_PHEP"], CUM)
    b = dien_giai(["KHONG_NGHI_PHEP", "KY_NANG_KHOP"], CUM)
    assert a.cau != b.cau


def test_so_lieu_cho_phep_mac_dinh_la_hop_cua_so_lieu() -> None:
    r = dien_giai(["CA_CAN_THEM_NGUOI"], CUM, {"CA_CAN_THEM_NGUOI": ["3"]})
    assert "3" in r.cau
