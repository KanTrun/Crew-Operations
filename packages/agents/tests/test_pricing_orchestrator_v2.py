"""Kiểm thử orchestrator v2 — state machine, NEEDS_REVIEW, mã lỗi (plan mục 2.4, 5.3).

Toàn bộ nguồn cào + OCR đều bị mock: KHÔNG có network, KHÔNG tốn chi phí.
"""

from __future__ import annotations

from typing import Any

import pytest
from ca_agents.ag_pricing.job_manager import (
    InvalidJobTransitionError,
    JobStore,
    get_job_store,
    reset_job_store,
)
from ca_agents.ag_pricing.orchestrator_v2 import (
    SurveyExecutionError,
    SurveyOrchestrator,
    get_pricing_metrics,
    reset_pricing_metrics,
)
from ca_agents.ag_pricing.vision_menu_extractor import VisionExtractionResult
from ca_agents.clients.camoufox_client import CamoufoxUnavailable
from ca_contracts.catchment_survey import DishItem, StoreCandidate
from ca_contracts.catchment_survey_v2 import (
    CatchmentSurveyRequest,
    ChannelMode,
    MenuItemPrice,
    MenuSnapshotV2,
    RadiusProfile,
    SurveyErrorCode,
    SurveyJobStatus,
    SurveyReviewItem,
    SurveyReviewSubmission,
)


def _request(**kw: Any) -> CatchmentSurveyRequest:
    base: dict[str, Any] = {
        "latitude": 10.7769,
        "longitude": 106.7009,
        "core_category": "cơm tấm",
        "radius_profile": RadiusProfile(dine_in_km=1.0, delivery_km=5.0),
        "channel_mode": ChannelMode.HYBRID,
        "min_review_count": 50,
        "min_rating": 4.2,
    }
    base.update(kw)
    return CatchmentSurveyRequest(**base)


def _online_store(idx: int, *, review_count: int = 300, rating: float = 4.6) -> StoreCandidate:
    return StoreCandidate(
        id=f"sf_{idx}",
        name=f"Cơm Tấm Online {idx}",
        lat=10.7769,
        lng=106.7009,
        rating=rating,
        review_count=review_count,
        dishes=[
            DishItem(name="Cơm sườn bì chả", price=45000 + idx * 1000),
            DishItem(name="Cơm tấm sườn", price=40000 + idx * 1000),
            DishItem(name="Cơm gà nướng", price=50000 + idx * 1000),
        ],
        data_source="camoufox",
    )


def _dinein_store(idx: int, *, urls: list[str] | None = None) -> StoreCandidate:
    return StoreCandidate(
        id=f"gm_{idx}",
        name=f"Quán Cơm Tấm {idx}",
        lat=10.7769,
        lng=106.7009,
        rating=4.5,
        review_count=200,
        menu_image_urls=urls if urls is not None else [f"https://example.test/menu{idx}.jpg"],
        data_source="camoufox",
    )


def _snapshot(store_id: str, *, prices: list[int]) -> MenuSnapshotV2:
    return MenuSnapshotV2(
        store_id=store_id,
        image_url=f"https://example.test/{store_id}.jpg",
        extracted_items=[
            MenuItemPrice(
                item_name_raw=f"Món {i}",
                effective_price_vnd=p,
                original_price_vnd=p,
                source_channel=ChannelMode.DINE_IN_VISION,
                confidence="high",
            )
            for i, p in enumerate(prices)
        ],
        captured_at="2026-09-13T10:00:00+00:00",
    )


@pytest.fixture(autouse=True)
def _clean_state() -> Any:
    reset_job_store()
    reset_pricing_metrics()
    yield
    reset_job_store()
    reset_pricing_metrics()


@pytest.fixture
def store() -> JobStore:
    return JobStore()


# ── State machine ────────────────────────────────────────────────────────────


def test_full_happy_path_reaches_completed(store: JobStore, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_delivery_stores_camoufox",
        lambda *a, **k: [_online_store(i) for i in range(3)],
    )
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_gmaps_menu_images_camoufox",
        lambda *a, **k: [],
    )

    orch = SurveyOrchestrator(job_store=store)
    job = orch.create_job(_request())
    assert job.status == SurveyJobStatus.QUEUED

    seen: list[str] = []
    original = job.transition_to

    def _spy(status: SurveyJobStatus) -> None:
        seen.append(status.value)
        original(status)

    monkeypatch.setattr(job, "transition_to", _spy)
    finished = orch.execute_job(job.job_id)

    assert finished.status == SurveyJobStatus.COMPLETED
    assert seen == [
        SurveyJobStatus.SCRAPING_ONLINE.value,
        SurveyJobStatus.SCRAPING_DINEIN.value,
        SurveyJobStatus.OCR_PROCESSING.value,
        SurveyJobStatus.AGGREGATING.value,
        SurveyJobStatus.COMPLETED.value,
    ]
    assert finished.response is not None
    assert finished.response.job_id == finished.job_id
    assert finished.response.online_stats is not None
    assert finished.response.online_stats.sample_size == 9
    assert finished.response.online_stats.insufficient_data is False


def test_invalid_transition_is_rejected(store: JobStore) -> None:
    job = store.create_job(_request())
    with pytest.raises(InvalidJobTransitionError):
        job.transition_to(SurveyJobStatus.COMPLETED)
    assert job.status == SurveyJobStatus.QUEUED


def test_mark_failed_works_from_any_state(store: JobStore) -> None:
    job = store.create_job(_request())
    job.transition_to(SurveyJobStatus.SCRAPING_ONLINE)
    job.mark_failed(SurveyErrorCode.SOURCE_BLOCKED, "bi_chan")
    assert job.status == SurveyJobStatus.FAILED
    assert job.error_code == SurveyErrorCode.SOURCE_BLOCKED


def test_completed_is_terminal(store: JobStore) -> None:
    job = store.create_job(_request())
    for status in (
        SurveyJobStatus.SCRAPING_ONLINE,
        SurveyJobStatus.SCRAPING_DINEIN,
        SurveyJobStatus.OCR_PROCESSING,
        SurveyJobStatus.AGGREGATING,
        SurveyJobStatus.COMPLETED,
    ):
        job.transition_to(status)
    with pytest.raises(InvalidJobTransitionError):
        job.transition_to(SurveyJobStatus.AGGREGATING)


def test_executing_non_queued_job_is_refused(store: JobStore) -> None:
    orch = SurveyOrchestrator(job_store=store)
    job = orch.create_job(_request())
    job.transition_to(SurveyJobStatus.SCRAPING_ONLINE)
    with pytest.raises(SurveyExecutionError):
        orch.execute_job(job.job_id)


def test_unknown_job_raises_keyerror(store: JobStore) -> None:
    orch = SurveyOrchestrator(job_store=store)
    with pytest.raises(KeyError):
        orch.execute_job("khong_ton_tai")


# ── Channel mode ─────────────────────────────────────────────────────────────


def test_delivery_only_skips_gmaps(store: JobStore, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, int] = {"delivery": 0, "gmaps": 0}

    def _delivery(*a: Any, **k: Any) -> list[StoreCandidate]:
        calls["delivery"] += 1
        return [_online_store(i) for i in range(3)]

    def _gmaps(*a: Any, **k: Any) -> list[StoreCandidate]:
        calls["gmaps"] += 1
        return []

    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_delivery_stores_camoufox", _delivery
    )
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_gmaps_menu_images_camoufox", _gmaps
    )

    orch = SurveyOrchestrator(job_store=store)
    job = orch.create_job(_request(channel_mode=ChannelMode.DELIVERY_PLATFORM))
    finished = orch.execute_job(job.job_id)

    assert calls == {"delivery": 1, "gmaps": 0}
    assert finished.status == SurveyJobStatus.COMPLETED
    assert finished.response is not None
    assert finished.response.dinein_stats is None


def test_dinein_only_skips_delivery(store: JobStore, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, int] = {"delivery": 0, "gmaps": 0}
    def _delivery(*a: Any, **k: Any) -> list[StoreCandidate]:
        calls["delivery"] += 1
        return []

    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_delivery_stores_camoufox", _delivery
    )

    def _gmaps(*a: Any, **k: Any) -> list[StoreCandidate]:
        calls["gmaps"] += 1
        return [_dinein_store(i) for i in range(3)]

    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_gmaps_menu_images_camoufox", _gmaps
    )
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2._download_image", lambda url, **k: b"x" * 200
    )
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.extract_menu_from_image",
        lambda image_bytes, *, store_id, **k: VisionExtractionResult(
            snapshot=_snapshot(store_id, prices=[45000, 50000, 55000])
        ),
    )

    orch = SurveyOrchestrator(job_store=store)
    job = orch.create_job(_request(channel_mode=ChannelMode.DINE_IN_VISION))
    finished = orch.execute_job(job.job_id)

    assert calls == {"delivery": 0, "gmaps": 1}
    assert finished.status == SurveyJobStatus.COMPLETED
    assert finished.response is not None
    assert finished.response.online_stats is None
    assert finished.response.dinein_stats is not None
    assert finished.response.dinein_stats.sample_size == 9


def test_radius_profile_is_forwarded_to_scrapers(
    store: JobStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, dict[str, Any]] = {}

    def _delivery(*args: Any, **kwargs: Any) -> list[StoreCandidate]:
        seen["delivery"] = {"args": args, "kwargs": kwargs}
        return [_online_store(i) for i in range(3)]

    def _gmaps(*args: Any, **kwargs: Any) -> list[StoreCandidate]:
        seen["gmaps"] = {"args": args, "kwargs": kwargs}
        return []

    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_delivery_stores_camoufox", _delivery
    )
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_gmaps_menu_images_camoufox", _gmaps
    )

    orch = SurveyOrchestrator(job_store=store)
    job = orch.create_job(
        _request(
            radius_profile=RadiusProfile(dine_in_km=2.0, delivery_km=8.0),
            max_menu_images_per_store=7,
        )
    )
    orch.execute_job(job.job_id)

    assert seen["delivery"]["args"][:3] == (10.7769, 106.7009, "cơm tấm")
    assert seen["delivery"]["kwargs"]["radius_km"] == 8.0
    assert seen["gmaps"]["kwargs"]["radius_km"] == 2.0
    assert seen["gmaps"]["kwargs"]["max_images"] == 7


# ── Dual gate ────────────────────────────────────────────────────────────────


def test_low_review_store_is_excluded_from_stats(
    store: JobStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    stores = [
        _online_store(0, review_count=300),
        _online_store(1, review_count=300),
        _online_store(2, review_count=300),
        # Quán 3 đánh giá, rating cao → rớt Gate 1, giá không được tính
        _online_store(3, review_count=3),
    ]
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_delivery_stores_camoufox",
        lambda *a, **k: stores,
    )
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_gmaps_menu_images_camoufox",
        lambda *a, **k: [],
    )

    orch = SurveyOrchestrator(job_store=store)
    job = orch.execute_job(orch.create_job(_request()).job_id)

    assert job.response is not None
    assert job.response.online_stats is not None
    assert job.response.online_stats.sample_size == 9
    records = job.meta["online_records"]
    assert [r.passed_gate1 for r in records] == [True, True, True, False]
    assert records[3].passes_dual_gate is False


def test_low_rating_store_fails_gate2(store: JobStore, monkeypatch: pytest.MonkeyPatch) -> None:
    stores = [
        _online_store(0),
        _online_store(1),
        _online_store(2),
        _online_store(3, rating=3.1),
    ]
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_delivery_stores_camoufox",
        lambda *a, **k: stores,
    )
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_gmaps_menu_images_camoufox",
        lambda *a, **k: [],
    )

    orch = SurveyOrchestrator(job_store=store)
    job = orch.execute_job(orch.create_job(_request()).job_id)
    records = job.meta["online_records"]
    assert records[3].passed_gate1 is True
    assert records[3].passed_gate2 is False
    assert records[3].passes_dual_gate is False


# ── Error codes ──────────────────────────────────────────────────────────────


def test_insufficient_data_maps_to_422_code(
    store: JobStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_delivery_stores_camoufox",
        lambda *a, **k: [_online_store(0)],
    )
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_gmaps_menu_images_camoufox",
        lambda *a, **k: [],
    )

    orch = SurveyOrchestrator(job_store=store)
    job = orch.execute_job(orch.create_job(_request()).job_id)

    assert job.status == SurveyJobStatus.FAILED
    assert job.error_code == SurveyErrorCode.INSUFFICIENT_MARKET_DATA
    assert job.response is None
    assert get_pricing_metrics()["failures_by_code"]["INSUFFICIENT_MARKET_DATA"] == 1


def test_camoufox_unavailable_maps_to_source_blocked(
    store: JobStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*a: Any, **k: Any) -> list[StoreCandidate]:
        raise CamoufoxUnavailable("camoufox_chua_cai")

    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_delivery_stores_camoufox", _boom
    )
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_gmaps_menu_images_camoufox",
        lambda *a, **k: [],
    )

    orch = SurveyOrchestrator(job_store=store)
    job = orch.execute_job(orch.create_job(_request()).job_id)

    assert job.status == SurveyJobStatus.FAILED
    assert job.error_code == SurveyErrorCode.SOURCE_BLOCKED


def test_empty_market_maps_to_insufficient_data(
    store: JobStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_delivery_stores_camoufox",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_gmaps_menu_images_camoufox",
        lambda *a, **k: [],
    )

    orch = SurveyOrchestrator(job_store=store)
    job = orch.execute_job(orch.create_job(_request()).job_id)

    assert job.status == SurveyJobStatus.FAILED
    assert job.error_code == SurveyErrorCode.INSUFFICIENT_MARKET_DATA


# ── NEEDS_REVIEW (ADR-008) ───────────────────────────────────────────────────


def _patch_dinein_with_review(
    monkeypatch: pytest.MonkeyPatch, *, needs_review: list[dict[str, str]]
) -> None:
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_delivery_stores_camoufox",
        lambda *a, **k: [_online_store(i) for i in range(3)],
    )
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.scrape_gmaps_menu_images_camoufox",
        lambda *a, **k: [_dinein_store(0)],
    )
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2._download_image", lambda url, **k: b"x" * 200
    )
    monkeypatch.setattr(
        "ca_agents.ag_pricing.orchestrator_v2.extract_menu_from_image",
        lambda image_bytes, *, store_id, **k: VisionExtractionResult(
            snapshot=_snapshot(store_id, prices=[45000, 50000, 55000, 60000, 65000]),
            needs_review=needs_review,
        ),
    )


def test_needs_review_is_a_real_stop(
    store: JobStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_dinein_with_review(
        monkeypatch,
        needs_review=[{"name": "Cơm sườn", "raw_text": "??.000", "reason": "price_unreadable"}],
    )

    orch = SurveyOrchestrator(job_store=store)
    job = orch.execute_job(orch.create_job(_request()).job_id)

    assert job.status == SurveyJobStatus.NEEDS_REVIEW
    assert job.response is None
    assert job.error_code is None
    assert job.stores_flagged_for_review == ["gm_0"]
    assert len(job.meta["pending_review"]) == 1
    assert get_pricing_metrics()["jobs_needs_review"] == 1


def test_needs_review_does_not_auto_advance(
    store: JobStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-008: không có auto-approve — chạy lại execute_job phải bị từ chối."""
    _patch_dinein_with_review(
        monkeypatch, needs_review=[{"name": "X", "raw_text": "", "reason": "price_unreadable"}]
    )
    orch = SurveyOrchestrator(job_store=store)
    job = orch.execute_job(orch.create_job(_request()).job_id)
    assert job.status == SurveyJobStatus.NEEDS_REVIEW

    with pytest.raises(SurveyExecutionError):
        orch.execute_job(job.job_id)
    assert job.status == SurveyJobStatus.NEEDS_REVIEW


def test_resume_after_review_completes_with_human_price(
    store: JobStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_dinein_with_review(
        monkeypatch, needs_review=[{"name": "Cơm sườn", "raw_text": "", "reason": "price_unreadable"}]
    )
    orch = SurveyOrchestrator(job_store=store)
    job = orch.execute_job(orch.create_job(_request()).job_id)
    assert job.status == SurveyJobStatus.NEEDS_REVIEW

    submission = SurveyReviewSubmission(
        reviewed_by="lan",
        items=[
            SurveyReviewItem(
                store_id="gm_0",
                item_name_raw="Cơm sườn",
                effective_price_vnd=48000,
            )
        ],
    )
    resumed = orch.resume_after_review(job.job_id, submission)

    assert resumed.status == SurveyJobStatus.COMPLETED
    assert resumed.response is not None
    assert resumed.response.job_id == resumed.job_id
    assert resumed.stores_flagged_for_review == []
    assert resumed.meta["reviewed_by"] == "lan"

    dinein = {r.store_id: r for r in resumed.meta["dinein_records"]}["gm_0"]
    human = [m for m in dinein.menu_items if m.item_name_raw == "Cơm sườn"]
    assert len(human) == 1
    assert human[0].effective_price_vnd == 48000
    assert human[0].confidence == "high"


def test_review_can_reject_a_line(store: JobStore, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_dinein_with_review(
        monkeypatch, needs_review=[{"name": "Món 0", "raw_text": "", "reason": "price_unreadable"}]
    )
    orch = SurveyOrchestrator(job_store=store)
    job = orch.execute_job(orch.create_job(_request()).job_id)

    submission = SurveyReviewSubmission(
        items=[
            SurveyReviewItem(
                store_id="gm_0", item_name_raw="Món 0", effective_price_vnd=0, rejected=True
            )
        ]
    )
    resumed = orch.resume_after_review(job.job_id, submission)
    assert resumed.status == SurveyJobStatus.COMPLETED
    dinein = {r.store_id: r for r in resumed.meta["dinein_records"]}["gm_0"]
    assert all(m.item_name_raw != "Món 0" for m in dinein.menu_items)
    assert len(dinein.menu_items) == 4


def test_resume_from_wrong_state_is_refused(store: JobStore) -> None:
    orch = SurveyOrchestrator(job_store=store)
    job = orch.create_job(_request())
    with pytest.raises(SurveyExecutionError):
        orch.resume_after_review(job.job_id, SurveyReviewSubmission())


def test_global_job_store_singleton() -> None:
    assert get_job_store() is get_job_store()
    reset_job_store()
    assert get_job_store() is not None
