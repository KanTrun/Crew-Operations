"""AG-VOC — phản hồi khách thành sự cố vận hành, nối vào việc treo."""

from __future__ import annotations

from ca_agents.ag_voc import HAN_GIO, SU_CO_VAN_HANH, VIEC_TREO, phan_loai, phan_loai_lo
from ca_gates import validate_trace

# ── Nhận sự cố vận hành ───────────────────────────────────────────────────


def test_cho_lau() -> None:
    r = phan_loai("Chờ lâu quá, gần 20 phút mới có nước")
    assert r.la_su_co_van_hanh
    assert r.loai == "cho_lau"


def test_sai_don() -> None:
    r = phan_loai("Quán giao sai món, mình gọi trà mà ra cà phê")
    assert r.loai == "sai_don"


def test_chat_luong() -> None:
    r = phan_loai("Cà phê nhạt quá")
    assert r.loai == "chat_luong"


def test_ve_sinh() -> None:
    r = phan_loai("Ly bẩn, nhìn không sạch")
    assert r.la_su_co_van_hanh
    assert r.loai == "ve_sinh"


def test_thiet_bi() -> None:
    r = phan_loai("Wifi yếu không dùng được")
    assert r.loai == "thiet_bi"


def test_phuc_vu() -> None:
    r = phan_loai("Vào quán không ai tiếp")
    assert r.loai == "phuc_vu"


def test_khong_phu_thuoc_dau() -> None:
    assert phan_loai("cho lau qua").loai == phan_loai("chờ lâu quá").loai


def test_khong_phu_thuoc_chu_hoa() -> None:
    assert phan_loai("LY BẨN").loai == "ve_sinh"


# ── Việc treo ─────────────────────────────────────────────────────────────


def test_su_co_sinh_viec_treo() -> None:
    r = phan_loai("Chờ lâu quá")
    assert r.cau_viec_treo == VIEC_TREO["cho_lau"]
    assert r.han_gio == HAN_GIO["cho_lau"]


def test_moi_ma_su_co_deu_co_viec_treo_va_han() -> None:
    for ma in SU_CO_VAN_HANH:
        assert ma in VIEC_TREO
        assert ma in HAN_GIO


def test_viec_treo_khong_neu_ten_nguoi() -> None:
    """§9.1 — cấm tuyệt đối luật hay việc nhắm vào một con người."""
    for cau in VIEC_TREO.values():
        assert "nhân viên nào" not in cau
        assert not any(t in cau for t in ("chị ", "anh ", "bạn "))


def test_ve_sinh_han_ngan_nhat() -> None:
    assert HAN_GIO["ve_sinh"] == min(HAN_GIO.values())


# ── Marketing bị loại ─────────────────────────────────────────────────────


def test_gia_ca_khong_thanh_viec_treo() -> None:
    r = phan_loai("Giá hơi đắt quá so với quán khác")
    assert not r.la_su_co_van_hanh
    assert r.loai == "marketing"
    assert r.cau_viec_treo is None


def test_khuyen_mai_la_marketing() -> None:
    assert phan_loai("Có khuyến mãi gì không").loai == "marketing"


def test_marketing_ghi_ro_ly_do_loai() -> None:
    r = phan_loai("Nên thêm món mới")
    assert r.ghi_chu == "ngoai_pham_vi_van_hanh_khong_noi_viec_treo"


def test_van_hanh_uu_tien_hon_marketing() -> None:
    """Vừa nói giá vừa báo chờ lâu — phần có người phải xử lý mới quan trọng."""
    r = phan_loai("Giá đắt mà còn chờ lâu nữa")
    assert r.la_su_co_van_hanh
    assert r.loai == "cho_lau"


# ── Không phân loại được ──────────────────────────────────────────────────


def test_phan_hoi_rong() -> None:
    r = phan_loai("")
    assert r.loai == "khong_doc_duoc"
    assert r.ghi_chu == "phan_hoi_rong"
    assert r.do_tin_cay == 0.0


def test_phan_hoi_toan_khoang_trang() -> None:
    assert phan_loai("    ").loai == "khong_doc_duoc"


def test_khong_nhan_ra_thi_day_len_nguoi() -> None:
    r = phan_loai("Hôm nay trời đẹp")
    assert not r.la_su_co_van_hanh
    assert r.loai == "chua_phan_loai_duoc"
    assert r.ghi_chu == "day_len_nguoi"


def test_khong_phan_loai_duoc_thi_khong_co_span() -> None:
    assert phan_loai("Hôm nay trời đẹp").source_span == {}


# ── VF-TRACE ──────────────────────────────────────────────────────────────


def test_su_co_co_source_span() -> None:
    r = phan_loai("Chờ lâu quá")
    assert "text_offset" in r.source_span


def test_vf_trace_qua_voi_su_co() -> None:
    text = "Nay ghé quán, chờ lâu quá"
    r = phan_loai(text)
    g = validate_trace({"source_span": r.source_span}, text)
    assert g.passed, g.reason


def test_vf_trace_qua_voi_marketing() -> None:
    text = "Giá hơi đắt quá"
    r = phan_loai(text)
    assert validate_trace({"source_span": r.source_span}, text).passed


def test_vf_trace_day_len_nguoi_khi_khong_co_span() -> None:
    r = phan_loai("Hôm nay trời đẹp")
    g = validate_trace({"source_span": r.source_span or None}, "Hôm nay trời đẹp")
    assert not g.passed
    assert g.escalate


def test_offset_tro_dung_tu_khoa() -> None:
    text = "Nay ghé quán, ly bẩn lắm"
    r = phan_loai(text)
    assert r.tu_khoa
    assert r.source_span["text_offset"] >= 0


# ── Lô ────────────────────────────────────────────────────────────────────


def test_phan_loai_lo_giu_thu_tu() -> None:
    out = phan_loai_lo(["Chờ lâu quá", "Giá đắt", "Trời đẹp"])
    assert [r.loai for r in out] == ["cho_lau", "marketing", "chua_phan_loai_duoc"]


def test_lo_rong() -> None:
    assert phan_loai_lo([]) == []


# ── Bất biến ──────────────────────────────────────────────────────────────


def test_khong_bao_gio_tra_loi_khach() -> None:
    """Agent bị cấm trả lời khách thay quán — output không có trường nào làm việc đó."""
    r = phan_loai("Chờ lâu quá")
    assert not hasattr(r, "tra_loi")
    assert not hasattr(r, "reply")


def test_tat_dinh() -> None:
    assert phan_loai("Ly bẩn").loai == phan_loai("Ly bẩn").loai


def test_do_tin_cay_su_co_cao_hon_marketing() -> None:
    assert phan_loai("Chờ lâu quá").do_tin_cay > phan_loai("Giá đắt").do_tin_cay
