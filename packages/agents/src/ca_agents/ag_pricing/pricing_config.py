"""Loader tất định cho tham số nghiệp vụ khảo sát giá (plan mục 1.5, 3.4).

ADR-002: module này chỉ ĐỌC cấu hình — không suy luận, không LLM, không network.
Toàn bộ con số nghiệp vụ nằm ở `config/khao-sat-gia-tham-so.yaml`; các khóa gắn
nhãn `BUSINESS_DECISION_PENDING_REVIEW` là ĐỀ XUẤT chưa được chủ dự án chốt
(plan mục 1.5: "Không tự chốt thay chủ dự án các tham số nghiệp vụ").

Loader fail-fast: thiếu khóa hoặc sai kiểu → `PricingConfigError`, không âm thầm
rơi về default khác với file cấu hình.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[5]
CONFIG_PATH = ROOT / "config" / "khao-sat-gia-tham-so.yaml"


class PricingConfigError(ValueError):
    """Cấu hình tham số khảo sát giá thiếu hoặc sai kiểu."""


@dataclass(frozen=True, slots=True)
class PercentileConfig:
    """Plan mục 4.1."""

    method: str = "linear"
    min_sample_size: int = 5
    gia_hop_le_toi_thieu_vnd: int = 5000
    gia_hop_le_toi_da_vnd: int = 2000000


@dataclass(frozen=True, slots=True)
class DualGateConfig:
    """Plan mục 1.4 / 4.2."""

    min_review_count: int = 50
    min_rating: float = 4.2
    min_weighted_rating: float = 4.0
    bayes_m: int = 50
    bayes_prior_c: float = 4.2
    distance_decay_alpha: float = 0.15
    low_confidence_review_threshold: int = 10
    low_confidence_weight_factor: float = 0.5


@dataclass(frozen=True, slots=True)
class AmbiConfig:
    """Plan mục 1.3 / 4.3."""

    trong_so_core: float = 0.5
    trong_so_substitutes: float = 0.5
    he_so_vung_rui_ro: float = 1.2


@dataclass(frozen=True, slots=True)
class SweetSpotConfig:
    """Plan mục 4.4 — [ĐỀ XUẤT MỚI], chờ chủ dự án duyệt công thức."""

    phan_vi_canh_duoi: float = 40.0
    phan_vi_canh_tren: float = 60.0
    dung_gia_goc: bool = True
    tach_theo_tang_dinh_vi: bool = True
    loai_tru_combo: bool = True


@dataclass(frozen=True, slots=True)
class CostPlusConfig:
    """Plan mục 1.5.1 / 4.4.2."""

    target_margin_ratio_mac_dinh: float = 0.30


@dataclass(frozen=True, slots=True)
class CostConfig:
    """Plan mục 9 — suất chi phí biến đổi để quy số lượt gọi thành tiền.

    Đơn giá là ước lượng từ bảng giá công khai, chưa được chủ dự án duyệt
    (nhãn `BUSINESS_DECISION_PENDING_REVIEW` trong file config).
    """

    vision_usd_moi_anh: float = 0.0025
    proxy_usd_moi_luot: float = 0.002
    ngan_sach_usd_thang: float = 50.0


@dataclass(frozen=True, slots=True)
class AlertConfig:
    """Plan mục 9 — ngưỡng cảnh báo nguồn bị chặn."""

    source_blocked_nguong_phan_tram: float = 15.0
    source_blocked_mau_toi_thieu: int = 20


@dataclass(frozen=True, slots=True)
class PricingConfig:
    """Toàn bộ tham số nghiệp vụ của AG-PRICING Math Layer."""

    phien_ban: str = "1.0.0"
    schema_version_hop_dong: str = "2.1"
    phan_vi: PercentileConfig = PercentileConfig()
    dual_gate: DualGateConfig = DualGateConfig()
    radius_profile_mac_dinh: tuple[float, float] = (1.0, 5.0)
    ambi: AmbiConfig = AmbiConfig()
    sweet_spot: SweetSpotConfig = SweetSpotConfig()
    lam_tron_hien_thi: tuple[int, int, int] = (1000, 5000, 5000)
    cost_plus: CostPlusConfig = CostPlusConfig()
    chi_phi: CostConfig = CostConfig()
    canh_bao: AlertConfig = AlertConfig()
    pi: float = 3.14159
    ocr_nguong_lech_sigma: float = 2.0
    ocr_confidence_can_review: str = "low"


def _mapping(data: Any, key: str, source: str) -> dict[str, Any]:
    section = data.get(key)
    if not isinstance(section, dict):
        raise PricingConfigError(f"{source}: thiếu section mapping '{key}'")
    return section


def _require(section: dict[str, Any], key: str, source: str) -> Any:
    if key not in section:
        raise PricingConfigError(f"{source}: thiếu khóa '{key}'")
    return section[key]


def _mapping_tuy_chon(data: Any, key: str) -> dict[str, Any] | None:
    """Section có thể vắng mặt; nếu CÓ mặt thì phải là mapping.

    Dùng cho các section thêm sau (`chi_phi`, `canh_bao` — plan mục 9) để config
    cũ vẫn parse được. Bên trong section thì vẫn fail-fast từng khóa: vắng cả
    section khác với viết nửa vời một section.
    """
    if key not in data:
        return None
    section = data[key]
    if not isinstance(section, dict):
        raise PricingConfigError(f"{key}: thiếu section mapping '{key}'")
    return section


def _as_float(section: dict[str, Any], key: str, source: str) -> float:
    raw = _require(section, key, source)
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise PricingConfigError(f"{source}: '{key}' phải là số, nhận {raw!r}") from exc


def _as_int(section: dict[str, Any], key: str, source: str) -> int:
    raw = _require(section, key, source)
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise PricingConfigError(f"{source}: '{key}' phải là số nguyên, nhận {raw!r}") from exc


def _as_bool(section: dict[str, Any], key: str, source: str) -> bool:
    raw = _require(section, key, source)
    if not isinstance(raw, bool):
        raise PricingConfigError(f"{source}: '{key}' phải là bool, nhận {raw!r}")
    return raw


def _as_str(section: dict[str, Any], key: str, source: str) -> str:
    raw = _require(section, key, source)
    if not isinstance(raw, str) or not raw.strip():
        raise PricingConfigError(f"{source}: '{key}' phải là chuỗi không rỗng, nhận {raw!r}")
    return raw.strip()


def parse_pricing_config(data: Any) -> PricingConfig:
    """Hàm THUẦN: dict YAML → PricingConfig. Test được bằng fixture, không đọc đĩa."""
    if not isinstance(data, dict):
        raise PricingConfigError("config khảo sát giá phải là mapping ở gốc")

    phan_vi = _mapping(data, "phan_vi", "phan_vi")
    gate = _mapping(data, "dual_gate", "dual_gate")
    ambi = _mapping(data, "ambi", "ambi")
    sweet = _mapping(data, "sweet_spot", "sweet_spot")
    lam_tron = _mapping(data, "lam_tron_hien_thi", "lam_tron_hien_thi")
    cost_plus = _mapping(data, "cost_plus", "cost_plus")
    canh_tranh = _mapping(data, "canh_tranh", "canh_tranh")
    ocr = _mapping(data, "ocr_guardrail", "ocr_guardrail")
    radius = _mapping(data, "radius_profile_mac_dinh", "radius_profile_mac_dinh")
    chi_phi = _mapping_tuy_chon(data, "chi_phi")
    canh_bao = _mapping_tuy_chon(data, "canh_bao")

    return PricingConfig(
        phien_ban=_as_str(data, "phien_ban", "root"),
        schema_version_hop_dong=_as_str(data, "schema_version_hop_dong", "root"),
        phan_vi=PercentileConfig(
            method=_as_str(phan_vi, "method", "phan_vi"),
            min_sample_size=_as_int(phan_vi, "min_sample_size", "phan_vi"),
            gia_hop_le_toi_thieu_vnd=_as_int(phan_vi, "gia_hop_le_toi_thieu_vnd", "phan_vi"),
            gia_hop_le_toi_da_vnd=_as_int(phan_vi, "gia_hop_le_toi_da_vnd", "phan_vi"),
        ),
        dual_gate=DualGateConfig(
            min_review_count=_as_int(gate, "min_review_count", "dual_gate"),
            min_rating=_as_float(gate, "min_rating", "dual_gate"),
            min_weighted_rating=_as_float(gate, "min_weighted_rating", "dual_gate"),
            bayes_m=_as_int(gate, "bayes_m", "dual_gate"),
            bayes_prior_c=_as_float(gate, "bayes_prior_c", "dual_gate"),
            distance_decay_alpha=_as_float(gate, "distance_decay_alpha", "dual_gate"),
            low_confidence_review_threshold=_as_int(
                gate, "low_confidence_review_threshold", "dual_gate"
            ),
            low_confidence_weight_factor=_as_float(
                gate, "low_confidence_weight_factor", "dual_gate"
            ),
        ),
        radius_profile_mac_dinh=(
            _as_float(radius, "dine_in_km", "radius_profile_mac_dinh"),
            _as_float(radius, "delivery_km", "radius_profile_mac_dinh"),
        ),
        ambi=AmbiConfig(
            trong_so_core=_as_float(ambi, "trong_so_core", "ambi"),
            trong_so_substitutes=_as_float(ambi, "trong_so_substitutes", "ambi"),
            he_so_vung_rui_ro=_as_float(ambi, "he_so_vung_rui_ro", "ambi"),
        ),
        sweet_spot=SweetSpotConfig(
            phan_vi_canh_duoi=_as_float(sweet, "phan_vi_canh_duoi", "sweet_spot"),
            phan_vi_canh_tren=_as_float(sweet, "phan_vi_canh_tren", "sweet_spot"),
            dung_gia_goc=_as_bool(sweet, "dung_gia_goc", "sweet_spot"),
            tach_theo_tang_dinh_vi=_as_bool(sweet, "tach_theo_tang_dinh_vi", "sweet_spot"),
            loai_tru_combo=_as_bool(sweet, "loai_tru_combo", "sweet_spot"),
        ),
        lam_tron_hien_thi=(
            _as_int(lam_tron, "beverage", "lam_tron_hien_thi"),
            _as_int(lam_tron, "mon_chinh", "lam_tron_hien_thi"),
            _as_int(lam_tron, "mac_dinh", "lam_tron_hien_thi"),
        ),
        cost_plus=CostPlusConfig(
            target_margin_ratio_mac_dinh=_as_float(
                cost_plus, "target_margin_ratio_mac_dinh", "cost_plus"
            )
        ),
        chi_phi=(
            CostConfig()
            if chi_phi is None
            else CostConfig(
                vision_usd_moi_anh=_as_float(chi_phi, "vision_usd_moi_anh", "chi_phi"),
                proxy_usd_moi_luot=_as_float(chi_phi, "proxy_usd_moi_luot", "chi_phi"),
                ngan_sach_usd_thang=_as_float(chi_phi, "ngan_sach_usd_thang", "chi_phi"),
            )
        ),
        canh_bao=(
            AlertConfig()
            if canh_bao is None
            else AlertConfig(
                source_blocked_nguong_phan_tram=_as_float(
                    canh_bao, "source_blocked_nguong_phan_tram", "canh_bao"
                ),
                source_blocked_mau_toi_thieu=_as_int(
                    canh_bao, "source_blocked_mau_toi_thieu", "canh_bao"
                ),
            )
        ),
        pi=_as_float(canh_tranh, "pi", "canh_tranh"),
        ocr_nguong_lech_sigma=_as_float(ocr, "nguong_lech_sigma", "ocr_guardrail"),
        ocr_confidence_can_review=_as_str(ocr, "confidence_can_review", "ocr_guardrail"),
    )


def load_pricing_config(path: Path | None = None) -> PricingConfig:
    """Đọc `config/khao-sat-gia-tham-so.yaml` và parse thành PricingConfig."""
    cfg = path or CONFIG_PATH
    if not cfg.exists():
        raise PricingConfigError(f"không tìm thấy file cấu hình: {cfg}")
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    return parse_pricing_config(data)


_DEFAULT: PricingConfig | None = None


def get_pricing_config() -> PricingConfig:
    """Config đã cache — tránh đọc đĩa mỗi lần gọi trong một lượt khảo sát."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = load_pricing_config()
    return _DEFAULT


def _reset_pricing_config_cache() -> None:
    """Xóa cache (dùng cho test)."""
    global _DEFAULT
    _DEFAULT = None
