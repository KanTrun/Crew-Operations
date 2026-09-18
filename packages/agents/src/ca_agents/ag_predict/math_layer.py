"""Math Layer — AG-PREDICT (plan mục 4).

ADR-002: MỌI con số nghiệp vụ (outlier dương, độ co giãn giá, phân rã mùa, doanh
thu mô phỏng, lợi nhuận thêm nhân sự) nằm trong các hàm THUẦN ở module này.

CẤM trong module này:
- gọi LLM / model AI
- gọi network
- đọc/ghi DB
- đọc file
- dùng `random`, `time.time()`, hoặc bất kỳ nguồn bất định nào

Cùng input → cùng output, offline hoàn toàn.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ca_contracts.ops_predict import (
    SuccessPattern,
    SuccessPatternSource,
    SuccessPatternType,
)

# Ngưỡng outlier dương (z-score) — plan mục 13.2, chờ duyệt.
_DEFAULT_ZSCORE_THRESHOLD = 1.5
# Số ca "thành công" tối thiểu để coi là mẫu — plan mục 13.2.
_MIN_SAMPLE = 3
# Hệ số co giãn giá mặc định — plan mục 13.2.
_DEFAULT_ELASTICITY = -0.5


# ── 4.1 Phát hiện mẫu thành công ─────────────────────────────────────────────


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    var = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def _zscore(value: float, values: Sequence[float]) -> float:
    m = _mean(values)
    s = _stddev(values)
    if s == 0:
        return 0.0
    return (value - m) / s


def _is_positive_outlier(value: float, values: Sequence[float], threshold: float) -> bool:
    """Outlier dương: giá trị vượt trội so với trung bình của các giá trị KHÁC.

    Dùng leave-one-out mean để outlier không tự làm lệch chính nó (phù hợp dữ
    liệu nhỏ). Giá trị > mean_khac + threshold * stddev_khac.
    """
    others = [v for v in values if v != value]
    if len(others) < 2:
        return False
    m = _mean(others)
    s = _stddev(others)
    if s == 0:
        return value > m
    return (value - m) / s > threshold


def detect_success_patterns(
    doanh_thu_by_ca: dict[str, float],
    doanh_thu_by_mon: dict[str, float],
    ton_kho_by_time: dict[str, float],
    *,
    zscore_threshold: float = _DEFAULT_ZSCORE_THRESHOLD,
    min_sample: int = _MIN_SAMPLE,
) -> list[SuccessPattern]:
    """Phát hiện mẫu thành công từ dữ liệu lịch sử (tất định).

    - Ca doanh thu vượt trội: z-score dương > ngưỡng.
    - Món bán chạy: top N theo doanh thu (z-score dương).
    - Tồn kho tiêu thụ nhanh: giá trị cao (z-score dương).
    """
    patterns: list[SuccessPattern] = []

    # 1. Ca doanh thu vượt trội (outlier dương)
    ca_values = list(doanh_thu_by_ca.values())
    if len(ca_values) >= min_sample:
        for ca_id, val in doanh_thu_by_ca.items():
            if _is_positive_outlier(val, ca_values, zscore_threshold):
                patterns.append(
                    SuccessPattern(
                        pattern_id=f"pat_ca_{ca_id}",
                        loai=SuccessPatternType.CA_DOANH_THU,
                        mo_ta=f"Ca {ca_id} doanh thu {val:.0f} vượt trội",
                        do_tin_cay=0.8,
                        bang_chung=[ca_id],
                        nguon=SuccessPatternSource.LICH_SU_DOANH_THU,
                    )
                )

    # 2. Món bán chạy (outlier dương theo doanh thu)
    mon_values = list(doanh_thu_by_mon.values())
    if len(mon_values) >= min_sample:
        for mon_id, val in doanh_thu_by_mon.items():
            if _is_positive_outlier(val, mon_values, zscore_threshold):
                patterns.append(
                    SuccessPattern(
                        pattern_id=f"pat_mon_{mon_id}",
                        loai=SuccessPatternType.MON_BAN_CHAY,
                        mo_ta=f"Món {mon_id} doanh thu {val:.0f} bán chạy",
                        do_tin_cay=0.8,
                        bang_chung=[mon_id],
                        nguon=SuccessPatternSource.LICH_SU_BAN,
                    )
                )

    # 3. Tồn kho tiêu thụ nhanh
    ton_values = list(ton_kho_by_time.values())
    if len(ton_values) >= min_sample:
        for item_id, val in ton_kho_by_time.items():
            if _is_positive_outlier(val, ton_values, zscore_threshold):
                patterns.append(
                    SuccessPattern(
                        pattern_id=f"pat_ton_{item_id}",
                        loai=SuccessPatternType.TON_KHO_NHANH,
                        mo_ta=f"Nguyên liệu {item_id} tiêu thụ nhanh",
                        do_tin_cay=0.8,
                        bang_chung=[item_id],
                        nguon=SuccessPatternSource.TON_KHO,
                    )
                )

    return patterns


# ── 4.2 Độ co giãn giá ───────────────────────────────────────────────────────


def price_elasticity(
    gia_cu: float,
    gia_moi: float,
    luong_ban_cu: float,
    he_so_co_gian: float = _DEFAULT_ELASTICITY,
) -> float:
    """Ước tính lượng bán mới khi đổi giá (tất định).

    phan_tram_gia = (gia_moi - gia_cu) / gia_cu
    phan_tram_luong = he_so_co_gian * phan_tram_gia
    luong_moi = luong_cu * (1 + phan_tram_luong)
    """
    if gia_cu <= 0:
        return luong_ban_cu
    phan_tram_gia = (gia_moi - gia_cu) / gia_cu
    phan_tram_luong = he_so_co_gian * phan_tram_gia
    return max(0.0, luong_ban_cu * (1 + phan_tram_luong))


# ── 4.3 Ước tính doanh thu mới ───────────────────────────────────────────────


def doanh_thu_moi(
    gia_moi: float,
    luong_ban_moi: float,
    chi_phi_bien_doi: float,
) -> float:
    """Doanh thu mới = giá mới × lượng bán mới − chi phí biến đổi."""
    return gia_moi * luong_ban_moi - chi_phi_bien_doi


# ── 4.4 Ước tính lợi nhuận thêm nhân sự ──────────────────────────────────────


def loi_nhuan_them_nhan_su(
    doanh_thu_tang_them: float,
    chi_phi_nhan_su: float,
) -> float:
    """Lợi nhuận ròng khi thêm nhân sự."""
    return doanh_thu_tang_them - chi_phi_nhan_su


# ── 4.5 Phân rã mùa (Seasonal Decomposition) ─────────────────────────────────


_THU_ORDER = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


def phan_ra_mua(
    doanh_thu_by_ngay: dict[str, float],
) -> dict[str, float]:
    """Phân rã doanh thu theo ngày trong tuần (tất định).

    Trả về hệ số mùa cho từng ngày (T2–CN): doanh_thu_ngay / trung_bình.
    Ngày không có dữ liệu → 0.0.
    """
    values = list(doanh_thu_by_ngay.values())
    avg = _mean(values)
    if avg == 0:
        return {thu: 0.0 for thu in _THU_ORDER}
    result: dict[str, float] = {}
    for thu in _THU_ORDER:
        val = doanh_thu_by_ngay.get(thu, 0.0)
        result[thu] = val / avg
    return result