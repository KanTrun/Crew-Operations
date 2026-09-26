"""AG-VOC — đọc phản hồi khách do quán tự chuyển vào.

Phạm vi đã thu hẹp có chủ ý (§6.2): **không** thu thập tự động từ Google Maps,
ShopeeFood hay Grab, vì việc đó có thể vi phạm điều khoản sử dụng của các nền
tảng và đội chưa kiểm chứng được. Chỉ nhận nội dung quán tự dán, chuyển tiếp,
hoặc chụp ảnh.

Nhiệm vụ: phân loại thành **sự cố vận hành** rồi nối vào **việc treo** có người
nhận và có hạn. Phản hồi thuộc nhóm giá cả / khuyến mãi / thực đơn là việc
marketing — agent trả `la_su_co_van_hanh=False` và **không** sinh việc treo.

Mỗi kết quả mang `source_span` dạng `{"text_offset": int}` để cổng VF-TRACE
kiểm được: mọi phân loại phải trỏ về một đoạn văn thật trong phản hồi gốc.

Không ghi DB · không gọi agent khác · không quyết định luồng · không trả lời khách.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ca_agents.sensors.sensor_chain import SensorChain

# ── Nhóm sự cố vận hành ───────────────────────────────────────────────────
# Khoá = mã sự cố · giá trị = từ khoá không dấu, chữ thường.
SU_CO_VAN_HANH: dict[str, tuple[str, ...]] = {
    "cho_lau": ("cho lau", "cho hoi lau", "lau qua", "doi lau", "cham qua", "15 phut"),
    "sai_don": ("sai don", "sai mon", "khong dung mon", "giao sai", "nham mon"),
    "chat_luong": ("nhat", "loang", "chua", "khet", "nguoi", "khong ngon", "qua ngot"),
    "ve_sinh": ("ban", "khong sach", "ve sinh", "ly ban", "ban ghe ban", "co ruoi"),
    "thiet_bi": ("may hu", "may pha", "wifi", "dieu hoa", "may lanh", "o cam", "toilet"),
    "phuc_vu": ("khong ai tiep", "khong chao", "bo mac", "khong ai hoi"),
}

# Nhóm marketing — nhận ra để **loại**, không nối vào việc treo.
MARKETING: tuple[str, ...] = (
    "gia",
    "dat qua",
    "khuyen mai",
    "voucher",
    "giam gia",
    "them mon",
    "menu moi",
    "combo",
)

# Câu việc treo theo từng mã sự cố. Không câu nào nêu tên người.
VIEC_TREO: dict[str, str] = {
    "cho_lau": "Xem lại luồng pha chế giờ cao điểm — khách phản hồi chờ lâu",
    "sai_don": "Rà lại bước xác nhận đơn trước khi pha — khách phản hồi sai món",
    "chat_luong": "Kiểm định mức pha và nhiệt độ — khách phản hồi chất lượng đồ uống",
    "ve_sinh": "Bổ sung lượt vệ sinh khu khách ngồi — khách phản hồi chưa sạch",
    "thiet_bi": "Kiểm tra thiết bị khách nêu và ghi vào phiếu bảo trì",
    "phuc_vu": "Rà lại bước chào và tiếp khách trong phiếu mở quán",
    "su_co_an_toan": "Kiểm tra khẩn cấp an toàn vệ sinh thực phẩm và liên hệ khách ngay",
    "khieu_nai_gay_gat": "Xử lý khẩn cấp phản hồi gay gắt từ khách hàng",
}

HAN_GIO: dict[str, int] = {
    "cho_lau": 24,
    "sai_don": 24,
    "chat_luong": 12,
    "ve_sinh": 4,
    "thiet_bi": 8,
    "phuc_vu": 24,
}


def _bo_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt, hạ chữ thường — để so từ khoá ổn định."""
    nfd = unicodedata.normalize("NFD", s or "")
    khong_dau = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return khong_dau.replace("đ", "d").replace("Đ", "D").lower()


@dataclass
class VocResult:
    la_su_co_van_hanh: bool
    loai: str
    tu_khoa: str = ""
    source_span: dict[str, int] = field(default_factory=dict)
    cau_viec_treo: str | None = None
    han_gio: int | None = None
    do_tin_cay: float = 0.0
    ghi_chu: str = ""


def phan_loai(phan_hoi: str) -> VocResult:
    """Phân loại một phản hồi khách.

    Args:
        phan_hoi: nội dung thô do quán chuyển vào.

    Returns:
        VocResult. Nếu là sự cố vận hành thì có `cau_viec_treo`, `han_gio` và
        `source_span` trỏ về vị trí từ khoá trong `phan_hoi`. Nếu là marketing
        hoặc không nhận ra thì không sinh việc treo.
    """
    if not (phan_hoi or "").strip():
        return VocResult(
            la_su_co_van_hanh=False,
            loai="khong_doc_duoc",
            do_tin_cay=0.0,
            ghi_chu="phan_hoi_rong",
        )

    phang = _bo_dau(phan_hoi)

    # Sự cố vận hành đứng trước marketing: một phản hồi vừa khen giá vừa
    # báo chờ lâu thì phần vận hành mới là phần có người phải xử lý.
    for ma in SU_CO_VAN_HANH:
        for tu in SU_CO_VAN_HANH[ma]:
            vi_tri = phang.find(tu)
            if vi_tri < 0:
                continue
            return VocResult(
                la_su_co_van_hanh=True,
                loai=ma,
                tu_khoa=tu,
                source_span={"text_offset": vi_tri},
                cau_viec_treo=VIEC_TREO[ma],
                han_gio=HAN_GIO[ma],
                do_tin_cay=0.78,
            )

    for tu in MARKETING:
        vi_tri = phang.find(tu)
        if vi_tri >= 0:
            return VocResult(
                la_su_co_van_hanh=False,
                loai="marketing",
                tu_khoa=tu,
                source_span={"text_offset": vi_tri},
                do_tin_cay=0.6,
                ghi_chu="ngoai_pham_vi_van_hanh_khong_noi_viec_treo",
            )

    return VocResult(
        la_su_co_van_hanh=False,
        loai="chua_phan_loai_duoc",
        do_tin_cay=0.0,
        ghi_chu="day_len_nguoi",
    )


def phan_loai_lo(phan_hoi_list: list[str]) -> list[VocResult]:
    """Phân loại một lô phản hồi. Mỗi phản hồi độc lập."""
    return [phan_loai(p) for p in phan_hoi_list]


def phan_loai_nang_cao(
    phan_hoi: str,
    sensor_chain: SensorChain | None = None,
) -> VocResult:
    """Phân loại nâng cao: regex trước, SensorChain bổ sung sau (opt-in).

    Gọi `phan_loai()` để phân loại tất định rồi dùng SensorChain (JEV →
    RegexSensor fallback) để bổ sung:
    - `nguy_co_suc_khoe ≥ 0.30` → nâng loại thành "su_co_an_toan", han_gio=1.
    - `muc_gay_gat ≥ 1.5`       → rút han_gio xuống còn 2h (thay vì 24h).
    - `co_ve_mia_mai ≥ 0.50`    → ghi vào ghi_chu để báo người xử lý.

    Nguyên tắc đơn điệu: SensorChain chỉ rút ngắn hạn (leo thang) hoặc thêm
    loại nghiêm trọng hơn, không bao giờ nới lỏng kết quả regex đã có.

    Args:
        phan_hoi: Nội dung phản hồi khách.
        sensor_chain: SensorChain đã khởi tạo. None → tạo mới chỉ Regex.

    Returns:
        VocResult (có thể đã được nâng cấp so với phan_loai() thuần túy).
    """
    base = phan_loai(phan_hoi)

    # Import lazy tránh vòng lặp phụ thuộc.
    from ca_agents.sensors.sensor_chain import SensorChain
    from ca_agents.sensors.voc_questions import VOC_QUESTIONS

    chain = sensor_chain
    if chain is None:
        chain = SensorChain()  # chỉ Regex (JEV chưa bật)

    result = chain.evaluate(phan_hoi, "voc_phan_loai", VOC_QUESTIONS)

    # Nếu cả hai cảm biến thất bại → giữ kết quả regex cơ bản, ghi chú.
    if result.both_failed:
        return VocResult(
            la_su_co_van_hanh=base.la_su_co_van_hanh,
            loai=base.loai,
            tu_khoa=base.tu_khoa,
            source_span=base.source_span,
            cau_viec_treo=base.cau_viec_treo,
            han_gio=base.han_gio,
            do_tin_cay=base.do_tin_cay,
            ghi_chu=f"{base.ghi_chu}|sensor_chain_failed" if base.ghi_chu else "sensor_chain_failed",
        )

    signals = result.signals
    health = signals.get("nguy_co_suc_khoe")
    hostility = signals.get("muc_gay_gat")
    sarcasm = signals.get("co_ve_mia_mai")

    loai = base.loai
    han_gio = base.han_gio
    la_su_co = base.la_su_co_van_hanh
    ghi_chu_parts = [base.ghi_chu] if base.ghi_chu else []

    if result.fallback_used:
        ghi_chu_parts.append(f"sensor_source={result.source}")

    # An toàn sức khỏe: ưu tiên cao nhất — ghi đè loại và rút hạn xuống 1h.
    if health is not None and float(health.value) >= 0.30:
        loai = "su_co_an_toan"
        han_gio = 1
        la_su_co = True
        ghi_chu_parts.append(f"health_risk={health.value:.2f}")

    # Bức xúc cao: rút hạn xuống 2h (chỉ khi han_gio > 2 hoặc chưa có) và đánh dấu sự cố.
    elif hostility is not None and float(hostility.value) >= 1.5:
        la_su_co = True
        if loai == "chua_phan_loai_duoc":
            loai = "khieu_nai_gay_gat"
        if han_gio is None or han_gio > 2:
            han_gio = 2
        ghi_chu_parts.append(f"hostility={hostility.value:.2f}")

    # Mỉa mai: không thay đổi phân loại, chỉ ghi chú để người xử lý biết.
    if sarcasm is not None and float(sarcasm.value) >= 0.50:
        ghi_chu_parts.append(f"mia_mai={sarcasm.value:.2f}")

    return VocResult(
        la_su_co_van_hanh=la_su_co,
        loai=loai,
        tu_khoa=base.tu_khoa,
        source_span=base.source_span,
        cau_viec_treo=VIEC_TREO.get(loai, base.cau_viec_treo),
        han_gio=han_gio,
        do_tin_cay=base.do_tin_cay,
        ghi_chu="|".join(ghi_chu_parts) if ghi_chu_parts else "",
    )
