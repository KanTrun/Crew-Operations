# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Contract test cho hợp đồng dữ liệu v2.1 (plan mục 3.1–3.5).

ADR-003: các test này PHẢI tồn tại và pass trước khi `ag_pricing` viết bất kỳ
logic nghiệp vụ nào trên các model ở đây.

Không network, không LLM, không DB — thuần validate Pydantic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from ca_contracts.catchment_survey_v2 import (
    SCHEMA_VERSION,
    SUPPORTED_SCHEMA_MAJORS,
    SURVEY_JOB_TRANSITIONS,
    AreaContext,
    AreaType,
    CatchmentSurveyRequest,
    CatchmentSurveyResponse,
    ChannelMode,
    ConfidenceLevel,
    CostPlusCheck,
    MenuItemPrice,
    MenuSnapshotV2,
    PercentileStats,
    PositioningTier,
    RadiusProfile,
    StoreRecord,
    SubstituteCategoryStats,
    SubstitutePriceComparison,
    SubstituteTaxonomy,
    SubstituteTaxonomyEntry,
    SurveyErrorCode,
    SurveyJobStatus,
    schema_major,
)
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "packages" / "contracts" / "schema" / "CatchmentPriceSurveyV2.json"


def _store_record(**overrides: object) -> StoreRecord:
    base: dict[str, object] = {
        "store_id": "res_001",
        "name": "Cơm sườn 47",
        "lat": 10.762622,
        "lng": 106.660172,
        "review_count": 320,
        "rating": 4.6,
        "weighted_rating": 4.55,
        "passed_gate1": True,
        "passed_gate2": True,
    }
    base.update(overrides)
    return StoreRecord(**base)  # type: ignore[arg-type]


def _menu_item(**overrides: object) -> MenuItemPrice:
    base: dict[str, object] = {
        "item_name_raw": "Cơm sườn bì chả",
        "item_name_normalized": "com suon bi cha",
        "original_price_vnd": 45000,
        "effective_price_vnd": 39000,
        "is_promotional": True,
        "source_channel": ChannelMode.DELIVERY_PLATFORM,
        "confidence": "high",
    }
    base.update(overrides)
    return MenuItemPrice(**base)  # type: ignore[arg-type]


# ── 3.1 Request Contract ─────────────────────────────────────────────────────


def test_request_defaults_dung_plan_muc_3_1() -> None:
    """Mặc định phải đúng plan: hybrid, radius 1.0/5.0, min_review 50, min_rating 4.2."""
    req = CatchmentSurveyRequest(
        latitude=10.762622, longitude=106.660172, core_category="com_suon_bi_cha"
    )

    assert req.schema_version == SCHEMA_VERSION == "2.1"
    assert req.channel_mode is ChannelMode.HYBRID
    assert req.radius_profile.dine_in_km == 1.0
    assert req.radius_profile.delivery_km == 5.0
    assert req.max_menu_images_per_store == 5
    assert req.min_review_count == 50
    assert req.min_rating == 4.2
    assert req.include_substitutes is True
    # ADR-008: hệ thống không tự chốt tầng định vị thay chủ quán
    assert req.positioning_tier is None
    assert req.cost_plus_check is None
    assert req.idempotency_key is None


def test_request_tu_choi_toa_do_ngoai_pham_vi() -> None:
    with pytest.raises(ValidationError):
        CatchmentSurveyRequest(latitude=91.0, longitude=106.66, core_category="com")
    with pytest.raises(ValidationError):
        CatchmentSurveyRequest(latitude=10.76, longitude=181.0, core_category="com")


def test_request_tu_choi_core_category_rong() -> None:
    with pytest.raises(ValidationError):
        CatchmentSurveyRequest(latitude=10.76, longitude=106.66, core_category="")


def test_radius_profile_chan_gioi_han_theo_kenh() -> None:
    """Plan mục 1.1: dine-in ≤3km, delivery ≤10km — hai trần khác nhau."""
    assert RadiusProfile(dine_in_km=3.0, delivery_km=10.0).delivery_km == 10.0

    with pytest.raises(ValidationError):
        RadiusProfile(dine_in_km=3.5)
    with pytest.raises(ValidationError):
        RadiusProfile(delivery_km=10.5)
    with pytest.raises(ValidationError):
        RadiusProfile(dine_in_km=0.0)


def test_cost_plus_check_chan_margin_ratio_ngoai_0_1() -> None:
    assert CostPlusCheck(estimated_cogs_vnd=15000, target_margin_ratio=0.30).estimated_cogs_vnd == 15000
    assert CostPlusCheck().estimated_cogs_vnd is None

    for bad in (0.0, 1.0, 1.5, -0.1):
        with pytest.raises(ValidationError):
            CostPlusCheck(target_margin_ratio=bad)
    with pytest.raises(ValidationError):
        CostPlusCheck(estimated_cogs_vnd=-1)


def test_request_chan_max_menu_images_ngoai_1_20() -> None:
    assert CatchmentSurveyRequest(
        latitude=10.76, longitude=106.66, core_category="com", max_menu_images_per_store=20
    ).max_menu_images_per_store == 20

    for bad in (0, 21, -1):
        with pytest.raises(ValidationError):
            CatchmentSurveyRequest(
                latitude=10.76,
                longitude=106.66,
                core_category="com",
                max_menu_images_per_store=bad,
            )


def test_request_chan_nguong_gate_am() -> None:
    with pytest.raises(ValidationError):
        CatchmentSurveyRequest(
            latitude=10.76, longitude=106.66, core_category="com", min_review_count=-1
        )
    with pytest.raises(ValidationError):
        CatchmentSurveyRequest(latitude=10.76, longitude=106.66, core_category="com", min_rating=5.5)


# ── 3.5 Versioning & tương thích ngược ───────────────────────────────────────


@pytest.mark.parametrize(
    ("version", "expected"),
    [("2.1", 2), ("2.0", 2), ("3.0", 3), ("1.0", 1), ("", -1), ("abc", -1), ("v2.1", -1)],
)
def test_schema_major_trich_dung_phan_major(version: str, expected: int) -> None:
    assert schema_major(version) == expected


def test_schema_version_sai_dinh_dang_bi_chan() -> None:
    with pytest.raises(ValidationError):
        CatchmentSurveyRequest(
            latitude=10.76, longitude=106.66, core_category="com", schema_version="khong-ro"
        )


def test_major_khong_tuong_thich_nam_ngoai_tap_ho_tro() -> None:
    """Plan mục 3.5: MAJOR lệch → ca_api trả 409 thay vì cố parse sai."""
    assert schema_major(SCHEMA_VERSION) in SUPPORTED_SCHEMA_MAJORS
    assert schema_major("1.0") not in SUPPORTED_SCHEMA_MAJORS
    assert schema_major("3.0") not in SUPPORTED_SCHEMA_MAJORS


def test_v1_module_van_con_de_tuong_thich_nguoc() -> None:
    """Plan mục 3.5: giữ endpoint/contract cũ song song tối thiểu 1 chu kỳ release."""
    from ca_contracts import catchment_survey as v1

    old = v1.CatchmentSurveyRequest(
        latitude=10.76, longitude=106.66, category_keyword="cơm tấm"
    )
    assert old.radius_km == 3.0
    assert old.channel_mode == "dine_in_vision"


# ── 3.2 Store & Menu Contracts ───────────────────────────────────────────────


def test_menu_item_price_tach_gia_goc_va_gia_hieu_luc() -> None:
    """Plan mục 1.5.2: hai trường giá riêng biệt, không được trộn."""
    item = _menu_item()

    assert item.original_price_vnd == 45000
    assert item.effective_price_vnd == 39000
    assert item.is_promotional is True
    assert item.is_combo is False
    assert item.is_fallback_derived is False
    assert item.portion_note is None


def test_menu_item_price_chan_confidence_ngoai_thang_3_muc() -> None:
    valid: tuple[ConfidenceLevel, ...] = ("low", "medium", "high")
    for level in valid:
        assert _menu_item(confidence=level).confidence == level

    for bad in ("very_high", "LOW", "", "0.9"):
        with pytest.raises(ValidationError):
            _menu_item(confidence=bad)


def test_menu_item_price_chan_gia_am() -> None:
    with pytest.raises(ValidationError):
        _menu_item(original_price_vnd=-1000)
    with pytest.raises(ValidationError):
        _menu_item(effective_price_vnd=-1)


def test_menu_item_price_bat_buoc_khai_bao_kenh_nguon() -> None:
    # `type: ignore[call-arg]` là cố ý: test này PHẢI gọi thiếu tham số bắt buộc thì
    # mới chứng minh được pydantic chặn. Bỏ ignore thì mypy đỏ, mà thêm tham số vào
    # thì test mất ý nghĩa (nó sẽ pass vì lý do khác). Lời giải thích phải nằm ở dòng
    # RIÊNG — mypy báo "Invalid type: ignore comment" nếu có chữ đứng sau `[...]`.
    with pytest.raises(ValidationError):
        MenuItemPrice(  # type: ignore[call-arg]
            item_name_raw="Cơm sườn",
            original_price_vnd=40000,
            effective_price_vnd=40000,
        )


def test_menu_snapshot_bat_buoc_captured_at() -> None:
    """Plan mục 1.5.8: mọi bản ghi phải gắn thời điểm thu thập."""
    snap = MenuSnapshotV2(
        store_id="res_001",
        image_url="https://example.test/menu.jpg",
        extracted_items=[_menu_item()],
        captured_at="2026-09-13T14:55:00+07:00",
    )
    assert snap.ocr_model == "gemini-vision"
    assert len(snap.extracted_items) == 1

    with pytest.raises(ValidationError):
        MenuSnapshotV2(store_id="res_001", captured_at="")


def test_store_record_wr_va_rating_gioi_han_thang_5() -> None:
    for bad_field in ("rating", "weighted_rating"):
        with pytest.raises(ValidationError):
            _store_record(**{bad_field: 5.5})
        with pytest.raises(ValidationError):
            _store_record(**{bad_field: -0.1})


def test_store_record_passes_dual_gate_chi_true_khi_ca_hai_gate() -> None:
    assert _store_record(passed_gate1=True, passed_gate2=True).passes_dual_gate is True
    assert _store_record(passed_gate1=True, passed_gate2=False).passes_dual_gate is False
    assert _store_record(passed_gate1=False, passed_gate2=True).passes_dual_gate is False
    assert _store_record(passed_gate1=False, passed_gate2=False).passes_dual_gate is False


def test_store_record_low_confidence_mac_dinh_false() -> None:
    """Plan mục 4.2: low_confidence là CỜ, không phải lý do loại bỏ."""
    store = _store_record()
    assert store.low_confidence is False
    assert store.has_favorite_badge is False
    assert store.positioning_tier_suggested is None

    flagged = _store_record(review_count=3, has_favorite_badge=True, low_confidence=True)
    assert flagged.low_confidence is True
    assert flagged.passes_dual_gate is True


def test_store_record_chan_toa_do_sai() -> None:
    with pytest.raises(ValidationError):
        _store_record(lat=95.0)
    with pytest.raises(ValidationError):
        _store_record(lng=-190.0)


# ── 3.3 Aggregation Contracts ────────────────────────────────────────────────


def test_percentile_stats_co_co_insufficient_data() -> None:
    """Plan mục 4.1: n < 5 → không trả phân vị, chỉ trả sample_size + cờ."""
    thin = PercentileStats(sample_size=3, insufficient_data=True)
    assert thin.insufficient_data is True
    assert (thin.p25, thin.p50, thin.p75) == (0.0, 0.0, 0.0)

    full = PercentileStats(p25=35000.0, p50=42000.0, p75=50000.0, sample_size=40)
    assert full.insufficient_data is False
    assert full.p25 <= full.p50 <= full.p75

    with pytest.raises(ValidationError):
        PercentileStats(sample_size=-1)


def test_substitute_comparison_tach_raw_va_display() -> None:
    """Plan mục 1.5.7: `_raw` để lưu trữ/tính tiếp, `_display` chỉ để hiển thị."""
    comp = SubstitutePriceComparison(
        core_category="com_suon_bi_cha",
        positioning_tier=PositioningTier.CASUAL_DINE_IN,
        core_stats=PercentileStats(p25=35000.0, p50=42000.0, p75=50000.0, sample_size=40),
        substitutes=[
            SubstituteCategoryStats(
                category_name="bun_bo_hue",
                stats=PercentileStats(p25=40000.0, p50=48000.0, p75=55000.0, sample_size=22),
            )
        ],
        ambi=45000.0,
        sweet_spot_low_raw=41250.0,
        sweet_spot_high_raw=44800.0,
        sweet_spot_low_display=40000.0,
        sweet_spot_high_display=45000.0,
    )

    assert comp.sweet_spot_low_raw == 41250.0
    assert comp.sweet_spot_low_display == 40000.0
    assert comp.min_viable_price is None
    assert comp.cost_plus_warning is False


def test_substitute_comparison_bat_buoc_khai_bao_tang_dinh_vi() -> None:
    """Plan mục 1.5.3: không được trộn nhiều tier vào một rổ so sánh."""
    # Cố tình thiếu `positioning_tier` — đó chính là điều test này chứng minh.
    with pytest.raises(ValidationError):
        SubstitutePriceComparison(  # type: ignore[call-arg]
            core_category="com",
            core_stats=PercentileStats(sample_size=0),
            ambi=0.0,
            sweet_spot_low_raw=0.0,
            sweet_spot_high_raw=0.0,
            sweet_spot_low_display=0.0,
            sweet_spot_high_display=0.0,
        )


def test_substitute_comparison_chan_so_am() -> None:
    with pytest.raises(ValidationError):
        SubstitutePriceComparison(
            core_category="com",
            positioning_tier=PositioningTier.STREET_FOOD,
            core_stats=PercentileStats(sample_size=0),
            ambi=-1.0,
            sweet_spot_low_raw=0.0,
            sweet_spot_high_raw=0.0,
            sweet_spot_low_display=0.0,
            sweet_spot_high_display=0.0,
        )


def test_area_context_la_ngu_canh_khong_phai_cong_thuc_gia() -> None:
    ctx = AreaContext(area_type=AreaType.OFFICE, competitive_intensity=3.2)
    assert ctx.area_type is AreaType.OFFICE
    assert ctx.competitive_intensity == 3.2

    # area_type=None hợp lệ: chưa suy ra được thì để trống, không bịa (ADR-002)
    assert AreaContext().area_type is None
    assert AreaContext().competitive_intensity == 0.0

    with pytest.raises(ValidationError):
        AreaContext(competitive_intensity=-0.5)


# ── 2.4 State machine ────────────────────────────────────────────────────────


def test_state_machine_phu_dung_cac_trang_thai_trong_plan() -> None:
    expected = {
        "queued",
        "scraping_online",
        "scraping_dinein",
        "ocr_processing",
        "aggregating",
        "needs_review",
        "completed",
        "failed",
    }
    assert {s.value for s in SurveyJobStatus} == expected
    assert set(SURVEY_JOB_TRANSITIONS) == set(SurveyJobStatus)


def test_state_machine_chan_duong_tat_qua_needs_review() -> None:
    """ADR-008: needs_review là điểm dừng thật — không có cạnh nào bỏ qua nó để
    đi thẳng tới completed, và không có cạnh tự động nào ngoài aggregating/failed."""
    assert SurveyJobStatus.COMPLETED not in SURVEY_JOB_TRANSITIONS[SurveyJobStatus.NEEDS_REVIEW]
    assert SURVEY_JOB_TRANSITIONS[SurveyJobStatus.NEEDS_REVIEW] == frozenset(
        {SurveyJobStatus.AGGREGATING, SurveyJobStatus.FAILED}
    )
    # COMPLETED và FAILED là trạng thái kết thúc
    assert SURVEY_JOB_TRANSITIONS[SurveyJobStatus.COMPLETED] == frozenset()
    assert SURVEY_JOB_TRANSITIONS[SurveyJobStatus.FAILED] == frozenset()


def test_state_machine_hanh_trinh_hanh_phuc_di_qua_du_cac_buoc() -> None:
    path = [
        SurveyJobStatus.QUEUED,
        SurveyJobStatus.SCRAPING_ONLINE,
        SurveyJobStatus.SCRAPING_DINEIN,
        SurveyJobStatus.OCR_PROCESSING,
        SurveyJobStatus.AGGREGATING,
        SurveyJobStatus.COMPLETED,
    ]
    for current, nxt in zip(path, path[1:], strict=False):
        assert nxt in SURVEY_JOB_TRANSITIONS[current]


def test_state_machine_ocr_co_the_re_ve_review() -> None:
    assert (
        SurveyJobStatus.NEEDS_REVIEW
        in SURVEY_JOB_TRANSITIONS[SurveyJobStatus.OCR_PROCESSING]
    )


# ── 3.3 Response ─────────────────────────────────────────────────────────────


def _response(**overrides: object) -> CatchmentSurveyResponse:
    base: dict[str, object] = {
        "job_id": "job_01",
        "status": SurveyJobStatus.COMPLETED,
        "survey_captured_at": "2026-09-13T14:55:00+07:00",
        "generated_at": "2026-09-13T14:57:12+07:00",
    }
    base.update(overrides)
    return CatchmentSurveyResponse(**base)  # type: ignore[arg-type]


def test_response_bat_buoc_job_id_va_hai_dau_thoi_gian() -> None:
    """Plan mục 1.5.8: `survey_captured_at` bắt buộc để UI ghi rõ thời điểm khảo sát."""
    resp = _response()
    assert resp.schema_version == "2.1"
    assert resp.stores_flagged_for_review == []
    assert resp.online_stats is None and resp.dinein_stats is None

    with pytest.raises(ValidationError):
        CatchmentSurveyResponse(job_id="job_01", survey_captured_at="", generated_at="x")
    with pytest.raises(ValidationError):
        CatchmentSurveyResponse(job_id="", survey_captured_at="x", generated_at="x")
    # Cố tình thiếu `job_id` — đó chính là điều test này chứng minh.
    with pytest.raises(ValidationError):
        CatchmentSurveyResponse(  # type: ignore[call-arg]
            survey_captured_at="x", generated_at="x"
        )


def test_response_luu_hang_doi_review_theo_adr_008() -> None:
    resp = _response(
        status=SurveyJobStatus.NEEDS_REVIEW,
        stores_flagged_for_review=["res_004", "res_009"],
    )
    assert resp.status is SurveyJobStatus.NEEDS_REVIEW
    assert resp.stores_flagged_for_review == ["res_004", "res_009"]


def test_response_tu_choi_status_ngoai_state_machine() -> None:
    with pytest.raises(ValidationError):
        _response(status="dang_chay")


def test_response_error_code_chỉ_dung_khi_that_bai() -> None:
    resp = _response(status=SurveyJobStatus.FAILED, error_code=SurveyErrorCode.SOURCE_BLOCKED)
    assert resp.error_code is SurveyErrorCode.SOURCE_BLOCKED

    with pytest.raises(ValidationError):
        _response(error_code="KHONG_CO_TRONG_BANG")


def test_error_taxonomy_phu_dung_bang_ma_loi_muc_5_3() -> None:
    assert {c.value for c in SurveyErrorCode} == {
        "INVALID_RADIUS",
        "SCHEMA_VERSION_MISMATCH",
        "INSUFFICIENT_MARKET_DATA",
        "RATE_LIMITED",
        "SOURCE_BLOCKED",
        "VISION_QUOTA_EXCEEDED",
    }


# ── 3.4 Cấu hình động ────────────────────────────────────────────────────────


def test_substitute_taxonomy_entry_bat_buoc_version_duong() -> None:
    entry = SubstituteTaxonomyEntry(
        jtbd_group="lunch_meal_replacement",
        core_categories=["com_suon_bi_cha", "com_tam"],
        substitute_categories=["bun_bo_hue", "pho_bo", "hu_tieu"],
        version=1,
    )
    assert entry.version == 1
    assert "pho_bo" in entry.substitute_categories

    with pytest.raises(ValidationError):
        SubstituteTaxonomyEntry(jtbd_group="x", version=0)
    with pytest.raises(ValidationError):
        SubstituteTaxonomyEntry(jtbd_group="", version=1)


def test_substitute_taxonomy_rong_van_hop_le() -> None:
    assert SubstituteTaxonomy().entries == []
    assert SubstituteTaxonomy().schema_version == 1


# ── JSON Schema export ───────────────────────────────────────────────────────


def test_json_schema_v2_da_xuat_va_khop_model() -> None:
    """Plan mục 3: schema JSON phải tồn tại song song Pydantic model."""
    assert SCHEMA_PATH.exists(), f"Thiếu {SCHEMA_PATH} — chạy `make contracts`"

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["title"] == "CatchmentSurveyResponse"
    props = schema["properties"]
    for required in (
        "schema_version",
        "job_id",
        "status",
        "survey_captured_at",
        "generated_at",
        "stores_flagged_for_review",
    ):
        assert required in props, f"schema thiếu {required}"
    # Chỉ field không có default mới vào `required` của JSON Schema.
    assert set(schema["required"]) == {"job_id", "survey_captured_at", "generated_at"}
    assert props["status"]["$ref"].endswith("SurveyJobStatus")
    assert props["stores_flagged_for_review"]["items"]["type"] == "string"


def test_model_round_trip_qua_json() -> None:
    resp = _response(
        online_stats=PercentileStats(p25=35000.0, p50=42000.0, p75=50000.0, sample_size=40),
        area_context=AreaContext(area_type=AreaType.MIXED, competitive_intensity=2.5),
    )
    restored = CatchmentSurveyResponse.model_validate(json.loads(resp.model_dump_json()))
    assert restored == resp
    assert restored.area_context is not None
    assert restored.area_context.area_type is AreaType.MIXED
