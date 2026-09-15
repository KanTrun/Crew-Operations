"""Cost dashboard & KPI cho khảo sát giá (plan `260913-1455` mục 9 và 12).

Plan mục 9 yêu cầu ba thứ mà metrics thô chưa trả lời được:
  - **Chi phí biến đổi** quy ra tiền: Vision API (số ảnh × đơn giá) và proxy/
    anti-detect (số lượt × đơn giá) — vì đây là khoản phình theo lượng khảo sát.
  - **KPI thí điểm** (mục 12): tỷ lệ hoàn tất, thời gian trung bình, tỷ lệ phải
    review thủ công.
  - **Alerting**: tỷ lệ `SOURCE_BLOCKED` vượt ngưỡng là dấu hiệu nền tảng đã siết
    chống bot — phải biết TRƯỚC khi chạy ồ ạt.

ADR-002: mọi hàm ở đây là HÀM THUẦN. Nhận snapshot metrics + danh sách job +
config, trả dict. Không đọc đồng hồ hệ thống, không đọc đĩa, không network,
không LLM. Số đếm thời gian đến từ `created_at`/`updated_at` đã ghi sẵn trên job.

Đơn giá nằm ở `config/khao-sat-gia-tham-so.yaml` (khóa `chi_phi`), KHÔNG hard-code
ở đây — đổi nhà cung cấp proxy/Vision là sửa config, không sửa mã.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ca_agents.ag_pricing.pricing_config import (
    AlertConfig,
    CostConfig,
    get_pricing_config,
)

# ── Ngưỡng KPI — plan mục 12 ─────────────────────────────────────────────────
# Đây là MỤC TIÊU thí điểm ghi trong plan, không phải tham số nghiệp vụ cần chủ
# dự án duyệt, nên để hằng số ở đây thay vì đẩy vào config.
KPI_TI_LE_HOAN_TAT_TOI_THIEU = 0.85
KPI_THOI_GIAN_TRUNG_BINH_TOI_DA_GIAY = 180.0
KPI_TI_LE_CAN_REVIEW_TOI_DA = 0.15

MUC_CANH_BAO = "canh_bao"
MUC_NGHIEM_TRONG = "nghiem_trong"
MUC_THONG_TIN = "thong_tin"


@dataclass(frozen=True, slots=True)
class CanhBao:
    """Một cảnh báo vận hành. `ma` là khóa ổn định cho UI/log, không phải cho người đọc."""

    ma: str
    muc: str
    thong_diep: str
    gia_tri: float
    nguong: float


def _so(value: Any) -> float:
    """Ép về float an toàn — metrics thiếu khóa thì coi như 0, không nổ."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return 0.0
    return n if n == n and n not in (float("inf"), float("-inf")) else 0.0


def _nguyen(value: Any) -> int:
    return int(_so(value))


def _ti_le(tu: float, mau: float) -> float:
    """Tỷ lệ 0–1; mẫu bằng 0 thì trả 0.0 chứ không phải NaN hay exception."""
    return tu / mau if mau > 0 else 0.0


# ── Chi phí (plan mục 9) ─────────────────────────────────────────────────────


def tinh_chi_phi(
    metrics: Mapping[str, Any],
    cost: CostConfig | None = None,
) -> dict[str, Any]:
    """Quy số lượt gọi thành tiền theo đơn giá trong config.

    `vision_calls` đếm MỌI ảnh đưa qua OCR, kể cả ảnh bị từ chối đọc — nhà cung
    cấp vẫn tính tiền những lượt đó, nên không được trừ ra cho "đẹp số liệu".
    """
    cfg = cost or get_pricing_config().chi_phi
    vision_luot = _nguyen(metrics.get("vision_calls"))
    proxy_luot = _nguyen(metrics.get("proxy_requests"))
    jobs = _nguyen(metrics.get("jobs_created"))

    vision_usd = vision_luot * cfg.vision_usd_moi_anh
    proxy_usd = proxy_luot * cfg.proxy_usd_moi_luot
    tong_usd = vision_usd + proxy_usd

    return {
        "vision_luot": vision_luot,
        "vision_usd": round(vision_usd, 4),
        "proxy_luot": proxy_luot,
        "proxy_usd": round(proxy_usd, 4),
        "tong_usd": round(tong_usd, 4),
        "don_gia_vision_usd": cfg.vision_usd_moi_anh,
        "don_gia_proxy_usd": cfg.proxy_usd_moi_luot,
        "chi_phi_moi_job_usd": round(_ti_le(tong_usd, jobs), 4),
        "ngan_sach_usd_thang": cfg.ngan_sach_usd_thang,
        "phan_tram_ngan_sach": round(_ti_le(tong_usd, cfg.ngan_sach_usd_thang) * 100, 2),
    }


# ── KPI (plan mục 12) ────────────────────────────────────────────────────────


def _thoi_gian_giay(created_at: Any, updated_at: Any) -> float | None:
    """Hiệu hai mốc ISO trên job; `None` nếu thiếu hoặc sai định dạng.

    Không suy đoán, không thay bằng "bây giờ" — job chưa kết thúc thì chưa có
    thời lượng, và việc đó phải hiện ra là thiếu dữ liệu chứ không phải 0 giây.
    """
    if not isinstance(created_at, str) or not isinstance(updated_at, str):
        return None
    try:
        start = datetime.fromisoformat(created_at)
        end = datetime.fromisoformat(updated_at)
    except ValueError:
        return None
    delta = (end - start).total_seconds()
    return delta if delta >= 0 else None


def tinh_thoi_gian_trung_binh(jobs: Iterable[Any]) -> dict[str, Any]:
    """Thời lượng trung bình của các job ĐÃ KẾT THÚC (completed/failed).

    Chỉ tính job đã đóng: gộp job đang chạy vào sẽ kéo trung bình xuống và che mất
    việc khảo sát đang chậm. `so_job_dang_chay` trả riêng để UI nói rõ.
    """
    ket_thuc = {"completed", "failed"}
    thoi_luong: list[float] = []
    dang_chay = 0
    for job in jobs:
        trang_thai = getattr(getattr(job, "status", None), "value", None) or getattr(job, "status", None)
        if trang_thai not in ket_thuc:
            dang_chay += 1
            continue
        giay = _thoi_gian_giay(getattr(job, "created_at", None), getattr(job, "updated_at", None))
        if giay is not None:
            thoi_luong.append(giay)

    if not thoi_luong:
        return {
            "so_job_da_ket_thuc": 0,
            "so_job_dang_chay": dang_chay,
            "thoi_gian_trung_binh_giay": None,
            "thoi_gian_dai_nhat_giay": None,
            "dat_muc_tieu": None,
        }
    trung_binh = sum(thoi_luong) / len(thoi_luong)
    return {
        "so_job_da_ket_thuc": len(thoi_luong),
        "so_job_dang_chay": dang_chay,
        "thoi_gian_trung_binh_giay": round(trung_binh, 2),
        "thoi_gian_dai_nhat_giay": round(max(thoi_luong), 2),
        "dat_muc_tieu": trung_binh <= KPI_THOI_GIAN_TRUNG_BINH_TOI_DA_GIAY,
    }


def tinh_kpi(
    metrics: Mapping[str, Any],
    jobs: Sequence[Any] = (),
    *,
    source_block: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Gom KPI thí điểm (plan mục 12) từ metrics + job store + thống kê block.

    `ti_le_can_review` dùng `jobs_needs_review / jobs_created` — plan định nghĩa
    theo "tổng số bản ghi giá", nhưng số bản ghi giá không được đếm ở tầng metrics
    hiện có. Tỷ lệ theo job là xấp xỉ bảo thủ (một job review có thể chứa nhiều
    dòng), nên ghi rõ công thức trong payload để không ai đọc nhầm.
    """
    created = _nguyen(metrics.get("jobs_created"))
    completed = _nguyen(metrics.get("jobs_completed"))
    failed = _nguyen(metrics.get("jobs_failed"))
    needs_review = _nguyen(metrics.get("jobs_needs_review"))

    ti_le_hoan_tat = _ti_le(completed, created)
    ti_le_can_review = _ti_le(needs_review, created)

    failures = metrics.get("failures_by_code") or {}
    blocked = _nguyen(failures.get("SOURCE_BLOCKED") if isinstance(failures, Mapping) else 0)

    tong_luot_nguon = 0
    tong_bi_chan = 0
    for stats in (source_block or {}).values():
        tong_luot_nguon += _nguyen(stats.get("total_requests"))
        tong_bi_chan += _nguyen(stats.get("blocked_count"))
    ti_le_block_nguon = _ti_le(tong_bi_chan, tong_luot_nguon)

    return {
        "jobs_created": int(created),
        "jobs_completed": int(completed),
        "jobs_failed": int(failed),
        "jobs_needs_review": int(needs_review),
        "ti_le_hoan_tat": round(ti_le_hoan_tat, 4),
        "ti_le_hoan_tat_muc_tieu": KPI_TI_LE_HOAN_TAT_TOI_THIEU,
        "ti_le_can_review": round(ti_le_can_review, 4),
        "ti_le_can_review_muc_tieu": KPI_TI_LE_CAN_REVIEW_TOI_DA,
        "ti_le_can_review_cong_thuc": "jobs_needs_review / jobs_created",
        "failures_by_code": dict(failures) if isinstance(failures, Mapping) else {},
        "so_job_chet_vi_source_blocked": int(blocked),
        "nguon_tong_luot": int(tong_luot_nguon),
        "nguon_bi_chan": int(tong_bi_chan),
        "ti_le_source_blocked": round(ti_le_block_nguon, 4),
        "thoi_gian": tinh_thoi_gian_trung_binh(jobs),
    }


# ── Alerting (plan mục 9) ────────────────────────────────────────────────────


def tinh_canh_bao(
    kpi: Mapping[str, Any],
    chi_phi: Mapping[str, Any],
    alert: AlertConfig | None = None,
) -> list[dict[str, Any]]:
    """Danh sách cảnh báo, mức nặng trước. Rỗng nghĩa là vận hành bình thường.

    Hai nguyên tắc cố ý:
      - Dưới `source_blocked_mau_toi_thieu` lượt thì KHÔNG báo động: 1/2 lượt bị
        chặn là 50% nhưng chưa nói lên nền tảng đã siết bot, chỉ là nhiễu.
      - Vượt ngân sách là `nghiem_trong` nhưng chỉ CẢNH BÁO — không tự tắt tính
        năng. Quyết định dừng chi tiền là của con người (ADR-008).
    """
    cfg = alert or get_pricing_config().canh_bao
    canh_bao: list[CanhBao] = []

    ti_le_block = _so(kpi.get("ti_le_source_blocked"))
    mau = _nguyen(kpi.get("nguon_tong_luot"))
    nguong = cfg.source_blocked_nguong_phan_tram / 100.0
    if mau >= cfg.source_blocked_mau_toi_thieu and ti_le_block > nguong:
        canh_bao.append(
            CanhBao(
                ma="SOURCE_BLOCKED_VUOT_NGUONG",
                muc=MUC_NGHIEM_TRONG,
                thong_diep=(
                    f"Nguồn dữ liệu đang chặn {ti_le_block * 100:.1f}% lượt truy cập "
                    f"(ngưỡng {cfg.source_blocked_nguong_phan_tram:.0f}% trên {mau} lượt). "
                    "Dấu hiệu nền tảng đã siết chống bot — giảm tần suất crawl và kiểm tra "
                    "lại chiến lược trước khi chạy tiếp."
                ),
                gia_tri=round(ti_le_block, 4),
                nguong=round(nguong, 4),
            )
        )

    phan_tram_ngan_sach = _so(chi_phi.get("phan_tram_ngan_sach"))
    if phan_tram_ngan_sach >= 100.0:
        canh_bao.append(
            CanhBao(
                ma="VUOT_NGAN_SACH",
                muc=MUC_NGHIEM_TRONG,
                thong_diep=(
                    f"Chi phí khảo sát đã dùng {phan_tram_ngan_sach:.0f}% ngân sách tháng "
                    f"({_so(chi_phi.get('tong_usd')):.2f} USD / "
                    f"{_so(chi_phi.get('ngan_sach_usd_thang')):.2f} USD). "
                    "Cần người quyết định có tiếp tục chi hay không — hệ thống không tự tắt."
                ),
                gia_tri=round(phan_tram_ngan_sach, 2),
                nguong=100.0,
            )
        )
    elif phan_tram_ngan_sach >= 80.0:
        canh_bao.append(
            CanhBao(
                ma="GAN_NGAN_SACH",
                muc=MUC_CANH_BAO,
                thong_diep=(
                    f"Đã dùng {phan_tram_ngan_sach:.0f}% ngân sách Vision + proxy tháng này. "
                    "Còn dưới 20% thì nên giãn lượng khảo sát."
                ),
                gia_tri=round(phan_tram_ngan_sach, 2),
                nguong=80.0,
            )
        )

    ti_le_hoan_tat = _so(kpi.get("ti_le_hoan_tat"))
    if _nguyen(kpi.get("jobs_created")) >= cfg.source_blocked_mau_toi_thieu and (
        ti_le_hoan_tat < KPI_TI_LE_HOAN_TAT_TOI_THIEU
    ):
        canh_bao.append(
            CanhBao(
                ma="TI_LE_HOAN_TAT_THAP",
                muc=MUC_CANH_BAO,
                thong_diep=(
                    f"Chỉ {ti_le_hoan_tat * 100:.1f}% khảo sát chạy tới kết quả "
                    f"(mục tiêu ≥ {KPI_TI_LE_HOAN_TAT_TOI_THIEU * 100:.0f}%). "
                    "Xem `failures_by_code` để biết lỗi nằm ở nguồn hay ở bước đọc ảnh."
                ),
                gia_tri=round(ti_le_hoan_tat, 4),
                nguong=KPI_TI_LE_HOAN_TAT_TOI_THIEU,
            )
        )

    ti_le_can_review = _so(kpi.get("ti_le_can_review"))
    if _nguyen(kpi.get("jobs_created")) >= cfg.source_blocked_mau_toi_thieu and (
        ti_le_can_review > KPI_TI_LE_CAN_REVIEW_TOI_DA
    ):
        canh_bao.append(
            CanhBao(
                ma="TI_LE_CAN_REVIEW_CAO",
                muc=MUC_THONG_TIN,
                thong_diep=(
                    f"{ti_le_can_review * 100:.1f}% khảo sát phải dừng chờ chủ quán xác nhận giá "
                    f"(mục tiêu ≤ {KPI_TI_LE_CAN_REVIEW_TOI_DA * 100:.0f}%). "
                    "Đây là hành vi đúng theo ADR-008, nhưng tỷ lệ cao nghĩa là ảnh thực đơn "
                    "đang kém chất lượng hoặc ngưỡng guardrail quá chặt."
                ),
                gia_tri=round(ti_le_can_review, 4),
                nguong=KPI_TI_LE_CAN_REVIEW_TOI_DA,
            )
        )

    thu_tu = {MUC_NGHIEM_TRONG: 0, MUC_CANH_BAO: 1, MUC_THONG_TIN: 2}
    canh_bao.sort(key=lambda c: thu_tu.get(c.muc, 9))
    return [
        {
            "ma": c.ma,
            "muc": c.muc,
            "thong_diep": c.thong_diep,
            "gia_tri": c.gia_tri,
            "nguong": c.nguong,
        }
        for c in canh_bao
    ]


def tong_hop_dashboard(
    metrics: Mapping[str, Any],
    jobs: Sequence[Any] = (),
    *,
    source_block: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Payload đầy đủ cho cost dashboard: chi phí + KPI + cảnh báo.

    Một hàm duy nhất để API và test dùng chung một định nghĩa — tránh hai nơi
    tính "chi phí mỗi khảo sát" theo hai công thức khác nhau.
    """
    chi_phi = tinh_chi_phi(metrics)
    kpi = tinh_kpi(metrics, jobs, source_block=source_block)
    # `dict(metrics)` là copy NÔNG: `failures_by_code` vẫn trỏ về dict gốc, nên ai
    # sửa payload trả về sẽ đổi luôn counter thật của orchestrator. Tách riêng.
    metrics_tho = dict(metrics)
    failures = metrics_tho.get("failures_by_code")
    if isinstance(failures, Mapping):
        metrics_tho["failures_by_code"] = dict(failures)
    return {
        "chi_phi": chi_phi,
        "kpi": kpi,
        "canh_bao": tinh_canh_bao(kpi, chi_phi),
        "metrics_tho": metrics_tho,
    }
