# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Kiểm thử JobStore + SurveyJob state machine (plan mục 2.4).

Tập trung vào các tính chất mà orchestrator và API dựa vào:
- chỉ chuyển state theo đúng bảng `SURVEY_JOB_TRANSITIONS`;
- `FAILED` tới được từ MỌI state (job không được kẹt);
- `COMPLETED`/`FAILED` là terminal;
- store thread-safe và không rò rỉ job giữa các test.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest
from ca_agents.ag_pricing.job_manager import (
    InvalidJobTransitionError,
    JobStore,
    SurveyJob,
    get_job_store,
    reset_job_store,
)
from ca_contracts.catchment_survey_v2 import (
    SURVEY_JOB_TRANSITIONS,
    CatchmentSurveyRequest,
    CatchmentSurveyResponse,
    SurveyErrorCode,
    SurveyJobStatus,
)


def _request(**overrides: Any) -> CatchmentSurveyRequest:
    base: dict[str, Any] = {
        "latitude": 10.7769,
        "longitude": 106.7009,
        "core_category": "cơm tấm",
    }
    base.update(overrides)
    return CatchmentSurveyRequest.model_validate(base)


@pytest.fixture(autouse=True)
def _clean_global_store() -> Any:
    reset_job_store()
    yield
    reset_job_store()


@pytest.fixture
def store() -> JobStore:
    return JobStore()


def _job(status: SurveyJobStatus = SurveyJobStatus.QUEUED) -> SurveyJob:
    return SurveyJob(job_id="j1", request=_request(), status=status)


# ── State machine ────────────────────────────────────────────────────────────


def test_happy_path_transitions_are_all_legal() -> None:
    job = _job()
    for status in (
        SurveyJobStatus.SCRAPING_ONLINE,
        SurveyJobStatus.SCRAPING_DINEIN,
        SurveyJobStatus.OCR_PROCESSING,
        SurveyJobStatus.AGGREGATING,
        SurveyJobStatus.COMPLETED,
    ):
        job.transition_to(status)
    assert job.status == SurveyJobStatus.COMPLETED


def test_needs_review_path_is_legal() -> None:
    job = _job()
    job.transition_to(SurveyJobStatus.SCRAPING_ONLINE)
    job.transition_to(SurveyJobStatus.SCRAPING_DINEIN)
    job.transition_to(SurveyJobStatus.OCR_PROCESSING)
    job.transition_to(SurveyJobStatus.NEEDS_REVIEW)
    job.transition_to(SurveyJobStatus.AGGREGATING)
    job.transition_to(SurveyJobStatus.COMPLETED)
    assert job.status == SurveyJobStatus.COMPLETED


def test_illegal_transition_raises_and_keeps_state() -> None:
    job = _job()
    with pytest.raises(InvalidJobTransitionError) as exc:
        job.transition_to(SurveyJobStatus.COMPLETED)
    assert exc.value.job_id == "j1"
    assert exc.value.current == SurveyJobStatus.QUEUED
    assert exc.value.target == SurveyJobStatus.COMPLETED
    assert job.status == SurveyJobStatus.QUEUED


def test_needs_review_cannot_skip_to_completed() -> None:
    """ADR-008: review phải đi qua AGGREGATING, không nhảy thẳng COMPLETED."""
    assert SurveyJobStatus.COMPLETED not in SURVEY_JOB_TRANSITIONS[
        SurveyJobStatus.NEEDS_REVIEW
    ]
    job = _job(SurveyJobStatus.NEEDS_REVIEW)
    with pytest.raises(InvalidJobTransitionError):
        job.transition_to(SurveyJobStatus.COMPLETED)


@pytest.mark.parametrize("status", list(SurveyJobStatus))
def test_failed_is_reachable_from_every_state(status: SurveyJobStatus) -> None:
    job = _job(status)
    job.mark_failed(SurveyErrorCode.SOURCE_BLOCKED, "nguon_chan_crawler")
    assert job.status == SurveyJobStatus.FAILED
    assert job.error_code == SurveyErrorCode.SOURCE_BLOCKED
    assert job.error_message == "nguon_chan_crawler"


@pytest.mark.parametrize(
    "terminal", [SurveyJobStatus.COMPLETED, SurveyJobStatus.FAILED]
)
def test_terminal_states_have_no_exits(terminal: SurveyJobStatus) -> None:
    assert SURVEY_JOB_TRANSITIONS[terminal] == frozenset()
    job = _job(terminal)
    with pytest.raises(InvalidJobTransitionError):
        job.transition_to(SurveyJobStatus.QUEUED)


def test_transition_updates_timestamp() -> None:
    job = _job()
    before = job.updated_at
    job.updated_at = "2020-01-01T00:00:00+00:00"
    job.transition_to(SurveyJobStatus.SCRAPING_ONLINE)
    assert job.updated_at != "2020-01-01T00:00:00+00:00"
    assert before


def test_set_response_and_flagged_stores() -> None:
    job = _job()
    response = CatchmentSurveyResponse(
        job_id="j1",
        status=SurveyJobStatus.COMPLETED,
        survey_captured_at="2026-09-13T10:00:00+00:00",
        generated_at="2026-09-13T10:05:00+00:00",
    )
    job.set_response(response)
    assert job.response is response

    job.add_flagged_stores(["gm_1", "gm_2"])
    job.add_flagged_stores(["gm_3"])
    assert job.stores_flagged_for_review == ["gm_1", "gm_2", "gm_3"]


def test_meta_is_isolated_per_job() -> None:
    """`meta` dùng default_factory — hai job không được chia sẻ cùng dict."""
    a = SurveyJob(job_id="a", request=_request())
    b = SurveyJob(job_id="b", request=_request())
    a.meta["pending_review"] = [{"store_id": "gm_0"}]
    assert b.meta == {}


# ── JobStore ─────────────────────────────────────────────────────────────────


def test_create_assigns_unique_ids(store: JobStore) -> None:
    first = store.create_job(_request())
    second = store.create_job(_request())
    assert first.job_id != second.job_id
    assert first.status == SurveyJobStatus.QUEUED
    assert store.get_job(first.job_id) is first


def test_get_unknown_job_returns_none(store: JobStore) -> None:
    assert store.get_job("khong-co") is None


def test_update_job_persists_changes(store: JobStore) -> None:
    job = store.create_job(_request())
    job.transition_to(SurveyJobStatus.SCRAPING_ONLINE)
    store.update_job(job)
    # Gán qua biến rồi assert not None: `get_job` trả Optional nên truy cập thẳng
    # `.status` sẽ AttributeError nếu job biến mất — và lỗi đó sẽ hiện thành
    # "test hỏng vì None" thay vì đúng thông điệp "update không lưu".
    reloaded = store.get_job(job.job_id)
    assert reloaded is not None
    assert reloaded.status == SurveyJobStatus.SCRAPING_ONLINE


def test_list_jobs_filters_by_status(store: JobStore) -> None:
    a = store.create_job(_request())
    b = store.create_job(_request())
    a.transition_to(SurveyJobStatus.SCRAPING_ONLINE)
    store.update_job(a)

    assert {j.job_id for j in store.list_jobs(status=SurveyJobStatus.QUEUED)} == {b.job_id}
    assert {j.job_id for j in store.list_jobs(status=SurveyJobStatus.SCRAPING_ONLINE)} == {
        a.job_id
    }
    assert len(store.list_jobs()) == 2


def test_list_jobs_respects_limit(store: JobStore) -> None:
    for _ in range(5):
        store.create_job(_request())
    assert len(store.list_jobs(limit=2)) == 2


def test_delete_job(store: JobStore) -> None:
    job = store.create_job(_request())
    assert store.delete_job(job.job_id) is True
    assert store.get_job(job.job_id) is None
    assert store.delete_job(job.job_id) is False


def test_concurrent_creates_do_not_lose_jobs(store: JobStore) -> None:
    """Store dùng RLock — 40 thread tạo job phải còn đủ 40 job."""
    def worker() -> None:
        for _ in range(5):
            store.create_job(_request())

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(store.list_jobs(limit=1000)) == 40


# ── Global singleton ─────────────────────────────────────────────────────────


def test_global_store_is_singleton_until_reset() -> None:
    first = get_job_store()
    assert get_job_store() is first
    job = first.create_job(_request())

    reset_job_store()
    second = get_job_store()
    assert second is not first
    assert second.get_job(job.job_id) is None
