"""Test cho `scraper_selectors.py` — nguồn duy nhất của selector bên thứ ba.

File này nằm TRONG test suite chặn merge, còn canary thì KHÔNG. Lý do tách đôi:

- Canary dò trang thật nên có thể đỏ vì mạng, vì Google chặn IP của runner, vì
  camoufox chưa cài — không thứ nào trong số đó là lỗi của repo, nên nó không được
  phép chặn release (plan `260913-1455` mục 7).
- Còn NHỮNG GÌ Ở ĐÂY thì ngược lại: scraper và canary có đang đọc cùng một danh
  sách selector không, luật xếp mức có đúng không — đó là lỗi của repo, phải đỏ
  ngay trong CI.

Ba nhóm test:
1. Scraper và canary không lệch nhau (không ai chép lại selector của ai).
2. Luật xếp mức canary đúng — hàm thuần, không cần trình duyệt.
3. Cấu trúc dữ liệu không tự mâu thuẫn (nhóm thay thế phải nằm trong danh sách dò).
"""

from __future__ import annotations

import pathlib
import re

import pytest
from ca_agents.sources import gmaps_menu_source
from ca_agents.sources.scraper_selectors import (
    CAC_NGUON,
    DAU_HIEU_BI_CHAN,
    GMAPS_NGUON,
    GMAPS_SEL_ANH_TRONG_VUNG,
    GMAPS_SEL_KHUNG_KET_QUA,
    GMAPS_SEL_NUT_TAT_CA_ANH,
    GMAPS_SEL_NUT_THUC_DON,
    GMAPS_SEL_RATING,
    GMAPS_SEL_SO_REVIEW,
    GMAPS_SEL_TEN_QUAN,
    MUC_DO,
    MUC_KHONG_CHAY,
    MUC_VANG,
    MUC_XANH,
    SHOPEEFOOD_NGUON,
    NguonCanary,
    selector_can_do,
    tim_dau_hieu_chan,
    xep_muc_chung,
    xep_muc_nguon,
)

_NGUON_GIA = NguonCanary(
    ma="gia",
    ten="Nguồn giả để test luật xếp mức",
    url_mau="https://example.invalid/tim-kiem",
    selector_bat_buoc=("#bat-buoc",),
    selector_tuy_chon=("#phu-a", "#phu-b"),
    selector_nhom_it_nhat_mot=(("#duong-1", "#duong-2"),),
)


def _dem(**gia_tri: int) -> dict[str, int]:
    """Kết quả đếm mặc định: mọi selector đều tìm thấy, rồi ghi đè theo `gia_tri`."""
    mac_dinh = {s: 5 for s in selector_can_do(_NGUON_GIA)}
    mac_dinh.update(gia_tri)
    return mac_dinh


# ── 1. Scraper và canary đọc cùng một selector ────────────────────────────────


def test_scraper_dung_dung_selector_da_khai_bao() -> None:
    """`gmaps_menu_source` phải trỏ vào selector trong `scraper_selectors`.

    Nếu ai đó dán lại chuỗi selector thẳng vào scraper thì canary vẫn xanh trong khi
    scraper đã mù — đúng cái lỗ hổng mà việc tách file này sinh ra để bịt.
    """
    assert gmaps_menu_source._SEL_KHUNG_KET_QUA == GMAPS_SEL_KHUNG_KET_QUA
    assert gmaps_menu_source._SEL_TEN_QUAN == GMAPS_SEL_TEN_QUAN
    assert gmaps_menu_source._SEL_NUT_THUC_DON == GMAPS_SEL_NUT_THUC_DON
    assert gmaps_menu_source._SEL_NUT_TAT_CA_ANH == GMAPS_SEL_NUT_TAT_CA_ANH
    assert gmaps_menu_source._SEL_ANH_TRONG_VUNG == GMAPS_SEL_ANH_TRONG_VUNG
    assert gmaps_menu_source._SEL_RATING == GMAPS_SEL_RATING
    assert gmaps_menu_source._SEL_SO_REVIEW == GMAPS_SEL_SO_REVIEW


def test_scraper_khong_con_chuoi_selector_cung() -> None:
    """Không được khai báo selector chữ trong file scraper — chỉ được import."""
    nguon = pathlib.Path(gmaps_menu_source.__file__).read_text(encoding="utf-8")
    # Bỏ phần import để không tự bắt chính các tên hằng số được import vào.
    than_file = nguon.split("logger = logging.getLogger", 1)[-1]
    trung_voi_selectors = [
        selector
        for selector in selector_can_do(GMAPS_NGUON)
        if selector and f'"{selector}"' in than_file
    ]
    assert not trung_voi_selectors, (
        f"gmaps_menu_source.py khai báo lại selector thay vì import: {trung_voi_selectors}"
    )


def test_scraper_va_canary_dung_chung_dinh_nghia_bi_chan() -> None:
    """Scraper phải dùng `DAU_HIEU_BI_CHAN`, không tự liệt kê từ khóa riêng."""
    nguon = pathlib.Path(gmaps_menu_source.__file__).read_text(encoding="utf-8")
    assert "DAU_HIEU_BI_CHAN" in nguon
    for tu_khoa in ("captcha", "unusual traffic"):
        assert f'"{tu_khoa}"' not in nguon, (
            f"gmaps_menu_source.py còn hard-code từ khóa '{tu_khoa}' — "
            "scraper và canary sẽ lệch định nghĩa 'bị chặn'"
        )


def test_moi_nguon_canary_co_du_truong_de_chay() -> None:
    """Canary cần `ma`, `ten`, `url_mau` để in báo cáo; thiếu là báo cáo vô nghĩa."""
    assert CAC_NGUON, "CAC_NGUON rỗng thì canary không dò gì cả"
    for nguon in CAC_NGUON:
        assert nguon.ma and nguon.ten
        assert nguon.url_mau.startswith("http")
        assert nguon.ma in {GMAPS_NGUON.ma, SHOPEEFOOD_NGUON.ma}


def test_ma_nguon_khong_trung_nhau() -> None:
    """`ma` là khóa để đối chiếu báo cáo canary với thống kê block của scraper."""
    cac_ma = [nguon.ma for nguon in CAC_NGUON]
    assert len(cac_ma) == len(set(cac_ma)), f"trùng mã nguồn: {cac_ma}"


def test_selector_can_do_khu_trung_lap() -> None:
    """Selector trùng thì `so_phan_tu_tim_thay` (dict) tự ghi đè, mất bằng chứng đếm."""
    nguon = NguonCanary(
        ma="trung",
        ten="Nguồn khai báo trùng selector",
        url_mau="https://example.invalid",
        selector_bat_buoc=("#a",),
        selector_tuy_chon=("#a", "#b"),
        selector_nhom_it_nhat_mot=(("#b", "#c"),),
    )
    assert selector_can_do(nguon) == ("#a", "#b", "#c")


def test_selector_can_do_giu_nguyen_selector_cua_nguon_that() -> None:
    """Nguồn thật không khai trùng, nên danh sách dò phải đủ cả 7 selector của GMAPS."""
    assert set(selector_can_do(GMAPS_NGUON)) == {
        GMAPS_SEL_KHUNG_KET_QUA,
        GMAPS_SEL_TEN_QUAN,
        GMAPS_SEL_NUT_THUC_DON,
        GMAPS_SEL_NUT_TAT_CA_ANH,
        GMAPS_SEL_ANH_TRONG_VUNG,
        GMAPS_SEL_RATING,
        GMAPS_SEL_SO_REVIEW,
    }


def test_selector_bat_buoc_khong_nam_trong_nhom_thay_the() -> None:
    """Một selector không thể vừa là bắt buộc vừa là nhánh thay thế được.

    Bắt buộc nghĩa là mất nó là ĐỎ; nằm trong nhóm nghĩa là mất nó vẫn có thể VÀNG.
    Khai báo cả hai là mâu thuẫn, và `xep_muc_nguon` sẽ cho kết quả tùy thứ tự if.
    """
    for nguon in CAC_NGUON:
        trong_nhom = {s for nhom in nguon.selector_nhom_it_nhat_mot for s in nhom}
        xung_dot = set(nguon.selector_bat_buoc) & trong_nhom
        assert not xung_dot, f"{nguon.ma}: {xung_dot} vừa bắt buộc vừa trong nhóm thay thế"


def test_moi_nhom_thay_the_deu_duoc_dem() -> None:
    """Nhóm không nằm trong `selector_can_do` sẽ bị kết luận là CHẾT oan.

    `so_phan_tu.get(s, 0)` trả 0 cho selector chưa từng đếm, mà 0 == "mất".
    """
    for nguon in CAC_NGUON:
        can_do = set(selector_can_do(nguon))
        for nhom in nguon.selector_nhom_it_nhat_mot:
            assert nhom, f"{nguon.ma}: nhóm thay thế rỗng là khai báo thừa"
            for selector in nhom:
                assert selector in can_do, (
                    f"{nguon.ma}: selector nhóm '{selector}' không được đếm"
                )


def test_shopeefood_khong_duoc_gan_selector_dom() -> None:
    """Scraper ShopeeFood bắt response JSON, không đọc DOM.

    Gán selector DOM vào đây là tạo ra cảnh báo đỏ vĩnh viễn mà không ai sửa được,
    vì trang đó vốn không có phần tử nào khớp.
    """
    assert SHOPEEFOOD_NGUON.selector_bat_buoc == ()
    assert SHOPEEFOOD_NGUON.selector_tuy_chon == ()
    assert SHOPEEFOOD_NGUON.selector_nhom_it_nhat_mot == ()
    assert selector_can_do(SHOPEEFOOD_NGUON) == ()


def test_url_mau_gmaps_co_toa_do_va_tu_khoa() -> None:
    """URL mẫu phải là trang có quán thật, nếu không "0 kết quả" là vô nghĩa."""
    assert "cơm tấm" in GMAPS_NGUON.url_mau
    assert re.search(r"@\d+\.\d+,\d+\.\d+", GMAPS_NGUON.url_mau), (
        "URL Google Maps thiếu tọa độ — canary sẽ mở trang không định vị được khu vực"
    )


def test_dau_hieu_bi_chan_giu_nguyen_tap_scraper_dang_dung() -> None:
    """Bốn khóa đầu là hành vi scraper đã chạy thật; đổi là đổi cách phát hiện chặn."""
    for tu_khoa in ("captcha", "blocked", "forbidden", "403", "unusual traffic"):
        assert tu_khoa in DAU_HIEU_BI_CHAN
    assert all(dau == dau.lower() for dau in DAU_HIEU_BI_CHAN), (
        "từ khóa phải chữ thường — `tim_dau_hieu_chan` so trên text đã lower()"
    )


# ── 2. Luật xếp mức (hàm thuần) ───────────────────────────────────────────────


def test_tim_dau_hieu_chan_khong_phan_biet_hoa_thuong() -> None:
    assert tim_dau_hieu_chan("Xin lỗi, CAPTCHA required") == ["captcha"]
    assert tim_dau_hieu_chan("HTTP 403 Forbidden") == ["forbidden", "403"]


def test_tim_dau_hieu_chan_khong_thay_gi_thi_tra_rong() -> None:
    assert tim_dau_hieu_chan("<div class='feed'>Cơm tấm Ba Ghiền</div>") == []


@pytest.mark.parametrize("gia_tri", ["", None, 123, [], {}])
def test_tim_dau_hieu_chan_khong_chet_vi_dau_vao_la(gia_tri: object) -> None:
    """Canary nhận `page.content()` — thứ có thể là bất cứ gì khi trang lỗi."""
    assert tim_dau_hieu_chan(gia_tri) == []  # type: ignore[arg-type]


def test_xep_muc_xanh_khi_moi_thu_con() -> None:
    muc, thieu, mat = xep_muc_nguon(_NGUON_GIA, _dem())
    assert muc == MUC_XANH
    assert thieu == [] and mat == []


def test_bi_chan_la_do_du_selector_van_con() -> None:
    """Bị chặn thì selector còn hay mất không quan trọng — scraper không vào được."""
    muc, thieu, _ = xep_muc_nguon(
        _NGUON_GIA, _dem(), dau_hieu_bi_chan=["captcha"]
    )
    assert muc == MUC_DO
    assert thieu == []


def test_loi_tai_trang_la_do() -> None:
    muc, _, _ = xep_muc_nguon(_NGUON_GIA, _dem(), loi="TimeoutError: 45000ms exceeded")
    assert muc == MUC_DO


def test_mat_selector_bat_buoc_la_do() -> None:
    muc, thieu, _ = xep_muc_nguon(_NGUON_GIA, _dem(**{"#bat-buoc": 0}))
    assert muc == MUC_DO
    assert thieu == ["#bat-buoc"]


def test_mat_mot_nhanh_cua_nhom_chi_la_vang() -> None:
    """Còn một đường thay thế là scraper còn chạy được — báo đỏ là báo oan."""
    muc, thieu, mat = xep_muc_nguon(_NGUON_GIA, _dem(**{"#duong-1": 0}))
    assert muc == MUC_VANG
    assert thieu == []
    assert mat == ["#duong-1"]


def test_nhom_suy_giam_khong_can_selector_phai_nam_trong_danh_sach_tuy_chon() -> None:
    """Nhóm thay thế phải tự đủ: không bắt khai báo lặp lại ở `selector_tuy_chon`.

    Nếu luật xếp mức chỉ suy ra VÀNG từ `selector_tuy_chon` thì một nguồn khai nhóm
    mà quên liệt kê lại selector sẽ im lặng khi mất một nhánh — canary mù mà vẫn xanh.
    """
    nguon = NguonCanary(
        ma="chi-co-nhom",
        ten="Nguồn chỉ khai nhóm thay thế",
        url_mau="https://example.invalid",
        selector_bat_buoc=(),
        selector_tuy_chon=(),
        selector_nhom_it_nhat_mot=(("#duong-1", "#duong-2"),),
    )
    muc, thieu, mat = xep_muc_nguon(nguon, {"#duong-1": 0, "#duong-2": 4})
    assert muc == MUC_VANG
    assert thieu == []
    assert mat == ["#duong-1"]
    assert xep_muc_nguon(nguon, {"#duong-1": 0, "#duong-2": 0})[0] == MUC_DO


def test_chet_ca_nhom_thay_the_moi_la_do() -> None:
    muc, thieu, _ = xep_muc_nguon(_NGUON_GIA, _dem(**{"#duong-1": 0, "#duong-2": 0}))
    assert muc == MUC_DO
    assert set(thieu) == {"#duong-1", "#duong-2"}


def test_selector_trong_nhom_chet_khong_bao_lai_o_muc_phu() -> None:
    """Một selector chỉ được kể là MỘT sự cố, không in hai dòng gây hiểu nhầm."""
    _, thieu, mat = xep_muc_nguon(_NGUON_GIA, _dem(**{"#duong-1": 0, "#duong-2": 0}))
    assert not (set(thieu) & set(mat))


def test_mat_selector_phu_don_thuan_la_vang() -> None:
    muc, thieu, mat = xep_muc_nguon(_NGUON_GIA, _dem(**{"#phu-b": 0}))
    assert muc == MUC_VANG
    assert thieu == []
    assert mat == ["#phu-b"]


def test_selector_chua_tung_dem_duoc_coi_nhu_mat() -> None:
    """`so_phan_tu` thiếu khóa nghĩa là canary không đếm được — phải coi là mất.

    Coi là "còn" thì canary sẽ xanh đúng lúc nó không đọc được gì, tức là mù.
    """
    muc, thieu, _ = xep_muc_nguon(_NGUON_GIA, {})
    assert muc == MUC_DO
    assert "#bat-buoc" in thieu


def test_nguon_khong_co_selector_chi_do_khi_bi_chan_hoac_loi() -> None:
    """ShopeeFood: không dò DOM, nên chỉ trang chặn bot mới làm nó đỏ."""
    assert xep_muc_nguon(SHOPEEFOOD_NGUON, {})[0] == MUC_XANH
    assert (
        xep_muc_nguon(SHOPEEFOOD_NGUON, {}, dau_hieu_bi_chan=["403"])[0] == MUC_DO
    )
    assert xep_muc_nguon(SHOPEEFOOD_NGUON, {}, loi="net::ERR_NAME_NOT_RESOLVED")[0] == MUC_DO


def test_xep_muc_chung_lay_muc_nang_nhat() -> None:
    assert xep_muc_chung([MUC_XANH, MUC_VANG, MUC_XANH]) == MUC_VANG
    assert xep_muc_chung([MUC_VANG, MUC_DO, MUC_XANH]) == MUC_DO
    assert xep_muc_chung([MUC_XANH, MUC_XANH]) == MUC_XANH


def test_xep_muc_chung_khong_co_nguon_nao_thi_xanh() -> None:
    """Không có nguồn nào để dò thì không có bằng chứng hỏng — không được báo đỏ."""
    assert xep_muc_chung([]) == MUC_XANH


def test_xep_muc_chung_bo_qua_chuoi_rong() -> None:
    assert xep_muc_chung(["", MUC_VANG]) == MUC_VANG


def test_muc_khong_chay_duoc_nhe_hon_do() -> None:
    """Hạ tầng hỏng (không mở được trình duyệt) không nặng bằng nguồn chết thật.

    Nếu xếp ngược lại thì một lần runner thiếu camoufox sẽ che mất tín hiệu
    "ShopeFood đang chặn bot" — đúng thông tin canary sinh ra để báo.
    """
    assert xep_muc_chung([MUC_KHONG_CHAY, MUC_DO]) == MUC_DO


def test_xep_muc_nguon_la_ham_thuan() -> None:
    """ADR-002: cùng đầu vào phải cùng đầu ra, và không sửa đầu vào."""
    dem = _dem(**{"#duong-1": 0})
    ban_sao = dict(dem)
    lan_mot = xep_muc_nguon(_NGUON_GIA, dem, dau_hieu_bi_chan=["captcha"])
    lan_hai = xep_muc_nguon(_NGUON_GIA, dem, dau_hieu_bi_chan=["captcha"])
    assert lan_mot == lan_hai
    assert dem == ban_sao


def test_gmaps_selector_van_dung_y_scraper_dang_dua_vao() -> None:
    """Neo giá trị thật: đổi selector phải là một quyết định có ý thức, không vô tình.

    Scraper đọc rating bằng `span[aria-hidden='true']` và số review bằng
    `span.fontBodySmall`. Nếu hai chuỗi này đổi chỗ thì scraper vẫn chạy, vẫn trả
    số, chỉ là rating thành số review — lỗi im lặng nguy hiểm nhất ở đây.
    """
    assert GMAPS_SEL_RATING == "span[aria-hidden='true']"
    assert GMAPS_SEL_SO_REVIEW == "span.fontBodySmall"
    assert GMAPS_SEL_RATING != GMAPS_SEL_SO_REVIEW
    assert GMAPS_SEL_KHUNG_KET_QUA == "div[role='feed'] > div > div[jsaction]"
    assert GMAPS_SEL_TEN_QUAN == "div.fontHeadlineSmall"


def test_gmaps_hai_tab_anh_nam_trong_mot_nhom_thay_the() -> None:
    """Đúng mô tả trong `chu_thich`: Thực đơn và Tất cả ảnh thay thế được nhau."""
    assert GMAPS_NGUON.selector_nhom_it_nhat_mot == (
        (GMAPS_SEL_NUT_THUC_DON, GMAPS_SEL_NUT_TAT_CA_ANH),
    )
