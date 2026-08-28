"""AG-EXPLAIN — dịch mã lý do của bộ giải thành câu tiếng Việt.

Ranh giới (§7.1): agent KHÔNG tính con số nào. Cụm từ và tập số hợp lệ do
lõi tất định (`ca_solver.explain`) đưa vào qua bộ điều phối. Agent chỉ soạn
câu. Nhờ vậy cổng VF-NUM luôn kiểm được: mọi chữ số trong câu đều phải nằm
trong `so_lieu_cho_phep`.

Không ghi DB · không gọi agent khác · không quyết định luồng.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_NUM = re.compile(r"\d+(?:[.,]\d+)?")

# Tối đa 3 mệnh đề trong một câu — quá 3 thì người đọc không nhớ được.
MAX_MENH_DE = 3

# Mã lý do có phần số kèm theo, và cách gắn số vào câu.
# Khoá = mã lý do · giá trị = mẫu câu dùng đúng số đã cho.
DUOI_SO: dict[str, str] = {
    "CON_TRAN_GIO": "đã làm {0}/{1} giờ tuần này",
    "DU_KHOANG_NGHI": "nghỉ tối thiểu {0} giờ giữa hai ca",
    "NO_CONG_BANG_CAO": "tổng nợ công bằng {0}",
    "NO_CONG_BANG_THAP": "tổng nợ công bằng {0}",
    "CA_CAN_THEM_NGUOI": "ca cần {0} người",
}


@dataclass
class ExplainResult:
    cau: str
    nguon_ma: list[str] = field(default_factory=list)
    so_lieu_dung: list[str] = field(default_factory=list)
    bi_loai: list[str] = field(default_factory=list)
    loai: str = "dien_giai_phan_cong"


def _duoi_so(ma: str, so_lieu: list[str], cho_phep: set[str]) -> str | None:
    """Sinh mệnh đề có số, chỉ khi mọi số đều nằm trong tập cho phép."""
    mau = DUOI_SO.get(ma)
    if not mau or not so_lieu:
        return None
    can = mau.count("{")
    if len(so_lieu) < can:
        return None
    dung = so_lieu[:can]
    if any(s not in cho_phep for s in dung):
        return None
    return mau.format(*dung)


def dien_giai(
    ma_list: list[str],
    cum_tu: dict[str, str],
    so_lieu: dict[str, list[str]] | None = None,
    *,
    so_lieu_cho_phep: set[str] | None = None,
) -> ExplainResult:
    """Soạn một câu tiếng Việt từ các mã lý do.

    Args:
        ma_list: mã lý do theo thứ tự ưu tiên, do lõi sinh ra.
        cum_tu: mã -> cụm từ tiếng Việt (từ `ca_solver.MA_LY_DO`).
        so_lieu: mã -> danh sách số kèm theo mã đó.
        so_lieu_cho_phep: tập số VF-NUM chấp nhận. Mặc định là hợp của `so_lieu`.

    Returns:
        ExplainResult — `cau` chỉ chứa số nằm trong tập cho phép.
    """
    so_lieu = so_lieu or {}
    if so_lieu_cho_phep is None:
        so_lieu_cho_phep = {s for v in so_lieu.values() for s in v}

    menh_de: list[str] = []
    dung_ma: list[str] = []
    bi_loai: list[str] = []

    for ma in ma_list:
        cum = cum_tu.get(ma)
        if not cum:
            bi_loai.append(f"{ma}:khong_co_cum_tu")
            continue
        if _NUM.search(cum):
            # Cụm từ gốc không được chứa số — số phải đi qua DUOI_SO.
            bi_loai.append(f"{ma}:cum_tu_co_so")
            continue
        if len(menh_de) >= MAX_MENH_DE:
            bi_loai.append(f"{ma}:vuot_max_menh_de")
            continue
        them = _duoi_so(ma, so_lieu.get(ma, []), so_lieu_cho_phep)
        menh_de.append(f"{cum} ({them})" if them else cum)
        dung_ma.append(ma)

    if not menh_de:
        return ExplainResult(
            cau="Chưa có căn cứ để diễn giải phân công này.",
            nguon_ma=[],
            so_lieu_dung=[],
            bi_loai=bi_loai,
        )

    if len(menh_de) == 1:
        thanh_phan = menh_de[0]
    else:
        thanh_phan = ", ".join(menh_de[:-1]) + " và " + menh_de[-1]

    cau = f"Người này vào ca vì {thanh_phan}."
    return ExplainResult(
        cau=cau,
        nguon_ma=dung_ma,
        so_lieu_dung=_NUM.findall(cau),
        bi_loai=bi_loai,
    )
