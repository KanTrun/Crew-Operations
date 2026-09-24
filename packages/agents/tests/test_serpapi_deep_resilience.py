# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Bộ kiểm thử chuyên sâu (Deep Resilience & Robustness Testing) cho SerpApi v2.0.

Nội dung kiểm thử:
1. Circuit Breaker State Machine & HALF_OPEN single failure immediate trip to OPEN.
2. An toàn đa luồng (Thread-safety & Concurrency) cho Circuit Breaker, L1 Cache, Metrics, và Quota Guard.
3. Bảo mật & Masking dữ liệu theo Nghị định 13/2023/NĐ-CP (sanitize_url, che giấu API key trong logs và exceptions).
4. Khả năng tự phục hồi (Self-Healing) khi file quota bị hỏng (corrupted JSON / 0-byte) hoặc chuyển giao tháng mới.
5. Kiểm thử biên và chịu lỗi (Boundary & Fuzzing) cho điểm đánh giá (rating), số lượt review, và tọa độ Haversine.
6. Xử lý phản hồi lỗi nghiệp vụ từ SerpApi dưới dạng HTTP 200 (Deferred Success Verification).
7. Rate Limiter trượt 60s đa luồng và tự động dọn dẹp bộ nhớ (Memory Leak Prevention).
"""

from __future__ import annotations

import concurrent.futures
import json
import time
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest
from ca_agents.clients.serpapi_client import (
    CircuitBreaker,
    CircuitBreakerState,
    SerpApiError,
    SerpApiQuotaExceededError,
    _get_l1_cache,
    _increment_quota,
    _load_quota_data,
    _put_l1_cache,
    clear_l1_cache,
    get_quota_status,
    get_serpapi_metrics,
    sanitize_url,
    search_serpapi,
)
from ca_agents.sources.gmaps_serpapi_source import (
    _parse_rating,
    _parse_review_count,
    fetch_gmaps_reviews_serpapi,
    haversine_distance_km,
    parse_gmaps_results_to_candidates,
)
from ca_api.interfaces.http.pricing_radar import (
    _USER_REQUEST_TIMESTAMPS,
    _check_rate_limit,
    clear_rate_limits,
)
from fastapi import HTTPException


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    cdir = tmp_path / "cache"
    cdir.mkdir(parents=True, exist_ok=True)
    return cdir


@pytest.fixture
def temp_quota_file(tmp_path: Path) -> Path:
    return tmp_path / "quota.json"


# ══════════════════════════════════════════════════════════════════════════════
# 1. Circuit Breaker State Machine & HALF_OPEN Verification
# ══════════════════════════════════════════════════════════════════════════════


def test_circuit_breaker_half_open_probing_and_single_failure_trips() -> None:
    """Kiểm tra thuộc tính SOTA: Khi ở HALF_OPEN, CHỈ CẦN 1 lỗi là phải lập tức ngắt mạch về OPEN."""
    cb = CircuitBreaker(failure_threshold=3, open_seconds=0.1)

    # 1. Ban đầu CLOSED
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.allow_request() is True

    # 2. Gặp 3 lỗi liên tiếp -> OPEN
    cb.record_failure()
    assert cb.state == CircuitBreakerState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitBreakerState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.allow_request() is False

    # 3. Đợi hết open_seconds -> chuyển sang HALF_OPEN khi thăm dò
    time.sleep(0.12)
    assert cb.allow_request() is True
    assert cb.state == CircuitBreakerState.HALF_OPEN

    # 4. Khi đang HALF_OPEN, CHỈ 1 lỗi phải lập tức ngắt lại về OPEN (không cần chờ đủ 3 lỗi)
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.allow_request() is False


def test_circuit_breaker_half_open_success_closes_circuit() -> None:
    """Khi ở HALF_OPEN, một yêu cầu thành công đưa Circuit Breaker trở lại CLOSED."""
    cb = CircuitBreaker(failure_threshold=2, open_seconds=0.05)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN

    time.sleep(0.06)
    assert cb.allow_request() is True
    assert cb.state == CircuitBreakerState.HALF_OPEN

    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.consecutive_failures == 0


def test_circuit_breaker_multithreaded_concurrency() -> None:
    """Kiểm tra an toàn luồng của CircuitBreaker khi hàng chục luồng truy cập đồng thời."""
    cb = CircuitBreaker(failure_threshold=5, open_seconds=0.1)
    errors: list[Exception] = []

    def worker_action(idx: int) -> None:
        try:
            if idx % 3 == 0:
                cb.record_failure()
            elif idx % 3 == 1:
                cb.record_success()
            else:
                _ = cb.allow_request()
                _ = cb.get_info()
        except Exception as e:
            errors.append(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker_action, i) for i in range(100)]
        concurrent.futures.wait(futures)

    assert len(errors) == 0
    info = cb.get_info()
    assert info["state"] in (CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Security & Data Privacy (Nghị định 13/2023/NĐ-CP & Sanitization)
# ══════════════════════════════════════════════════════════════════════════════


def test_sanitize_url_masks_all_secret_keys() -> None:
    """Kiểm tra hàm sanitize_url che giấu toàn bộ các biến thể bí mật trong URL."""
    url = (
        "https://serpapi.com/search.json"
        "?engine=google_maps&q=coffee&api_key=secret_xyz_12345&hl=vi"
    )
    sanitized = sanitize_url(url)
    assert "secret_xyz_12345" not in sanitized
    assert "api_key=ak_%2A%2A%2Amasked%2A%2A%2A" in sanitized or "ak_***masked***" in sanitized
    assert "engine=google_maps" in sanitized
    assert "hl=vi" in sanitized


def test_sanitize_url_handles_malformed_url_gracefully() -> None:
    """Kiểm tra URL hỏng hoặc định dạng lạ vẫn được che giấu bí mật bằng fallback regex."""
    malformed = "invalid-protocol://::???api_key=super_secret_key_999&param=1"
    sanitized = sanitize_url(malformed)
    assert "super_secret_key_999" not in sanitized
    assert "ak_***masked***" in sanitized


def test_no_api_key_leak_in_exceptions(
    monkeypatch: pytest.MonkeyPatch, temp_cache_dir: Path, temp_quota_file: Path
) -> None:
    """Đảm bảo ngoại lệ phát sinh không bao giờ in lộ raw API key trong thông báo lỗi."""
    secret_key = "super_confidential_serpapi_key_98765"
    monkeypatch.setenv("SERPAPI_API_KEY", secret_key)
    monkeypatch.setenv("SERPAPI_ENABLED", "true")

    with patch(
        "ca_agents.clients.serpapi_client._execute_http_request",
        side_effect=urllib.error.URLError(f"Connection failed to https://serpapi.com?api_key={secret_key}"),
    ):
        with pytest.raises(SerpApiError) as exc_info:
            search_serpapi(
                "google_maps",
                {"q": "cafe"},
                cache_dir=temp_cache_dir,
                quota_path=temp_quota_file,
                circuit_breaker=CircuitBreaker(open_seconds=60.0),
            )

        err_str = str(exc_info.value)
        assert secret_key not in err_str
        assert "ak_***masked***" in err_str


def test_review_anonymization_strips_pii(
    monkeypatch: pytest.MonkeyPatch, temp_cache_dir: Path, temp_quota_file: Path
) -> None:
    """Đảm bảo fetch_gmaps_reviews_serpapi bóc tách sạch sẽ thông tin định danh cá nhân."""
    monkeypatch.setenv("SERPAPI_API_KEY", "test_key")
    monkeypatch.setenv("SERPAPI_ENABLED", "true")

    raw_response = {
        "reviews": [
            {
                "user": {
                    "name": "Nguyễn Văn A",
                    "link": "https://google.com/maps/contrib/12345",
                    "thumbnail": "https://avatar.com/user123.jpg",
                },
                "rating": 4.5,
                "date": "1 ngày trước",
                "snippet": "Cà phê ngon, không gian yên tĩnh.",
            }
        ]
    }

    with patch("ca_agents.sources.gmaps_serpapi_source.search_serpapi", return_value=raw_response):
        reviews = fetch_gmaps_reviews_serpapi(
            "ChIJ123456",
            cache_dir=temp_cache_dir,
            quota_path=temp_quota_file,
        )

    assert len(reviews) == 1
    r = reviews[0]
    assert r["rating"] == 4.5
    assert r["snippet"] == "Cà phê ngon, không gian yên tĩnh."
    assert r["anonymized"] is True
    # Tuyệt đối không chứa thông tin định danh cá nhân (PII)
    assert "user" not in r
    assert "name" not in r
    assert "thumbnail" not in r
    assert "link" not in r


# ══════════════════════════════════════════════════════════════════════════════
# 3. Quota Guard Durability & Self-Healing
# ══════════════════════════════════════════════════════════════════════════════


def test_quota_file_corrupted_json_recovery(temp_quota_file: Path) -> None:
    """Tự phục hồi khi file quota bị hỏng (corrupted JSON hoặc byte rỗng do ngắt điện)."""
    temp_quota_file.write_text("{ this is corrupted invalid json }}}", encoding="utf-8")

    # Đọc quota không bị văng crash mà tự khởi tạo lại mặc định
    status = get_quota_status(temp_quota_file)
    assert status["used_requests"] == 0
    assert status["remaining_usable"] == 240

    # Ghi nhận lượt mới khôi phục file quota hợp lệ
    new_used = _increment_quota(temp_quota_file)
    assert new_used == 1

    # File phải được ghi lại chuẩn JSON
    saved_data = json.loads(temp_quota_file.read_text(encoding="utf-8"))
    assert saved_data["used_requests"] == 1


def test_quota_month_rollover_resets_counter(temp_quota_file: Path) -> None:
    """Tự động reset bộ đếm khi bước sang tháng mới."""
    old_data = {
        "year_month": "2026-01",  # Tháng cũ
        "used_requests": 239,
        "last_updated": "2026-01-31T23:59:59Z",
    }
    temp_quota_file.write_text(json.dumps(old_data), encoding="utf-8")

    # Khi load cho tháng hiện tại, dữ liệu tháng cũ bị bỏ qua
    current_data = _load_quota_data(temp_quota_file)
    assert current_data["used_requests"] == 0


def test_concurrent_quota_increments_thread_safe(temp_quota_file: Path) -> None:
    """Kiểm tra an toàn luồng khi nhiều request đồng thời ghi nhận hạn ngạch."""
    num_threads = 15

    def inc_action() -> int:
        return _increment_quota(temp_quota_file)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(lambda _: inc_action(), range(num_threads)))

    assert len(results) == num_threads
    final_status = get_quota_status(temp_quota_file)
    assert final_status["used_requests"] == num_threads


def test_quota_fail_closed_at_exact_cutoff(
    monkeypatch: pytest.MonkeyPatch, temp_cache_dir: Path, temp_quota_file: Path
) -> None:
    """Fail-closed tuyệt đối khi chạm ngưỡng an toàn 240."""
    monkeypatch.setenv("SERPAPI_API_KEY", "test_key")
    monkeypatch.setenv("SERPAPI_ENABLED", "true")
    monkeypatch.setenv("SERPAPI_MONTHLY_LIMIT", "250")
    monkeypatch.setenv("SERPAPI_SAFETY_MARGIN", "10")  # Usable limit = 240

    temp_quota_file.write_text(
        json.dumps({
            "year_month": get_quota_status()["year_month"],
            "used_requests": 240,
            "last_updated": "2026-09-13T00:00:00Z",
        }),
        encoding="utf-8",
    )

    with pytest.raises(SerpApiQuotaExceededError) as exc_info:
        search_serpapi(
            "google_maps",
            {"q": "test"},
            cache_dir=temp_cache_dir,
            quota_path=temp_quota_file,
        )

    assert "ngưỡng an toàn" in str(exc_info.value)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Parser Robustness & Boundary Conditions (Rating, Review, Distance)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("input_val", "expected"),
    [
        (None, 0.0),
        ("", 0.0),
        ("invalid", 0.0),
        (4.5, 4.5),
        ("4.8", 4.8),
        (5.5, 5.0),    # Clamped max 5.0
        (-2.0, 0.0),   # Clamped min 0.0
        (0, 0.0),
    ],
)
def test_parse_rating_boundary_cases(input_val: object, expected: float) -> None:
    assert _parse_rating(input_val) == expected


@pytest.mark.parametrize(
    ("input_val", "expected"),
    [
        (None, 0),
        ("", 0),
        ("0", 0),
        (150, 150),
        (25.0, 25),
        ("1,250", 1250),
        ("1.2k", 1200),
        ("3.5K", 3500),
        ("2,345 đánh giá", 2345),
        ("-10", 0),
        ("N/A", 0),
    ],
)
def test_parse_review_count_edge_cases(input_val: object, expected: int) -> None:
    assert _parse_review_count(input_val) == expected


def test_haversine_distance_boundary_points() -> None:
    """Kiểm tra tính toán khoảng cách Haversine với các tọa độ đặc biệt."""
    # Điểm trùng nhau
    assert haversine_distance_km(10.77, 106.70, 10.77, 106.70) == 0.0

    # Điểm tại xích đạo
    dist_eq = haversine_distance_km(0.0, 0.0, 0.0, 1.0)
    assert 111.0 <= dist_eq <= 112.0

    # Cực Bắc tới Cực Nam
    dist_poles = haversine_distance_km(90.0, 0.0, -90.0, 0.0)
    assert 20000.0 <= dist_poles <= 20050.0

    # Tọa độ đối cực (Antipodal) không gây math domain error
    dist_anti = haversine_distance_km(0.0, 0.0, 0.0, 180.0)
    assert 20000.0 <= dist_anti <= 20050.0


def test_gmaps_parser_skips_corrupted_candidates() -> None:
    """Kiểm tra parser lọc bỏ các bản ghi khuyết thiếu dữ liệu bắt buộc."""
    payload = {
        "local_results": [
            "not a dict item",
            {"title": "Quán không có ID"},
            {"place_id": "id_khong_co_ten", "title": ""},
            {
                "place_id": "valid_store_1",
                "title": "Quán Cà Phê Chuẩn",
                "rating": "4.7",
                "reviews": "1,200 đánh giá",
                "gps_coordinates": {"latitude": 10.77, "longitude": 106.70},
            },
        ]
    }

    candidates = parse_gmaps_results_to_candidates(
        payload,
        origin_lat=10.77,
        origin_lng=106.70,
        radius_km=5.0,
    )
    assert len(candidates) == 1
    c = candidates[0]
    assert c.id == "valid_store_1"
    assert c.name == "Quán Cà Phê Chuẩn"
    assert c.rating == 4.7
    assert c.review_count == 1200


# ══════════════════════════════════════════════════════════════════════════════
# 5. Upstream HTTP 200 Error Handling (Deferred Success Verification)
# ══════════════════════════════════════════════════════════════════════════════


def test_upstream_http_200_error_trips_circuit_breaker(
    monkeypatch: pytest.MonkeyPatch, temp_cache_dir: Path, temp_quota_file: Path
) -> None:
    """SerpApi trả HTTP 200 kèm payload {"error": "..."} không được coi là thành công mà phải ghi nhận failure."""
    monkeypatch.setenv("SERPAPI_API_KEY", "test_key")
    monkeypatch.setenv("SERPAPI_ENABLED", "true")

    cb = CircuitBreaker(failure_threshold=1, open_seconds=60.0)
    mock_resp = (200, json.dumps({"error": "Your searches left: 0"}))

    with patch("ca_agents.clients.serpapi_client._execute_http_request", return_value=mock_resp):
        with pytest.raises(SerpApiQuotaExceededError):
            search_serpapi(
                "google_maps",
                {"q": "cafe"},
                cache_dir=temp_cache_dir,
                quota_path=temp_quota_file,
                circuit_breaker=cb,
            )

    # Circuit breaker phải ngắt OPEN vì gặp lỗi payload
    assert cb.state == CircuitBreakerState.OPEN


# ══════════════════════════════════════════════════════════════════════════════
# 6. Rate Limiter Memory Management & Thread Concurrency
# ══════════════════════════════════════════════════════════════════════════════


def test_rate_limiter_prunes_inactive_users() -> None:
    """Kiểm tra dọn dẹp các user không còn hoạt động (> 60s) để chống rò rỉ bộ nhớ RAM."""
    clear_rate_limits()
    old_time = time.time() - 100.0
    _USER_REQUEST_TIMESTAMPS["inactive_user_1"] = [old_time]
    _USER_REQUEST_TIMESTAMPS["inactive_user_2"] = [old_time]
    _USER_REQUEST_TIMESTAMPS["active_user"] = [time.time()]

    # Khi user mới gọi, hệ thống dọn dẹp các user cũ
    _check_rate_limit("new_user")

    assert "inactive_user_1" not in _USER_REQUEST_TIMESTAMPS
    assert "inactive_user_2" not in _USER_REQUEST_TIMESTAMPS
    assert "active_user" in _USER_REQUEST_TIMESTAMPS
    assert "new_user" in _USER_REQUEST_TIMESTAMPS
    clear_rate_limits()


def test_rate_limiter_multithreaded_burst() -> None:
    """Gửi 10 request đồng thời từ 1 user: chính xác 3 request pass, 7 request bị 429."""
    clear_rate_limits()
    success_count = 0
    rate_limited_count = 0

    def call_rate_limiter() -> bool:
        try:
            _check_rate_limit("spamming_user")
            return True
        except HTTPException as exc:
            if exc.status_code == 429:
                return False
            raise

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(call_rate_limiter) for _ in range(10)]
        results = [f.result() for f in futures]

    success_count = sum(1 for r in results if r is True)
    rate_limited_count = sum(1 for r in results if r is False)

    assert success_count == 3
    assert rate_limited_count == 7
    clear_rate_limits()


# ══════════════════════════════════════════════════════════════════════════════
# 7. L1 Cache Thread Safety & Metrics Integrity
# ══════════════════════════════════════════════════════════════════════════════


def test_l1_cache_multithreaded_read_write() -> None:
    """Kiểm tra đọc ghi L1 cache đồng thời không gây corrupt dict."""
    clear_l1_cache()

    def cache_worker(idx: int) -> None:
        key = f"key_{idx % 5}"
        _put_l1_cache(key, {"idx": idx})
        _ = _get_l1_cache(key)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(cache_worker, i) for i in range(100)]
        concurrent.futures.wait(futures)

    clear_l1_cache()


def test_observability_metrics_export() -> None:
    """Kiểm tra hàm get_serpapi_metrics trả về đúng cấu trúc Prometheus / Dashboard."""
    metrics = get_serpapi_metrics()
    assert "enabled" in metrics
    assert "status" in metrics
    assert "quota" in metrics
    assert "circuit_breaker" in metrics
    assert "metrics" in metrics
    assert "cache_hit_rate_pct" in metrics
    assert isinstance(metrics["cache_hit_rate_pct"], float)
