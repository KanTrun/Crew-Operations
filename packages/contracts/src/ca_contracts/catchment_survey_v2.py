"""Hợp đồng dữ liệu v2.1 — Khảo sát Giá & Định vị Thị trường F&B theo Bán kính.

Nguồn: `plans/260913-1455-khao-sat-gia-fb-online-dinein-substitutes/plan.md` mục 3.1–3.4.

ADR-003 (contracts-first): module này phải tồn tại và có unit test validate TRƯỚC
khi bất kỳ logic nghiệp vụ nào của `ag_pricing` được viết.

ADR-002 (tất định): contract chỉ mô tả hình dạng dữ liệu, không chứa suy luận
nghiệp vụ. Mọi con số (phân vị, WR, AMBI, Sweet Spot, MinViablePrice,
CompetitiveIntensity) do tầng toán thuần ở `ca_agents.ag_pricing.math_layer` sinh ra.

ADR-008 (con người quyết định giá): `positioning_tier_suggested` và
`stores_flagged_for_review` là kênh GỢI Ý — không có field nào trong contract này
mang nghĩa "giá đã được áp dụng lên hệ thống thật của quán".

Tương thích ngược (plan mục 3.5): module v1.0 `ca_contracts.catchment_survey`
được giữ nguyên không sửa. Hai phiên bản chạy song song tối thiểu 1 chu kỳ
release; `schema_version` phân biệt MAJOR để `ca_api` từ chối request lệch (HTTP 409).
"""

from __future__ import annotations

# Không cần fallback `class StrEnum(str, Enum)` cho Python cũ: mọi package trong repo
# đều khai báo `requires-python = ">=3.12"`, và khai báo lại StrEnum trong except làm
# mypy báo no-redef (tên bị định nghĩa hai lần) mà không đổi được hành vi nào.
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ── Versioning (plan mục 3.5) ────────────────────────────────────────────────

SCHEMA_VERSION: str = "2.1"
"""Phiên bản contract hiện hành. Đổi breaking → bump MAJOR và giữ endpoint cũ."""

SUPPORTED_SCHEMA_MAJORS: frozenset[int] = frozenset({2})
"""Các MAJOR mà `ca_api` chấp nhận parse. Ngoài tập này → HTTP 409."""


def schema_major(schema_version: str) -> int:
    """Trích phần MAJOR từ chuỗi semver rút gọn `MAJOR.MINOR`.

    Trả -1 khi chuỗi không đúng định dạng để tầng API có thể từ chối dứt khoát
    thay vì âm thầm coi là tương thích.
    """
    head = (schema_version or "").strip().split(".", 1)[0]
    try:
        return int(head)
    except ValueError:
        return -1


# ── Enum nghiệp vụ (plan mục 3.1) ────────────────────────────────────────────


class ChannelMode(StrEnum):
    """Kênh lấy giá. `hybrid` = đối chiếu cả giá sàn lẫn giá tại quán."""

    DINE_IN_VISION = "dine_in_vision"
    DELIVERY_PLATFORM = "delivery_platform"
    HYBRID = "hybrid"


class PositioningTier(StrEnum):
    """Tầng định vị thương hiệu (plan mục 1.5.3).

    AMBI và Sweet Spot PHẢI tính riêng theo từng tầng — gộp quán vỉa hè với chuỗi
    thương hiệu vào một rổ trung vị là sai bản chất cạnh tranh.
    """

    STREET_FOOD = "street_food"
    CASUAL_DINE_IN = "casual_dine_in"
    BRANDED_CHAIN = "branded_chain"


class AreaType(StrEnum):
    """Loại khu vực theo đối tượng khách (plan mục 1.5.5) — ngữ cảnh diễn giải AMBI."""

    OFFICE = "office"
    RESIDENTIAL = "residential"
    MIXED = "mixed"
    TOURIST = "tourist"


class SurveyJobStatus(StrEnum):
    """State machine của một job khảo sát (plan mục 2.4).

    `needs_review` là ĐIỂM DỪNG THẬT (ADR-008): job không tự chuyển sang
    `aggregating` nếu chưa có người dùng xác nhận qua `POST .../{job_id}/review`.
    Không được thiết kế "auto-approve sau N giây".
    """

    QUEUED = "queued"
    SCRAPING_ONLINE = "scraping_online"
    SCRAPING_DINEIN = "scraping_dinein"
    OCR_PROCESSING = "ocr_processing"
    AGGREGATING = "aggregating"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    FAILED = "failed"


#: Thứ tự hợp lệ của state machine — dùng để chặn bước nhảy sai ở tầng orchestrator.
SURVEY_JOB_TRANSITIONS: dict[SurveyJobStatus, frozenset[SurveyJobStatus]] = {
    SurveyJobStatus.QUEUED: frozenset({SurveyJobStatus.SCRAPING_ONLINE, SurveyJobStatus.FAILED}),
    SurveyJobStatus.SCRAPING_ONLINE: frozenset(
        {SurveyJobStatus.SCRAPING_DINEIN, SurveyJobStatus.FAILED}
    ),
    SurveyJobStatus.SCRAPING_DINEIN: frozenset(
        {SurveyJobStatus.OCR_PROCESSING, SurveyJobStatus.FAILED}
    ),
    SurveyJobStatus.OCR_PROCESSING: frozenset(
        {SurveyJobStatus.AGGREGATING, SurveyJobStatus.NEEDS_REVIEW, SurveyJobStatus.FAILED}
    ),
    SurveyJobStatus.NEEDS_REVIEW: frozenset(
        {SurveyJobStatus.AGGREGATING, SurveyJobStatus.FAILED}
    ),
    SurveyJobStatus.AGGREGATING: frozenset(
        {SurveyJobStatus.COMPLETED, SurveyJobStatus.FAILED}
    ),
    SurveyJobStatus.COMPLETED: frozenset(),
    SurveyJobStatus.FAILED: frozenset(),
}


ConfidenceLevel = Literal["low", "medium", "high"]
"""Độ tin cậy của một lần đọc giá. `low` → đẩy vào hàng đợi review thủ công."""


class SurveyErrorCode(StrEnum):
    """Bảng mã lỗi (plan mục 5.3)."""

    INVALID_RADIUS = "INVALID_RADIUS"
    SCHEMA_VERSION_MISMATCH = "SCHEMA_VERSION_MISMATCH"
    INSUFFICIENT_MARKET_DATA = "INSUFFICIENT_MARKET_DATA"
    RATE_LIMITED = "RATE_LIMITED"
    SOURCE_BLOCKED = "SOURCE_BLOCKED"
    VISION_QUOTA_EXCEEDED = "VISION_QUOTA_EXCEEDED"


# ── 3.1 Request Contract ─────────────────────────────────────────────────────


class RadiusProfile(BaseModel):
    """Bán kính khảo sát tách theo kênh (plan mục 1.1).

    Dine-in cạnh tranh trong phạm vi đi bộ/xe ngắn; delivery phủ rộng hơn nhiều.
    Giá trị mặc định là ĐỀ XUẤT — xem `config/khao-sat-gia-tham-so.yaml`.
    """

    dine_in_km: float = Field(default=1.0, gt=0.0, le=3.0, description="Bán kính dine-in (km)")
    delivery_km: float = Field(default=5.0, gt=0.0, le=10.0, description="Bán kính delivery (km)")


class CostPlusCheck(BaseModel):
    """Đối chiếu giá vốn (plan mục 1.5.1) — TUỲ CHỌN, chỉ tính khi chủ quán cung cấp.

    Hệ thống so quán với thị trường là chưa đủ: quán có thể định giá đúng AMBI mà
    vẫn lỗ nếu food cost cao hơn chuẩn ngành.
    """

    estimated_cogs_vnd: int | None = Field(
        default=None, ge=0, description="Giá vốn nguyên liệu ước tính mỗi phần (VNĐ)"
    )
    target_margin_ratio: float = Field(
        default=0.30,
        gt=0.0,
        lt=1.0,
        description="Biên lợi nhuận mục tiêu. # BUSINESS_DECISION_PENDING_REVIEW: xem plan mục 1.5.1",
    )


class CatchmentSurveyRequest(BaseModel):
    """Yêu cầu tạo một job khảo sát giá theo bán kính (plan mục 3.1)."""

    schema_version: str = Field(default=SCHEMA_VERSION, description="Semver rút gọn MAJOR.MINOR")
    latitude: float = Field(ge=-90.0, le=90.0, description="Vĩ độ quán")
    longitude: float = Field(ge=-180.0, le=180.0, description="Kinh độ quán")
    core_category: str = Field(min_length=1, description='Danh mục cốt lõi, vd "com_suon_bi_cha"')
    positioning_tier: PositioningTier | None = Field(
        default=None,
        description="None = hệ thống gợi ý, CHỦ QUÁN xác nhận (ADR-008)",
    )
    channel_mode: ChannelMode = Field(default=ChannelMode.HYBRID)
    include_substitutes: bool = Field(
        default=True, description="Khảo sát thêm các nhóm món thay thế cùng JTBD"
    )
    radius_profile: RadiusProfile = Field(default_factory=RadiusProfile)
    max_menu_images_per_store: int = Field(default=5, ge=1, le=20)
    min_review_count: int = Field(default=50, ge=0, description="Ngưỡng Gate 1 (Volume)")
    min_rating: float = Field(default=4.2, ge=0.0, le=5.0, description="Ngưỡng Gate 2 (Quality)")
    cost_plus_check: CostPlusCheck | None = Field(default=None, description="Plan mục 1.5.1")
    idempotency_key: str | None = Field(
        default=None, max_length=200, description="Chống tạo trùng job (plan mục 5.2)"
    )

    @field_validator("schema_version")
    @classmethod
    def _schema_version_phai_dung_dinh_dang(cls, v: str) -> str:
        """Chặn sớm phiên bản sai định dạng — `ca_api` trả 409 thay vì parse sai."""
        text = (v or "").strip()
        if schema_major(text) < 0 or "." not in text:
            raise ValueError("schema_version phai dang MAJOR.MINOR")
        return text


# ── 3.2 Store & Menu Contracts ───────────────────────────────────────────────


class MenuItemPrice(BaseModel):
    """Một dòng giá bóc tách được (plan mục 3.2).

    Plan mục 1.5.2: ShopeeFood phần lớn hiển thị GIÁ ĐÃ KHUYẾN MÃI. Nếu lấy giá đó
    làm mẫu tính AMBI thì chỉ số bị kéo thấp giả tạo. Vì vậy:
    - `original_price_vnd` (giá gốc, thường có gạch ngang) là CƠ SỞ tính AMBI/Sweet Spot.
    - `effective_price_vnd` (giá sau giảm) chỉ để tham khảo mức khuyến mãi khu vực.
    """

    item_name_raw: str = Field(min_length=1, description="Tên món đúng như trên nguồn")
    item_name_normalized: str = Field(
        default="", description="Tên đã chuẩn hoá (bỏ dấu, lowercase, ánh xạ đồng nghĩa)"
    )
    original_price_vnd: int | None = Field(
        default=None,
        ge=0,
        description="Giá gốc — cơ sở tính AMBI (mục 1.5.2). None khi OCR không đọc được giá (ảnh mờ)",
    )
    effective_price_vnd: int = Field(ge=0, description="Giá sau khuyến mãi — chỉ tham khảo")
    is_promotional: bool = Field(default=False, description="True nếu đang có giá gạch ngang")
    is_combo: bool = Field(
        default=False, description="Mục 1.5.9 — combo tách kênh so sánh riêng, không trộn món lẻ"
    )
    portion_note: str | None = Field(
        default=None, description='Mục 1.5.4, vd "phần đặc biệt", "size L"'
    )
    source_channel: ChannelMode = Field(description="Kênh sinh ra dòng giá này")
    confidence: ConfidenceLevel = Field(default="medium")
    is_fallback_derived: bool = Field(
        default=False, description="True nếu giá gốc suy ngược từ chiết khấu (vd -20%)"
    )


class MenuSnapshotV2(BaseModel):
    """Kết quả OCR một ảnh menu (plan mục 3.2).

    `captured_at` bắt buộc: plan mục 1.5.8 — khảo sát là ảnh chụp một thời điểm,
    UI phải ghi rõ để chủ quán không hiểu nhầm số liệu là "luôn đúng mọi lúc".

    Phase 2 bổ sung: `photo_source` và `photo_taken_recency_days` để tầng tổng hợp
    Phase 3 phân biệt ảnh mới từ tab Menu vs ảnh cũ lọc từ All Photos — trọng số khác nhau.
    """

    store_id: str = Field(min_length=1)
    image_url: str = Field(default="")
    ocr_model: str = Field(default="gemini-vision")
    extracted_items: list[MenuItemPrice] = Field(default_factory=list)
    captured_at: str = Field(min_length=1, description="ISO 8601")
    photo_source: Literal["menu_tab", "all_photos_filtered"] = Field(
        default="menu_tab",
        description="Phase 2: nguồn ảnh — tab Menu (tin cậy cao) hay All Photos đã lọc",
    )
    photo_taken_recency_days: int | None = Field(
        default=None,
        ge=0,
        description="Phase 2: số ngày kể từ lúc chụp đến lúc khảo sát. None nếu platform không trả metadata",
    )


class StoreRecord(BaseModel):
    """Một quán đối thủ đã qua bước chuẩn hoá, kèm kết quả Dual-Gate (plan mục 3.2)."""

    store_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)
    review_count: int = Field(ge=0)
    rating: float = Field(ge=0.0, le=5.0, description="R — điểm sao thô")
    weighted_rating: float = Field(ge=0.0, le=5.0, description="WR — đã hiệu chỉnh Bayesian")
    passed_gate1: bool = Field(description="Gate 1 (Volume)")
    passed_gate2: bool = Field(description="Gate 2 (Quality)")
    has_favorite_badge: bool = Field(
        default=False,
        description="Nhãn 'Quán yêu thích' — cho qua Gate 1 bằng nhánh OR (plan mục 1.4/4.2)",
    )
    low_confidence: bool = Field(
        default=False,
        description="Mục 4.2: qua Gate 1 nhờ badge nhưng review_count quá thấp — "
        "vẫn được tính với TRỌNG SỐ GIẢM, không loại bỏ tuyệt đối",
    )
    positioning_tier_suggested: PositioningTier | None = Field(
        default=None,
        description="Mục 1.5.3 — hệ thống GỢI Ý, chủ quán xác nhận (ADR-008)",
    )
    menu_items: list[MenuItemPrice] = Field(default_factory=list)

    @property
    def passes_dual_gate(self) -> bool:
        """Quán đạt cả hai gate — đủ điều kiện vào tập mẫu tính AMBI/Sweet Spot."""
        return self.passed_gate1 and self.passed_gate2


# ── 3.3 Aggregation Contracts (kết quả tất định) ─────────────────────────────


class PercentileStats(BaseModel):
    """Phân vị giá của một tập mẫu (plan mục 3.3 + 4.1).

    `insufficient_data=True` khi `sample_size < min_sample_size`: KHÔNG trả số liệu
    phân vị không đáng tin, chỉ trả `sample_size` (plan mục 4.1).
    """

    p25: float = Field(default=0.0, ge=0.0)
    p50: float = Field(default=0.0, ge=0.0)
    p75: float = Field(default=0.0, ge=0.0)
    sample_size: int = Field(default=0, ge=0)
    insufficient_data: bool = Field(
        default=False, description="True khi mẫu < ngưỡng tối thiểu (plan mục 4.1)"
    )


class SubstituteCategoryStats(BaseModel):
    """Thống kê phổ giá của một nhóm món thay thế (plan mục 3.3)."""

    category_name: str = Field(min_length=1, description='VD "bun_bo_hue"')
    stats: PercentileStats


class SubstitutePriceComparison(BaseModel):
    """Bảng so sánh core ↔ substitutes trong CÙNG một tầng định vị (plan mục 3.3)."""

    core_category: str = Field(min_length=1)
    positioning_tier: PositioningTier = Field(
        description="Mục 1.5.3 — tính riêng theo tầng, không trộn"
    )
    core_stats: PercentileStats
    substitutes: list[SubstituteCategoryStats] = Field(default_factory=list)
    ambi: float = Field(ge=0.0, description="Area Meal Budget Index (plan mục 1.3/4.3)")
    sweet_spot_low_raw: float = Field(
        ge=0.0, description="Giá trị toán học CHƯA làm tròn — dùng lưu trữ/tính tiếp"
    )
    sweet_spot_high_raw: float = Field(ge=0.0)
    sweet_spot_low_display: float = Field(
        ge=0.0, description="Đã làm tròn theo mục 1.5.7 — CHỈ dùng hiển thị"
    )
    sweet_spot_high_display: float = Field(ge=0.0)
    min_viable_price: float | None = Field(
        default=None, ge=0.0, description="Mục 1.5.1 — chỉ có nếu request kèm cost_plus_check"
    )
    cost_plus_warning: bool = Field(
        default=False,
        description="True nếu sweet_spot_high_raw < min_viable_price. "
        "UI BẮT BUỘC hiển thị cảnh báo, không được ẩn cho 'gọn' (mục 1.5.1)",
    )


class AreaContext(BaseModel):
    """Ngữ cảnh diễn giải (plan mục 1.5.5, 1.5.6) — KHÔNG phải công thức giá.

    `competitive_intensity` chỉ hiển thị song song AMBI, không gộp vào AMBI/Sweet Spot.
    """

    area_type: AreaType | None = Field(
        default=None,
        description="None khi chưa suy ra được từ mật độ POI — KHÔNG được bịa (ADR-002)",
    )
    competitive_intensity: float = Field(
        default=0.0, ge=0.0, description="Số quán đạt Dual-Gate / km² (plan mục 4.5)"
    )


class CatchmentSurveyResponse(BaseModel):
    """Kết quả một job khảo sát (plan mục 3.3)."""

    schema_version: str = Field(default=SCHEMA_VERSION)
    job_id: str = Field(min_length=1)
    status: SurveyJobStatus = Field(default=SurveyJobStatus.QUEUED)
    online_stats: PercentileStats | None = Field(
        default=None, description="Phân vị giá kênh delivery"
    )
    dinein_stats: PercentileStats | None = Field(
        default=None, description="Phân vị giá kênh dine-in (OCR)"
    )
    substitute_comparison: SubstitutePriceComparison | None = None
    area_context: AreaContext | None = None
    stores_flagged_for_review: list[str] = Field(
        default_factory=list,
        description="store_id chờ người dùng xác nhận (ADR-008) — điểm dừng thật",
    )
    survey_captured_at: str = Field(
        min_length=1, description="Mục 1.5.8 — BẮT BUỘC hiển thị trên UI"
    )
    generated_at: str = Field(min_length=1, description="ISO 8601")
    error_code: SurveyErrorCode | None = Field(
        default=None, description="Chỉ có khi status=failed (plan mục 5.3)"
    )


# ── 3.4 Cấu hình động (không hard-code) ──────────────────────────────────────


class SubstituteTaxonomyEntry(BaseModel):
    """Một dòng của bảng ánh xạ JTBD → nhóm thay thế (plan mục 3.4).

    Nằm trong config versioned (`config/substitute-taxonomy.yaml`) để đội vận hành
    cập nhật mà không cần deploy lại `ag_pricing`.
    """

    jtbd_group: str = Field(min_length=1, description='VD "lunch_meal_replacement"')
    core_categories: list[str] = Field(default_factory=list)
    substitute_categories: list[str] = Field(default_factory=list)
    version: int = Field(ge=1)


class SubstituteTaxonomy(BaseModel):
    """Toàn bộ bảng taxonomy + version dùng để truy vết kết quả khảo sát."""

    schema_version: int = Field(default=1, ge=1)
    entries: list[SubstituteTaxonomyEntry] = Field(default_factory=list)


# ── 5.1 Review Contract (ADR-008: con người quyết định giá) ──────────────────


class SurveyReviewItem(BaseModel):
    """Một dòng giá do chủ quán xác nhận/sửa tay ở màn hình NEEDS_REVIEW.

    `rejected=True` nghĩa là chủ quán loại dòng này khỏi mẫu (OCR đọc nhầm món
    không thuộc ngành hàng đang khảo sát) — KHÔNG suy diễn thành giá 0.
    """

    store_id: str = Field(min_length=1)
    item_name_raw: str = Field(min_length=1)
    original_price_vnd: int | None = Field(default=None, ge=0)
    effective_price_vnd: int = Field(default=0, ge=0)
    is_combo: bool = Field(default=False)
    portion_note: str | None = Field(default=None)
    rejected: bool = Field(default=False)


class SurveyReviewSubmission(BaseModel):
    """Payload `POST /api/v1/market/catchment-survey/{job_id}/review`.

    `approve_all_remaining=True` là quyết định CỦA NGƯỜI DÙNG (ADR-008) — hệ
    thống không bao giờ tự đặt cờ này; không có "auto-approve sau N giây".
    """

    schema_version: str = Field(default=SCHEMA_VERSION)
    reviewed_by: str = Field(default="", max_length=120)
    items: list[SurveyReviewItem] = Field(default_factory=list)
    approve_all_remaining: bool = Field(default=False)
