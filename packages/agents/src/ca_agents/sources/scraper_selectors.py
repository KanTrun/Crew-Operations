"""Selector của các nguồn cào bên thứ ba — NGUỒN DUY NHẤT cho cả scraper lẫn canary.

Vì sao tách ra file riêng (plan `260913-1455` mục 7, [ĐỀ XUẤT MỚI]):
scraper phụ thuộc cấu trúc trang của ShopeeFood/Google Maps, thứ có thể đổi bất kỳ
lúc nào mà không báo trước. Nếu selector nằm rải rác trong hàm cào dữ liệu thì
canary test phải CHÉP LẠI chúng — mà bản chép thì vẫn pass sau khi trang đổi, tức
canary mù đúng lúc cần nó nhất.

Nên: selector khai báo ở đây, `gmaps_menu_source` / `delivery_camoufox_source` import
để cào, còn `scripts/canary/` import chính danh sách này để dò trang thật. Đổi selector
ở một chỗ là cả hai bên đổi theo.

File này không import gì ngoài stdlib nên canary chạy được trong môi trường tối giản,
và không có I/O nào — kể cả `tim_dau_hieu_chan` / `xep_muc_nguon` cũng là hàm THUẦN
(ADR-002) để test lại được luật xếp mức mà không phải mở trang thật.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NguonCanary:
    """Một bề mặt trang bên thứ ba mà scraper đang dựa vào.

    Ba loại ràng buộc, vì "mất selector" không phải lúc nào cũng cùng mức nghiêm trọng:

    - `selector_bat_buoc`: thiếu MỘT cái là scraper chắc chắn không lấy được dữ liệu
      → ĐỎ.
    - `selector_nhom_it_nhat_mot`: mỗi nhóm là các đường thay thế nhau; còn MỘT
      đường là còn chạy được (VÀNG), mất CẢ NHÓM mới là ĐỎ. Không có khái niệm này
      thì canary hoặc báo đỏ oan khi Google bỏ tab Thực đơn, hoặc im lặng khi mất
      luôn cả fallback Tất cả ảnh.
    - `selector_tuy_chon`: mất thì suy giảm chứ không chết → VÀNG.

    Một selector có thể nằm trong cả nhóm và `selector_tuy_chon`: nhóm quyết định
    MỨC báo cáo, còn `selector_tuy_chon` để báo cáo liệt kê từng cái một cho người đọc.
    """

    ma: str
    ten: str
    url_mau: str
    selector_bat_buoc: tuple[str, ...]
    selector_tuy_chon: tuple[str, ...] = ()
    selector_nhom_it_nhat_mot: tuple[tuple[str, ...], ...] = ()
    chu_thich: str = ""


# ── Google Maps (kênh dine-in, đọc ảnh thực đơn) ─────────────────────────────
#
# URL mẫu dùng tọa độ Quận 1 TP.HCM — khu vực có nhiều quán F&B thật, nên "không
# thấy kết quả nào" gần như chắc chắn là do trang đổi cấu trúc chứ không phải do
# chỗ đó không có quán.

_GMAPS_TOA_DO = (10.7769, 106.7009)
_GMAPS_TU_KHOA = "cơm tấm"

# Selector có TÊN, không phải theo vị trí trong tuple. Scraper import theo tên
# (`GMAPS_SEL_KHUNG_KET_QUA`) chứ không theo chỉ số (`selector_tuy_chon[3]`): đổi
# thứ tự khai báo bên dưới mà quên sửa chỗ khác sẽ làm scraper đọc rating bằng
# selector đếm review — lỗi im lặng, khó thấy nhất trong loại bug này.
GMAPS_SEL_KHUNG_KET_QUA = "div[role='feed'] > div > div[jsaction]"
GMAPS_SEL_TEN_QUAN = "div.fontHeadlineSmall"
GMAPS_SEL_NUT_THUC_DON = (
    "button[aria-label*='Thực đơn'], button[aria-label*='Menu'], "
    "button[aria-label*='thực đơn'], button[aria-label*='menu']"
)
GMAPS_SEL_NUT_TAT_CA_ANH = (
    "button[aria-label*='Ảnh'], button[aria-label*='Photos'], "
    "button[aria-label*='ảnh'], button[aria-label*='Tất cả ảnh']"
)
GMAPS_SEL_ANH_TRONG_VUNG = "div[role='region'] img, div[aria-label*='Ảnh'] img"
GMAPS_SEL_RATING = "span[aria-hidden='true']"
GMAPS_SEL_SO_REVIEW = "span.fontBodySmall"

GMAPS_NGUON = NguonCanary(
    ma="gmaps",
    ten="Google Maps — tìm kiếm quán F&B",
    url_mau=(
        f"https://www.google.com/maps/search/{_GMAPS_TU_KHOA}+gần+đây/"
        f"@{_GMAPS_TOA_DO[0]},{_GMAPS_TOA_DO[1]},15z"
    ),
    selector_bat_buoc=(
        # Khung danh sách kết quả. Mất cái này là không có quán nào để duyệt.
        GMAPS_SEL_KHUNG_KET_QUA,
        # Tên quán — không đọc được tên thì bản ghi vô dụng kể cả khi có ảnh.
        GMAPS_SEL_TEN_QUAN,
    ),
    selector_tuy_chon=(
        GMAPS_SEL_NUT_THUC_DON,
        GMAPS_SEL_NUT_TAT_CA_ANH,
        GMAPS_SEL_ANH_TRONG_VUNG,
        GMAPS_SEL_RATING,
        GMAPS_SEL_SO_REVIEW,
    ),
    selector_nhom_it_nhat_mot=(
        # Hai bước của scraper: tab Thực đơn trước, fallback Tất cả ảnh. Mất một
        # trong hai thì vẫn còn ảnh để OCR (VÀNG); mất cả hai là không còn đường
        # nào vào ảnh thực đơn (ĐỎ).
        (GMAPS_SEL_NUT_THUC_DON, GMAPS_SEL_NUT_TAT_CA_ANH),
    ),
    chu_thich=(
        "Hai bước: tab Thực đơn trước, fallback Tất cả ảnh. Mất cả HAI tab mới là "
        "sự cố đỏ; mất một tab chỉ làm giảm số ảnh đọc được."
    ),
)

# ── ShopeeFood (kênh delivery) ───────────────────────────────────────────────

SHOPEEFOOD_NGUON = NguonCanary(
    ma="shopeefood",
    ten="ShopeeFood — trang tìm kiếm",
    url_mau=f"https://shopeefood.vn/search?keyword={_GMAPS_TU_KHOA}",
    selector_bat_buoc=(),
    selector_tuy_chon=(),
    chu_thich=(
        "Scraper KHÔNG đọc DOM trang này — nó bắt response JSON của "
        "`api/delivery/search` / `api/delivery/get_browse_dishes`. Canary vì thế chỉ "
        "kiểm tra trang còn tải được và không trả trang chặn bot, không dò selector."
    ),
)

# Danh sách canary duyệt qua, theo thứ tự quan trọng giảm dần.
CAC_NGUON: tuple[NguonCanary, ...] = (GMAPS_NGUON, SHOPEEFOOD_NGUON)

# Chuỗi xuất hiện trong nội dung/URL khi bị chặn — dùng chung với scraper để hai
# bên không lệch định nghĩa "bị chặn". Bốn khóa đầu là tập scraper đang dùng thật
# (giữ nguyên để không đổi hành vi); hai khóa cuối là trang chặn đặc trưng của
# Google mà canary cần nhận ra sớm hơn scraper.
DAU_HIEU_BI_CHAN: tuple[str, ...] = (
    "captcha",
    "blocked",
    "forbidden",
    "403",
    "unusual traffic",
    "enablejsandcookies",
    "sorry/index",
)


# ── Xếp mức canary (hàm THUẦN — ADR-002) ─────────────────────────────────────
#
# Đặt ở đây chứ không phải trong script canary: script chỉ nên làm phần I/O trình
# duyệt, còn luật "thế nào là nguồn hỏng" phải test lại được mà không cần mở
# Google Maps thật.

MUC_XANH = "xanh"
MUC_VANG = "vang"
MUC_DO = "do"
MUC_KHONG_CHAY = "khong_chay_duoc"

_THU_TU_MUC: dict[str, int] = {MUC_DO: 0, MUC_VANG: 1, MUC_XANH: 2, MUC_KHONG_CHAY: 3}


def tim_dau_hieu_chan(text: str) -> list[str]:
    """Trả các chuỗi đặc trưng của trang chặn bot tìm thấy trong `text`.

    Rỗng nghĩa là không thấy dấu hiệu nào — KHÔNG suy ra "nguồn ổn", vì trang có
    thể đổi layout mà không chặn. Hai chuyện đó được xếp mức riêng.
    """
    if not isinstance(text, str) or not text:
        return []
    thuong = text.lower()
    return [dau for dau in DAU_HIEU_BI_CHAN if dau in thuong]


def xep_muc_nguon(
    nguon: NguonCanary,
    so_phan_tu: dict[str, int],
    *,
    dau_hieu_bi_chan: Sequence[str] = (),
    loi: str = "",
) -> tuple[str, list[str], list[str]]:
    """Xếp mức một nguồn từ kết quả đếm selector. Trả `(muc, thieu, mat_tuy_chon)`.

    `thieu` gộp selector bắt buộc mất VÀ các nhóm thay thế đã chết hết — cả hai đều
    nghĩa là "không có đường nào lấy được dữ liệu", nên người đọc không phải phân
    biệt hai loại để biết nguồn đã hỏng.

    Thứ tự ưu tiên cố ý:
      1. **Bị chặn** → ĐỎ. Scraper sẽ chết hẳn, không có dữ liệu nào để bàn.
      2. **Lỗi tải trang** → ĐỎ. Không phân biệt được "trang đổi" với "mạng hỏng",
         và cả hai đều nghĩa là không có dữ liệu.
      3. **Mất selector bắt buộc, hoặc chết cả một nhóm thay thế** → ĐỎ.
      4. **Chỉ mất selector phụ / mất một nhánh của nhóm** → VÀNG. Scraper còn
         đường fallback (vd tab Thực đơn mất thì vẫn còn Tất cả ảnh), nên đây là
         suy giảm chứ chưa phải hỏng.

    Nguồn không khai selector nào (vd ShopeeFood — scraper bắt response JSON chứ
    không đọc DOM) thì chỉ có thể ĐỎ do bị chặn/lỗi, không bao giờ đỏ vì selector.
    """
    thieu = [s for s in nguon.selector_bat_buoc if so_phan_tu.get(s, 0) == 0]
    nhom_chet: list[str] = []
    nhom_suy_giam: list[str] = []
    for nhom in nguon.selector_nhom_it_nhat_mot:
        if not nhom:
            continue
        mat = [s for s in nhom if so_phan_tu.get(s, 0) == 0]
        if len(mat) == len(nhom):
            # Ghi cả nhóm vào `thieu` để báo cáo chỉ ra được ĐÃ MẤT CẢ HAI ĐƯỜNG,
            # thay vì để người đọc tự suy từ hai dòng "mất selector phụ".
            nhom_chet.extend(nhom)
        elif mat:
            nhom_suy_giam.extend(mat)
    thieu.extend(s for s in nhom_chet if s not in thieu)

    # Mất một nhánh của nhóm là SUY GIẢM kể cả khi selector đó không nằm trong
    # `selector_tuy_chon`: nhóm thay thế tự nó đã nói lên "mất nhánh này thì ít ảnh
    # hơn". Bắt người khai báo phải liệt kê lại selector trong cả hai chỗ là mời
    # gọi hai danh sách lệch nhau.
    mat_tuy_chon = [s for s in nguon.selector_tuy_chon if so_phan_tu.get(s, 0) == 0]
    mat_tuy_chon.extend(s for s in nhom_suy_giam if s not in mat_tuy_chon)

    # Selector đã bị xếp vào "thiếu" thì không báo lại ở "mất phụ" — một selector
    # có thể nằm trong cả nhóm lẫn danh sách tùy chọn, in hai lần sẽ làm người đọc
    # tưởng có hai sự cố khác nhau.
    mat_tuy_chon = [s for s in mat_tuy_chon if s not in thieu]

    if dau_hieu_bi_chan:
        return MUC_DO, thieu, mat_tuy_chon
    if loi:
        return MUC_DO, thieu, mat_tuy_chon
    if thieu:
        return MUC_DO, thieu, mat_tuy_chon
    if mat_tuy_chon:
        return MUC_VANG, thieu, mat_tuy_chon
    return MUC_XANH, thieu, mat_tuy_chon


def xep_muc_chung(cac_muc: Iterable[str]) -> str:
    """Mức nặng nhất trong các nguồn — một chuỗi hỏng là cả radar hỏng."""
    muc = [m for m in cac_muc if m]
    if not muc:
        return MUC_XANH
    return min(muc, key=lambda m: _THU_TU_MUC.get(m, 9))


def selector_can_do(nguon: NguonCanary) -> tuple[str, ...]:
    """Mọi selector canary phải đếm, đã khử trùng lặp, giữ thứ tự khai báo.

    Canary dùng hàm này thay vì tự nối ba tuple: nếu một selector chỉ nằm trong
    `selector_nhom_it_nhat_mot` mà không được đếm thì `so_phan_tu.get(s, 0)` trả 0
    và nhóm đó sẽ bị kết luận là CHẾT — báo đỏ oan cho nguồn vẫn đang chạy tốt.
    """
    da_thay: dict[str, None] = {}
    for selector in (
        *nguon.selector_bat_buoc,
        *nguon.selector_tuy_chon,
        *(s for nhom in nguon.selector_nhom_it_nhat_mot for s in nhom),
    ):
        da_thay.setdefault(selector, None)
    return tuple(da_thay)
