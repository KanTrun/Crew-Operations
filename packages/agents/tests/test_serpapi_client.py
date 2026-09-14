"""Unit tests cho Central SerpApi Client và Quota Guard."""

from __future__ import annotations

import json
import time
import urllib.error
from email.message import Message
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ca_agents.clients.serpapi_client import (
    SerpApiAuthError,
    SerpApiDisabledError,
    SerpApiQuotaExceededError,
    get_quota_status,
    is_serpapi_enabled,
    search_serpapi,
)


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    cdir = tmp_path / "cache"
    cdir.mkdir(parents=True, exist_ok=True)
    return cdir


@pytest.fixture
def temp_quota_file(tmp_path: Path) -> Path:
    return tmp_path / "quota.json"


def test_is_serpapi_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    assert not is_serpapi_enabled()

    monkeypatch.setenv("SERPAPI_API_KEY", "test_key_123")
    monkeypatch.setenv("SERPAPI_ENABLED", "true")
    assert is_serpapi_enabled()

    monkeypatch.setenv("SERPAPI_ENABLED", "false")
    assert not is_serpapi_enabled()


def test_get_quota_status_fresh(
    monkeypatch: pytest.MonkeyPatch, temp_quota_file: Path
) -> None:
    monkeypatch.setenv("SERPAPI_API_KEY", "test_key_123")
    monkeypatch.setenv("SERPAPI_MONTHLY_LIMIT", "250")
    monkeypatch.setenv("SERPAPI_SAFETY_MARGIN", "10")

    status = get_quota_status(quota_path=temp_quota_file)
    assert status["total_limit"] == 250
    assert status["safety_margin"] == 10
    assert status["usable_limit"] == 240
    assert status["used_requests"] == 0
    assert status["remaining_usable"] == 240


def test_search_serpapi_disabled(
    monkeypatch: pytest.MonkeyPatch, temp_cache_dir: Path, temp_quota_file: Path
) -> None:
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    with pytest.raises(SerpApiDisabledError):
        search_serpapi(
            "google_maps",
            {"q": "cà phê"},
            cache_dir=temp_cache_dir,
            quota_path=temp_quota_file,
        )


def test_search_serpapi_quota_exceeded(
    monkeypatch: pytest.MonkeyPatch, temp_cache_dir: Path, temp_quota_file: Path
) -> None:
    monkeypatch.setenv("SERPAPI_API_KEY", "test_key_123")
    monkeypatch.setenv("SERPAPI_MONTHLY_LIMIT", "250")
    monkeypatch.setenv("SERPAPI_SAFETY_MARGIN", "10")

    # Giả lập đã dùng hết 240/240 lượt khả dụng
    from ca_agents.clients.serpapi_client import _get_current_year_month

    with open(temp_quota_file, "w", encoding="utf-8") as f:
        json.dump({
            "year_month": _get_current_year_month(),
            "used_requests": 240,
        }, f)

    with pytest.raises(SerpApiQuotaExceededError):
        search_serpapi(
            "google_maps",
            {"q": "cà phê"},
            cache_dir=temp_cache_dir,
            quota_path=temp_quota_file,
        )


def test_search_serpapi_cache_hit(
    monkeypatch: pytest.MonkeyPatch, temp_cache_dir: Path, temp_quota_file: Path
) -> None:
    monkeypatch.setenv("SERPAPI_API_KEY", "test_key_123")

    fake_data = {"local_results": [{"title": "Quán Cà Phê A"}]}
    from ca_agents.clients.serpapi_client import _cache_hash, _put_cache_payload

    k = _cache_hash("google_maps", {"q": "cà phê"})
    _put_cache_payload(k, fake_data, cache_dir=temp_cache_dir)

    # Đảm bảo KHÔNG có network call nào diễn ra khi Cache HIT
    with patch("urllib.request.urlopen") as mock_url:
        res = search_serpapi(
            "google_maps",
            {"q": "cà phê"},
            ttl_hours=24.0,
            cache_dir=temp_cache_dir,
            quota_path=temp_quota_file,
        )
        assert res == fake_data
        mock_url.assert_not_called()

    # Quota không bị tăng
    status = get_quota_status(quota_path=temp_quota_file)
    assert status["used_requests"] == 0


def test_search_serpapi_success_and_cache(
    monkeypatch: pytest.MonkeyPatch, temp_cache_dir: Path, temp_quota_file: Path
) -> None:
    monkeypatch.setenv("SERPAPI_API_KEY", "test_key_123")

    mock_resp_data = {"search_metadata": {"status": "Success"}, "local_results": []}
    mock_resp_bytes = json.dumps(mock_resp_data).encode("utf-8")

    mock_http_resp = MagicMock()
    mock_http_resp.status = 200
    mock_http_resp.read.return_value = mock_resp_bytes
    mock_http_resp.__enter__.return_value = mock_http_resp

    with patch("urllib.request.urlopen", return_value=mock_http_resp):
        res = search_serpapi(
            "google_maps",
            {"q": "cà phê tươi"},
            cache_dir=temp_cache_dir,
            quota_path=temp_quota_file,
        )
        assert res == mock_resp_data

    # Quota tăng +1
    status = get_quota_status(quota_path=temp_quota_file)
    assert status["used_requests"] == 1

    # Lần 2 gọi cùng tham số phải HIT cache (urlopen không được gọi)
    with patch("urllib.request.urlopen") as mock_second_call:
        res2 = search_serpapi(
            "google_maps",
            {"q": "cà phê tươi"},
            cache_dir=temp_cache_dir,
            quota_path=temp_quota_file,
        )
        assert res2 == mock_resp_data
        mock_second_call.assert_not_called()
        # Quota vẫn giữ nguyên 1
        assert get_quota_status(quota_path=temp_quota_file)["used_requests"] == 1


def test_search_serpapi_auth_error(
    monkeypatch: pytest.MonkeyPatch, temp_cache_dir: Path, temp_quota_file: Path
) -> None:
    monkeypatch.setenv("SERPAPI_API_KEY", "invalid_key")

    http_err = urllib.error.HTTPError(
        url="https://serpapi.com/search.json",
        code=401,
        msg="Unauthorized",
        # HTTPError.hdrs phải là email Message, không phải dict: truyền {} thì mypy
        # báo arg-type và runtime `.get()` trên header cũng sai kiểu.
        hdrs=Message(),
        fp=MagicMock(read=lambda: b'{"error": "Invalid API key"}'),
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(SerpApiAuthError):
            search_serpapi(
                "google_maps",
                {"q": "cà phê"},
                cache_dir=temp_cache_dir,
                quota_path=temp_quota_file,
            )


def test_search_serpapi_upstream_quota_error(
    monkeypatch: pytest.MonkeyPatch, temp_cache_dir: Path, temp_quota_file: Path
) -> None:
    monkeypatch.setenv("SERPAPI_API_KEY", "valid_key")

    mock_resp_data = {"error": "Your searches left: 0"}
    mock_resp_bytes = json.dumps(mock_resp_data).encode("utf-8")

    mock_http_resp = MagicMock()
    mock_http_resp.status = 200
    mock_http_resp.read.return_value = mock_resp_bytes
    mock_http_resp.__enter__.return_value = mock_http_resp

    with patch("urllib.request.urlopen", return_value=mock_http_resp):
        with pytest.raises(SerpApiQuotaExceededError):
            search_serpapi(
                "google_maps",
                {"q": "cà phê"},
                cache_dir=temp_cache_dir,
                quota_path=temp_quota_file,
            )


def test_circuit_breaker_states() -> None:
    from ca_agents.clients.serpapi_client import CircuitBreaker, CircuitBreakerState

    cb = CircuitBreaker(failure_threshold=3, open_seconds=0.1)
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.allow_request() is True

    # 2 thất bại liên tiếp -> vẫn CLOSED
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.allow_request() is True

    # Thất bại thứ 3 -> ngắt mạch sang OPEN
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.allow_request() is False

    # Đợi open_seconds -> chuyển sang HALF_OPEN
    import time
    time.sleep(0.12)
    assert cb.allow_request() is True
    assert cb.state == CircuitBreakerState.HALF_OPEN

    # Thành công khi HALF_OPEN -> quay về CLOSED
    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.consecutive_failures == 0


def test_circuit_breaker_open_blocks_request(
    monkeypatch: pytest.MonkeyPatch, temp_cache_dir: Path, temp_quota_file: Path
) -> None:
    from ca_agents.clients.serpapi_client import (
        CircuitBreaker,
        CircuitBreakerState,
        SerpApiCircuitOpenError,
    )

    monkeypatch.setenv("SERPAPI_API_KEY", "test_key")
    cb = CircuitBreaker(failure_threshold=1, open_seconds=60.0)
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN

    with pytest.raises(SerpApiCircuitOpenError):
        search_serpapi(
            "google_maps",
            {"q": "cà phê cb test"},
            cache_dir=temp_cache_dir,
            quota_path=temp_quota_file,
            circuit_breaker=cb,
        )


def test_l1_in_memory_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    from ca_agents.clients.serpapi_client import _get_l1_cache, _put_l1_cache, clear_l1_cache

    clear_l1_cache()
    assert _get_l1_cache("test_key") is None

    _put_l1_cache("test_key", {"title": "L1 Cached Store"})
    cached = _get_l1_cache("test_key")
    assert cached is not None
    assert cached["title"] == "L1 Cached Store"
    clear_l1_cache()
    assert _get_l1_cache("test_key") is None


def test_retry_backoff_on_500(monkeypatch: pytest.MonkeyPatch, temp_cache_dir: Path, temp_quota_file: Path) -> None:
    from ca_agents.clients.serpapi_client import CircuitBreaker

    monkeypatch.setenv("SERPAPI_API_KEY", "test_key")
    cb = CircuitBreaker()

    # Giả lập 2 lần lỗi 500, lần 3 thành công
    mock_resp_data = {"local_results": [{"title": "Retry Success"}]}
    mock_success_resp = MagicMock()
    mock_success_resp.status = 200
    mock_success_resp.read.return_value = json.dumps(mock_resp_data).encode("utf-8")
    mock_success_resp.__enter__.return_value = mock_success_resp

    err_500 = urllib.error.HTTPError(
        url="https://serpapi.com/search.json",
        code=500,
        msg="Internal Server Error",
        hdrs=Message(),
        fp=MagicMock(read=lambda: b"Server Error"),
    )

    with patch("urllib.request.urlopen", side_effect=[err_500, err_500, mock_success_resp]) as mock_call:
        res = search_serpapi(
            "google_maps",
            {"q": "cà phê retry test"},
            cache_dir=temp_cache_dir,
            quota_path=temp_quota_file,
            circuit_breaker=cb,
        )
        assert res == mock_resp_data
        assert mock_call.call_count == 3


def test_quota_threshold_levels(monkeypatch: pytest.MonkeyPatch, temp_quota_file: Path) -> None:
    from ca_agents.clients.serpapi_client import _get_current_year_month

    monkeypatch.setenv("SERPAPI_API_KEY", "test_key")
    monkeypatch.setenv("SERPAPI_MONTHLY_LIMIT", "250")
    monkeypatch.setenv("SERPAPI_SAFETY_MARGIN", "10")
    monkeypatch.setenv("SERPAPI_WARN_THRESHOLD", "200")
    monkeypatch.setenv("SERPAPI_INFO_THRESHOLD", "150")

    # Mức NORMAL (< 150)
    with open(temp_quota_file, "w", encoding="utf-8") as f:
        json.dump({"year_month": _get_current_year_month(), "used_requests": 100}, f)
    s = get_quota_status(quota_path=temp_quota_file)
    assert s["warning_level"] == "NORMAL"

    # Mức INFO (150-199)
    with open(temp_quota_file, "w", encoding="utf-8") as f:
        json.dump({"year_month": _get_current_year_month(), "used_requests": 160}, f)
    s = get_quota_status(quota_path=temp_quota_file)
    assert s["warning_level"] == "INFO"

    # Mức WARN (200-239)
    with open(temp_quota_file, "w", encoding="utf-8") as f:
        json.dump({"year_month": _get_current_year_month(), "used_requests": 205}, f)
    s = get_quota_status(quota_path=temp_quota_file)
    assert s["warning_level"] == "WARN"

    # Mức CRITICAL (>= 240)
    with open(temp_quota_file, "w", encoding="utf-8") as f:
        json.dump({"year_month": _get_current_year_month(), "used_requests": 240}, f)
    s = get_quota_status(quota_path=temp_quota_file)
    assert s["warning_level"] == "CRITICAL"


def test_mask_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from ca_agents.clients.serpapi_client import mask_api_key

    assert mask_api_key("1234567890abcdef") == "ak_***masked***"
    assert mask_api_key("") == ""
    assert mask_api_key(None) == ""

    # Test default param masks configured env key
    monkeypatch.setenv("SERPAPI_API_KEY", "env_secret_key_123")
    assert mask_api_key() == "ak_***masked***"
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    assert mask_api_key() == ""


def test_stale_if_error(monkeypatch: pytest.MonkeyPatch, temp_cache_dir: Path, temp_quota_file: Path) -> None:
    from ca_agents.clients.serpapi_client import (
        CircuitBreaker,
        _cache_hash,
    )

    monkeypatch.setenv("SERPAPI_API_KEY", "test_key")
    old_data = {"local_results": [{"title": "Stale Coffee"}]}
    k = _cache_hash("google_maps", {"q": "cà phê stale"})
    # Lưu cache cũ quá hạn (2 ngày trước) để cache tươi miss
    temp_cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = temp_cache_dir / f"{k}.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({"cached_at": time.time() - 172800, "data": old_data}, f)

    cb = CircuitBreaker(failure_threshold=1, open_seconds=60.0)
    cb.record_failure()  # Circuit Breaker OPEN

    # Cho phép stale_on_error -> trả cache cũ kèm stale=True
    res = search_serpapi(
        "google_maps",
        {"q": "cà phê stale"},
        cache_dir=temp_cache_dir,
        quota_path=temp_quota_file,
        circuit_breaker=cb,
        allow_stale_on_error=True,
    )
    assert res.get("stale") is True
    assert res.get("data_source") == "cache"
    assert res["local_results"][0]["title"] == "Stale Coffee"


def test_get_serpapi_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    from ca_agents.clients.serpapi_client import get_serpapi_metrics

    monkeypatch.setenv("SERPAPI_API_KEY", "test_key")
    metrics = get_serpapi_metrics()
    assert "enabled" in metrics
    assert "status" in metrics
    assert "quota" in metrics
    assert "circuit_breaker" in metrics
    assert "metrics" in metrics
    assert "cache_hit_rate_pct" in metrics
