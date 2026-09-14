"""Test cost dashboard & KPI khảo sát giá (plan `260913-1455` mục 9 và 12).

Ba điều test này phải chứng minh, vì đây là chỗ dễ "làm cho đẹp số liệu" nhất:

1. **Hàm thuần** — cùng input ra cùng output, không đọc đồng hồ, không đọc đĩa.
2. **Không bịa số** — thiếu dữ liệu thì trả `None`/0, không suy đoán. Đặc biệt:
   job đang chạy KHÔNG được tính vào thời lượng trung bình (sẽ kéo trung bình xuống
   và che mất việc khảo sát đang chậm).
3. **Cảnh báo không kêu oan** — dưới ngưỡng mẫu tối thiểu thì im lặng, vì 1/2 lượt
   bị chặn là 50% nhưng chưa nói lên nền tảng đã siết bot.

Không network, không LLM, không DB.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ca_agents.ag_pricing.cost_dashboard import (
    KPI_THOI_GIAN_TRUNG_BINH_TOI_DA_GIAY,
    KPI_TI_LE_CAN_REVIEW_TOI_DA,
    KPI_TI_LE_HOAN_TAT_TOI_THIEU,
    MUC_CANH_BAO,
    MUC_NGHIEM_TRONG,
    MUC_THONG_TIN,
    tinh_canh_bao,
    tinh_chi_phi,
    tinh_kpi,
    tinh_thoi_gian_trung_binh,
    tong_hop_dashboard,
)
from ca_agents.ag_pricing.pricing_config import AlertConfig, CostConfig


@dataclass
class JobGia:
    """Job tối giản đủ trường cho dashboard — không cần SurveyJob thật."""

    status: str
    created_at: str = ""
    updated_at: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


def _metrics(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "jobs_created": 0,
        "jobs_completed": 0,
        "jobs_failed": 0,
        "jobs_needs_review": 0,
        "failures_by_code": {},
        "vision_calls": 0,
        "vision_errors": 0,
        "images_downloaded": 0,
        "images_failed": 0,
        "image_bytes_downloaded": 0,
        "proxy_requests": 0,
    }
    base.update(overrides)
    return base


# ── 1. Chi phí ───────────────────────────────────────────────────────────────


def test_chi_phi_tinh_dung_theo_don_gia_config() -> None:
    cost = CostConfig(vision_usd_moi_anh=0.0025, proxy_usd_moi_luot=0.002, ngan_sach_usd_thang=50.0)
    ket_qua = tinh_chi_phi(_metrics(vision_calls=100, proxy_requests=10, jobs_created=5), cost)

    assert ket_qua["vision_usd"] == 0.25
    assert ket_qua["proxy_usd"] == 0.02
    assert ket_qua["tong_usd"] == 0.27
    assert ket_qua["chi_phi_moi_job_usd"] == 0.054
    assert ket_qua["phan_tram_ngan_sach"] == 0.54


def test_chi_phi_khong_co_job_thi_khong_no() -> None:
    """Chia cho 0 job phải ra 0, không phải ZeroDivisionError hay NaN."""
    ket_qua = tinh_chi_phi(_metrics(), CostConfig())
    assert ket_qua["chi_phi_moi_job_usd"] == 0
    assert ket_qua["tong_usd"] == 0


def test_chi_phi_thieu_khoa_thi_coi_nhu_khong() -> None:
    """Metrics cũ chưa có `proxy_requests` vẫn phải đọc được — không được nổ."""
    ket_qua = tinh_chi_phi({"vision_calls": 4}, CostConfig(vision_usd_moi_anh=0.01))
    assert ket_qua["proxy_luot"] == 0
    assert ket_qua["vision_usd"] == 0.04


def test_chi_phi_gia_tri_rac_khong_lam_nan() -> None:
    ket_qua = tinh_chi_phi(
        {"vision_calls": "khong-phai-so", "proxy_requests": None, "jobs_created": float("nan")},
        CostConfig(),
    )
    assert ket_qua["vision_luot"] == 0
    assert ket_qua["tong_usd"] == 0
    assert ket_qua["chi_phi_moi_job_usd"] == 0


def test_chi_phi_la_ham_thuan() -> None:
    """ADR-002: gọi hai lần cùng input phải ra đúng một kết quả."""
    metrics = _metrics(vision_calls=7, proxy_requests=3, jobs_created=2)
    cost = CostConfig()
    assert tinh_chi_phi(metrics, cost) == tinh_chi_phi(metrics, cost)


# ── 2. Thời lượng job ────────────────────────────────────────────────────────


def test_thoi_gian_chi_tinh_job_da_ket_thuc() -> None:
    jobs = [
        JobGia("completed", "2026-09-13T10:00:00+00:00", "2026-09-13T10:02:00+00:00"),
        JobGia("failed", "2026-09-13T11:00:00+00:00", "2026-09-13T11:01:00+00:00"),
        JobGia("scraping_online", "2026-09-13T12:00:00+00:00", "2026-09-13T12:00:10+00:00"),
    ]
    ket_qua = tinh_thoi_gian_trung_binh(jobs)

    assert ket_qua["so_job_da_ket_thuc"] == 2
    assert ket_qua["so_job_dang_chay"] == 1
    # (120 + 60) / 2 — job đang chạy 10s KHÔNG được kéo trung bình xuống
    assert ket_qua["thoi_gian_trung_binh_giay"] == 90.0
    assert ket_qua["thoi_gian_dai_nhat_giay"] == 120.0
    assert ket_qua["dat_muc_tieu"] is True


def test_thoi_gian_vuot_muc_tieu_thi_bao_khong_dat() -> None:
    # 4 phút > mục tiêu 3 phút của plan mục 12
    jobs = [JobGia("completed", "2026-09-13T10:00:00+00:00", "2026-09-13T10:04:00+00:00")]
    ket_qua = tinh_thoi_gian_trung_binh(jobs)
    assert ket_qua["thoi_gian_trung_binh_giay"] == 240.0
    assert ket_qua["thoi_gian_trung_binh_giay"] > KPI_THOI_GIAN_TRUNG_BINH_TOI_DA_GIAY
    assert ket_qua["dat_muc_tieu"] is False


def test_thoi_gian_khong_co_job_ket_thuc_thi_tra_none() -> None:
    """Không có dữ liệu thì nói là không có — không trả 0 (0 giây là một con số sai)."""
    ket_qua = tinh_thoi_gian_trung_binh([JobGia("queued", "", "")])
    assert ket_qua["thoi_gian_trung_binh_giay"] is None
    assert ket_qua["dat_muc_tieu"] is None
    assert ket_qua["so_job_dang_chay"] == 1


def test_thoi_gian_bo_qua_moc_sai_dinh_dang() -> None:
    jobs = [
        JobGia("completed", "khong-phai-ngay", "2026-09-13T10:02:00+00:00"),
        JobGia("completed", "2026-09-13T10:00:00+00:00", ""),
        JobGia("completed", "2026-09-13T10:00:00+00:00", "2026-09-13T09:00:00+00:00"),  # âm
        JobGia("completed", "2026-09-13T10:00:00+00:00", "2026-09-13T10:01:00+00:00"),
    ]
    ket_qua = tinh_thoi_gian_trung_binh(jobs)
    assert ket_qua["so_job_da_ket_thuc"] == 1
    assert ket_qua["thoi_gian_trung_binh_giay"] == 60.0


def test_thoi_gian_chap_nhan_enum_status() -> None:
    """Job thật mang `SurveyJobStatus` enum, không phải chuỗi — phải đọc được cả hai."""

    class EnumGia:
        value = "completed"

    jobs = [JobGia(EnumGia(), "2026-09-13T10:00:00+00:00", "2026-09-13T10:00:30+00:00")]  # type: ignore[arg-type]
    ket_qua = tinh_thoi_gian_trung_binh(jobs)
    assert ket_qua["so_job_da_ket_thuc"] == 1
    assert ket_qua["thoi_gian_trung_binh_giay"] == 30.0


# ── 3. KPI ───────────────────────────────────────────────────────────────────


def test_kpi_tinh_dung_cac_ti_le() -> None:
    metrics = _metrics(
        jobs_created=20,
        jobs_completed=17,
        jobs_failed=2,
        jobs_needs_review=3,
        failures_by_code={"SOURCE_BLOCKED": 2},
    )
    kpi = tinh_kpi(metrics)

    assert kpi["ti_le_hoan_tat"] == 0.85
    assert kpi["ti_le_can_review"] == 0.15
    assert kpi["so_job_chet_vi_source_blocked"] == 2
    assert kpi["ti_le_hoan_tat_muc_tieu"] == KPI_TI_LE_HOAN_TAT_TOI_THIEU
    assert kpi["ti_le_can_review_muc_tieu"] == KPI_TI_LE_CAN_REVIEW_TOI_DA


def test_kpi_ghi_ro_cong_thuc_de_khong_doc_nham() -> None:
    """Tỷ lệ review tính theo JOB chứ không theo dòng giá — payload phải nói rõ."""
    assert tinh_kpi(_metrics())["ti_le_can_review_cong_thuc"] == (
        "jobs_needs_review / jobs_created"
    )


def test_kpi_gom_block_rate_tu_nhieu_nguon() -> None:
    block = {
        "gmaps": {"total_requests": 80, "blocked_count": 8},
        "shopeefood": {"total_requests": 20, "blocked_count": 1},
    }
    kpi = tinh_kpi(_metrics(), source_block=block)
    assert kpi["nguon_tong_luot"] == 100
    assert kpi["nguon_bi_chan"] == 9
    assert kpi["ti_le_source_blocked"] == 0.09


def test_kpi_khong_co_job_thi_ti_le_bang_khong() -> None:
    kpi = tinh_kpi(_metrics())
    assert kpi["ti_le_hoan_tat"] == 0
    assert kpi["ti_le_can_review"] == 0
    assert kpi["ti_le_source_blocked"] == 0


def test_kpi_failures_by_code_khong_phai_mapping_van_doc_duoc() -> None:
    kpi = tinh_kpi({"jobs_created": 1, "failures_by_code": "hong"})
    assert kpi["failures_by_code"] == {}
    assert kpi["so_job_chet_vi_source_blocked"] == 0


# ── 4. Cảnh báo ──────────────────────────────────────────────────────────────


def _alert_cfg(mau_toi_thieu: int = 20) -> AlertConfig:
    return AlertConfig(source_blocked_nguong_phan_tram=15.0, source_blocked_mau_toi_thieu=mau_toi_thieu)


def test_canh_bao_bao_khi_block_vuot_nguong() -> None:
    kpi = {"ti_le_source_blocked": 0.20, "nguon_tong_luot": 100, "jobs_created": 30,
           "ti_le_hoan_tat": 0.9, "ti_le_can_review": 0.1}
    canh_bao = tinh_canh_bao(kpi, {"phan_tram_ngan_sach": 10.0, "tong_usd": 5.0,
                                   "ngan_sach_usd_thang": 50.0}, _alert_cfg())
    ma = [c["ma"] for c in canh_bao]
    assert "SOURCE_BLOCKED_VUOT_NGUONG" in ma
    nghiem_trong = next(c for c in canh_bao if c["ma"] == "SOURCE_BLOCKED_VUOT_NGUONG")
    assert nghiem_trong["muc"] == MUC_NGHIEM_TRONG
    assert nghiem_trong["nguong"] == 0.15


def test_canh_bao_im_lang_khi_chua_du_mau() -> None:
    """1/2 lượt bị chặn = 50% nhưng là NHIỄU, không phải tín hiệu nền tảng siết bot."""
    kpi = {"ti_le_source_blocked": 0.5, "nguon_tong_luot": 2, "jobs_created": 1,
           "ti_le_hoan_tat": 1.0, "ti_le_can_review": 0.0}
    canh_bao = tinh_canh_bao(kpi, {"phan_tram_ngan_sach": 0.0}, _alert_cfg())
    assert [c["ma"] for c in canh_bao] == []


def test_canh_bao_dung_ngay_nguong_thi_khong_bao() -> None:
    """Plan viết ">15%", nên đúng 15% là chưa vượt — không được làm tròn lên."""
    kpi = {"ti_le_source_blocked": 0.15, "nguon_tong_luot": 100, "jobs_created": 30,
           "ti_le_hoan_tat": 0.9, "ti_le_can_review": 0.1}
    canh_bao = tinh_canh_bao(kpi, {"phan_tram_ngan_sach": 0.0}, _alert_cfg())
    assert "SOURCE_BLOCKED_VUOT_NGUONG" not in [c["ma"] for c in canh_bao]


def test_canh_bao_vuot_ngan_sach_la_nghiem_trong_nhung_khong_tu_tat() -> None:
    """ADR-008: vượt tiền là chuyện con người quyết, hệ thống chỉ báo."""
    kpi = {"ti_le_source_blocked": 0.0, "nguon_tong_luot": 0, "jobs_created": 0,
           "ti_le_hoan_tat": 0.0, "ti_le_can_review": 0.0}
    canh_bao = tinh_canh_bao(
        kpi,
        {"phan_tram_ngan_sach": 120.0, "tong_usd": 60.0, "ngan_sach_usd_thang": 50.0},
        _alert_cfg(),
    )
    assert len(canh_bao) == 1
    assert canh_bao[0]["ma"] == "VUOT_NGAN_SACH"
    assert canh_bao[0]["muc"] == MUC_NGHIEM_TRONG
    assert "không tự tắt" in canh_bao[0]["thong_diep"]


def test_canh_bao_gan_ngan_sach_o_muc_canh_bao() -> None:
    kpi = {"ti_le_source_blocked": 0.0, "nguon_tong_luot": 0, "jobs_created": 0,
           "ti_le_hoan_tat": 0.0, "ti_le_can_review": 0.0}
    canh_bao = tinh_canh_bao(kpi, {"phan_tram_ngan_sach": 85.0}, _alert_cfg())
    assert canh_bao[0]["ma"] == "GAN_NGAN_SACH"
    assert canh_bao[0]["muc"] == MUC_CANH_BAO


def test_canh_bao_ti_le_hoan_tat_thap() -> None:
    kpi = {"ti_le_source_blocked": 0.0, "nguon_tong_luot": 0, "jobs_created": 40,
           "ti_le_hoan_tat": 0.60, "ti_le_can_review": 0.1}
    canh_bao = tinh_canh_bao(kpi, {"phan_tram_ngan_sach": 0.0}, _alert_cfg())
    assert [c["ma"] for c in canh_bao] == ["TI_LE_HOAN_TAT_THAP"]


def test_canh_bao_review_cao_chi_o_muc_thong_tin() -> None:
    """NEEDS_REVIEW là hành vi ĐÚNG theo ADR-008 — không được báo như sự cố."""
    kpi = {"ti_le_source_blocked": 0.0, "nguon_tong_luot": 0, "jobs_created": 40,
           "ti_le_hoan_tat": 0.9, "ti_le_can_review": 0.30}
    canh_bao = tinh_canh_bao(kpi, {"phan_tram_ngan_sach": 0.0}, _alert_cfg())
    assert len(canh_bao) == 1
    assert canh_bao[0]["ma"] == "TI_LE_CAN_REVIEW_CAO"
    assert canh_bao[0]["muc"] == MUC_THONG_TIN


def test_canh_bao_sap_xep_muc_nang_truoc() -> None:
    kpi = {"ti_le_source_blocked": 0.5, "nguon_tong_luot": 100, "jobs_created": 40,
           "ti_le_hoan_tat": 0.30, "ti_le_can_review": 0.40}
    canh_bao = tinh_canh_bao(
        kpi, {"phan_tram_ngan_sach": 150.0, "tong_usd": 75.0, "ngan_sach_usd_thang": 50.0},
        _alert_cfg(),
    )
    muc = [c["muc"] for c in canh_bao]
    assert muc == sorted(muc, key=lambda m: {MUC_NGHIEM_TRONG: 0, MUC_CANH_BAO: 1, MUC_THONG_TIN: 2}[m])
    assert muc[0] == MUC_NGHIEM_TRONG


def test_canh_bao_rong_khi_van_hanh_binh_thuong() -> None:
    kpi = {"ti_le_source_blocked": 0.02, "nguon_tong_luot": 500, "jobs_created": 100,
           "ti_le_hoan_tat": 0.92, "ti_le_can_review": 0.08}
    assert tinh_canh_bao(kpi, {"phan_tram_ngan_sach": 20.0}, _alert_cfg()) == []


# ── 5. Payload tổng hợp ──────────────────────────────────────────────────────


def test_tong_hop_dashboard_co_du_ba_khoi() -> None:
    data = tong_hop_dashboard(
        _metrics(jobs_created=2, jobs_completed=2, vision_calls=10, proxy_requests=4),
        [JobGia("completed", "2026-09-13T10:00:00+00:00", "2026-09-13T10:02:00+00:00")],
        source_block={"gmaps": {"total_requests": 10, "blocked_count": 0}},
    )
    assert set(data) == {"chi_phi", "kpi", "canh_bao", "metrics_tho"}
    assert data["kpi"]["ti_le_hoan_tat"] == 1.0
    assert data["chi_phi"]["vision_luot"] == 10
    assert isinstance(data["canh_bao"], list)


def test_tong_hop_dashboard_khong_lam_hong_metrics_goc() -> None:
    """Snapshot metrics phải được copy — sửa payload trả về không được đổi counter thật."""
    metrics = _metrics(jobs_created=1, failures_by_code={"SOURCE_BLOCKED": 1})
    data = tong_hop_dashboard(metrics)
    data["metrics_tho"]["jobs_created"] = 999
    data["metrics_tho"]["failures_by_code"]["SOURCE_BLOCKED"] = 999
    assert metrics["jobs_created"] == 1
    assert metrics["failures_by_code"] == {"SOURCE_BLOCKED": 1}
