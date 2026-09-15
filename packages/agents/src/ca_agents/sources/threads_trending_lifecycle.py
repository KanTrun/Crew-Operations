"""Theo dõi vòng đời xu hướng Threads Trending (plan 260914-1015 mục 4.2).

Logic THUẦN, không I/O, không LLM (ADR-002) — test được bằng fixture tĩnh.

So sánh snapshot chu kỳ T với T-1 để gán nhãn:
    NEW     — chủ đề chưa xuất hiện trong cửa sổ 24h qua.
    RISING  — thứ hạng tăng, hoặc volume tăng > 30% so với chu kỳ trước.
    PEAKING — giữ Top 1-3 từ >= 2 chu kỳ liên tiếp, tốc độ tăng đi ngang
              (biến thiên volume <= 10%).
    FADING  — tụt quá 3 bậc thứ hạng, hoặc volume giảm > 30%.

Cửa sổ 24h và các ngưỡng (30%, 10%, 3 bậc) lấy từ plan mục 4.2 — KHÔNG
tự chốt thêm tham số nghiệp vụ nào ngoài plan.
"""

from __future__ import annotations

from dataclasses import dataclass

from ca_contracts.threads_trending import ThreadsTrendingItem

# Ngưỡng theo plan mục 4.2 (hằng số có tên, không magic number rải rác).
NGUONG_TANG_TRUONG_PHAN_TRAM = 30.0  # RISING khi volume tăng > 30%
NGUONG_DI_NGANG_PHAN_TRAM = 10.0  # PEAKING khi biến thiên volume <= 10%
NGUONG_TU_HANG_BAC = 3  # FADING khi tụt > 3 bậc
NGUONG_GIU_TOP = 3  # PEAKING khi giữ Top 1-3
SO_CHU_KY_GIU_TOP_TOI_THIEU = 2  # PEAKING cần >= 2 chu kỳ liên tiếp
CUA_SO_GIO_24H = 24.0  # NEW khi chưa thấy trong 24h qua


@dataclass(frozen=True, slots=True)
class ChuKyTruoc:
    """Dữ liệu tối thiểu của chu kỳ T-1 cần cho việc gán nhãn.

    Giữ dạng dataclass riêng thay vì tái dùng ThreadsTrendingItem để caller
    (orchestrator) không phải lưu toàn bộ snapshot cũ — chỉ cần rank, volume
    và số chu kỳ đã giữ Top.
    """

    rank: int
    volume_count: int
    so_chu_ky_giu_top: int = 0


def _lech_phan_tram(moi: int, cu: int) -> float:
    """Trả lệch phần phần trăm so với giá trị cũ; cũ = 0 → +inf nếu moi > 0."""
    if cu <= 0:
        return float("inf") if moi > 0 else 0.0
    return (moi - cu) / cu * 100.0


def gan_nhan_vong_doi(
    hien_tai: ThreadsTrendingItem,
    truoc: ChuKyTruoc | None,
    lan_cuoi_thay_gio: float | None,
    gio_hien_tai: float,
) -> str:
    """Gán nhãn vòng đời cho MỘT chủ đề ở chu kỳ T.

    Args:
        hien_tai:          item snapshot hiện tại (rank, volume_count).
        truoc:             dữ liệu chu kỳ T-1 của cùng topic_id; None = chưa từng thấy.
        lan_cuoi_thay_gio: giờ (epoch) lần cuối topic xuất hiện; None = chưa từng thấy.
        gio_hien_tai:      giờ (epoch) của chu kỳ hiện tại.

    Returns:
        Một trong "NEW" | "RISING" | "PEAKING" | "FADING".

    Thứ tự ưu tiên (plan mục 4.2, mục 1 → 4):
        1. Chưa thấy trong 24h  → NEW
        2. Tụt > 3 bậc hoặc giảm > 30% → FADING
        3. Giữ Top 1-3 >= 2 chu kỳ + đi ngang → PEAKING
        4. Tăng hạng hoặc tăng > 30% → RISING
        5. Còn lại (đi ngang ngoài Top 3, biến thiên nhỏ) → PEAKING nếu đang
           trong Top 3, không thì RISING (vì vẫn còn trên bảng).
    """
    # 1. NEW — chưa từng thấy trong cửa sổ 24h
    if truoc is None or lan_cuoi_thay_gio is None:
        return "NEW"
    if gio_hien_tai - lan_cuoi_thay_gio > CUA_SO_GIO_24H * 3600:
        return "NEW"

    lech_hang = truoc.rank - hien_tai.rank  # dương = tăng hạng (số nhỏ hơn = cao hơn)
    lech_volume = _lech_phan_tram(hien_tai.volume_count, truoc.volume_count)

    # 2. FADING — tụt sâu hoặc mất động lực thảo luận
    if lech_hang < -NGUONG_TU_HANG_BAC or lech_volume < -NGUONG_TANG_TRUONG_PHAN_TRAM:
        return "FADING"

    # 3. PEAKING — giữ Top 1-3 liên tiếp >= 2 chu kỳ và volume đi ngang
    dang_giu_top = hien_tai.rank <= NGUONG_GIU_TOP
    if (
        truoc.so_chu_ky_giu_top + 1 >= SO_CHU_KY_GIU_TOP_TOI_THIEU
        and dang_giu_top
        and abs(lech_volume) <= NGUONG_DI_NGANG_PHAN_TRAM
    ):
        return "PEAKING"

    # 4. RISING — tăng hạng hoặc volume tăng mạnh
    if lech_hang > 0 or lech_volume > NGUONG_TANG_TRUONG_PHAN_TRAM:
        return "RISING"

    # 5. Còn lại: vẫn trên bảng, không đủ điều kiện PEAKING → giữ nhãn trung tính
    # theo vị trí: trong Top 3 mà chưa đủ số chu kỳ → RISING (đang tiến lên đỉnh).
    if dang_giu_top:
        return "RISING"
    return "FADING" if lech_hang < 0 else "RISING"


def gan_nhan_snapshot(
    hien_tai: list[ThreadsTrendingItem],
    lich_su: dict[str, ChuKyTruoc],
    lan_cuoi_thay: dict[str, float],
    gio_hien_tai: float | None = None,
) -> list[ThreadsTrendingItem]:
    """Gán nhãn vòng đời cho TOÀN BỘ snapshot, trả list item đã cập nhật.

    Args:
        hien_tai:        snapshot chu kỳ T (lifecycle có thể là giá trị placeholder).
        lich_su:         map topic_id → dữ liệu chu kỳ T-1.
        lan_cuoi_thay:   map topic_id → giờ lần cuối xuất hiện.
        gio_hien_tai:    giờ (epoch) của chu kỳ hiện tại; None = dùng giờ hệ thống.

    Returns:
        List item mới với `lifecycle` đã gán (item gốc không bị mutate —
        ThreadsTrendingItem là frozen theo convention pydantic immutable).
    """
    import time as _time

    if gio_hien_tai is None:
        gio_hien_tai = _time.time()

    out: list[ThreadsTrendingItem] = []
    for it in hien_tai:
        nhan = gan_nhan_vong_doi(
            hien_tai=it,
            truoc=lich_su.get(it.topic_id),
            lan_cuoi_thay_gio=lan_cuoi_thay.get(it.topic_id),
            gio_hien_tai=gio_hien_tai,
        )
        out.append(it.model_copy(update={"lifecycle": nhan}))
    return out


def tinh_trang_thai_chu_ky_sau(
    hien_tai: list[ThreadsTrendingItem],
    lich_su: dict[str, ChuKyTruoc] | None = None,
) -> dict[str, ChuKyTruoc]:
    """Tính dữ liệu `ChuKyTruoc` cho chu kỳ T+1 từ snapshot T.

    Gọi SAU khi đã gán nhãn xong chu kỳ T; kết quả đưa vào `lich_su` cho
    lần gán nhãn kế tiếp. `so_chu_ky_giu_top` cộng dồn khi topic nằm trong
    Top 1-3, reset về 0 khi rơi khỏi Top 3.

    Args:
        hien_tai: snapshot chu kỳ T (đã gán nhãn xong).
        lich_su:  map topic_id → ChuKyTruoc của chu kỳ T-1 (để cộng dồn số
                  chu kỳ giữ Top); None/missing → topic mới, đếm từ 0.
    """
    lich_su = lich_su or {}
    out: dict[str, ChuKyTruoc] = {}
    for it in hien_tai:
        trong_top = it.rank <= NGUONG_GIU_TOP
        truoc = lich_su.get(it.topic_id)
        so_chu_ky = (truoc.so_chu_ky_giu_top + 1) if (truoc and trong_top) else (1 if trong_top else 0)
        out[it.topic_id] = ChuKyTruoc(
            rank=it.rank,
            volume_count=it.volume_count,
            so_chu_ky_giu_top=so_chu_ky,
        )
    return out
