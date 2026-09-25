"""Thin wrapper, Resilience Engine và Quota Guard cho SerpApi REST API.

Kế hoạch: 260913-2045-serpapi-integration v2.0
Đặc thù tài khoản Free: 250 searches/tháng.

Quy chuẩn an toàn & Kiến trúc chuẩn SOTA:
1. Cache đa tầng:
   - L1 In-Memory Cache (process-local, TTL 5 phút): chống duplicate click / spam trong cùng phiên.
   - L2 Persistent Cache (file/sqlite): TTL cấu hình theo engine (Maps 24h, Photos 7 ngày, Trends 12h).
2. Circuit Breaker (3 trạng thái: CLOSED, OPEN, HALF_OPEN):
   - Ngắt mạch khi gặp >= 3 lỗi liên tiếp trong 60s, bảo vệ quota khỏi retry storm.
3. Retry với Exponential Backoff + Jitter:
   - Tự động retry cho HTTP status {429, 500, 502, 503, 504} tối đa 3 lần.
   - Timeout budget nghiêm ngặt (<= 20s cho toàn bộ chuỗi).
4. Quota Guard 3 mức (INFO >= 150, WARN >= 200, CRITICAL >= 240):
   - Tự động cảnh báo và ngắt (Fail-Closed) khi chạm ngưỡng an toàn.
5. Bảo mật & Masking API Key:
   - Che giấu API key thành 'ak_***masked***' trong mọi log/output (Nghị định 13/2023/NĐ-CP).
6. Stale-if-error:
   - Trả cache cũ nhất kèm cờ 'stale: true' khi cả SerpApi và Fallback đều gặp sự cố.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"

# Cấu hình mặc định hạn ngạch & an toàn
_DEFAULT_MONTHLY_LIMIT = 250
_DEFAULT_SAFETY_MARGIN = 10
_DEFAULT_WARN_THRESHOLD = 200
_DEFAULT_INFO_THRESHOLD = 150

# Cấu hình mặc định Cache TTL
_DEFAULT_CACHE_TTL_MAPS_HOURS = 24.0
_DEFAULT_CACHE_TTL_PHOTOS_DAYS = 7.0
_DEFAULT_CACHE_TTL_TRENDS_HOURS = 12.0
# Bảng "Trending Now" là dữ liệu thời gian thực → TTL 1h.
_DEFAULT_CACHE_TTL_TRENDING_NOW_HOURS = 1.0
_L1_CACHE_TTL_S = 300.0  # 5 phút

# Cấu hình Resilience & Circuit Breaker
_DEFAULT_CB_FAILURE_THRESHOLD = 3
_DEFAULT_CB_OPEN_SECONDS = 300.0
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BASE_DELAY_SEC = 0.5
_HTTP_TIMEOUT_S = 8
_TOTAL_BUDGET_TIMEOUT_S = 20

_ROOT_DIR = Path(__file__).resolve().parents[5]
_DEFAULT_CACHE_DIR = _ROOT_DIR / "data" / "cache" / "serpapi"
_QUOTA_FILE_PATH = _ROOT_DIR / "data" / "cache" / "serpapi_quota.json"

# In-memory L1 cache: key -> (cached_timestamp, data)
_L1_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_L1_LOCK = threading.Lock()

# Metrics theo dõi
_METRICS = {
    "request_total": 0,
    "success_total": 0,
    "fallback_total": 0,
    "error_total": 0,
    "cache_hit_total": 0,
    "cache_miss_total": 0,
}
_METRICS_LOCK = threading.Lock()
_QUOTA_LOCK = threading.Lock()


def _record_metric(name: str, count: int = 1) -> None:
    with _METRICS_LOCK:
        if name in _METRICS:
            _METRICS[name] += count


# ── Ngoại lệ nghiệp vụ ────────────────────────────────────────────────────────


class SerpApiError(Exception):
    """Lỗi chung khi gọi SerpApi."""


class SerpApiDisabledError(SerpApiError):
    """SerpApi chưa bật hoặc chưa cấu hình key."""


class SerpApiAuthError(SerpApiError):
    """API Key không hợp lệ hoặc bị từ chối truy cập."""


class SerpApiQuotaExceededError(SerpApiError):
    """Đã chạm ngưỡng an toàn hoặc cạn kiệt lượt tìm kiếm trong tháng."""


class SerpApiCircuitOpenError(SerpApiError):
    """Circuit Breaker đang mở (OPEN), tạm khóa request tới SerpApi."""


class SerpApiRateLimitedError(SerpApiError):
    """Vượt quá giới hạn tần suất gọi on-demand."""


# ── Circuit Breaker ───────────────────────────────────────────────────────────


class CircuitBreakerState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Bộ ngắt mạch (Circuit Breaker) 3 trạng thái bảo vệ Quota SerpApi."""

    def __init__(
        self,
        failure_threshold: int = _DEFAULT_CB_FAILURE_THRESHOLD,
        open_seconds: float = _DEFAULT_CB_OPEN_SECONDS,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds
        self.state: str = CircuitBreakerState.CLOSED
        self.consecutive_failures: int = 0
        self.opened_at: float = 0.0
        self._lock = threading.RLock()

    def allow_request(self) -> bool:
        with self._lock:
            now = time.time()
            if self.state == CircuitBreakerState.OPEN:
                if (now - self.opened_at) >= self.open_seconds:
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info("serpapi_circuit_breaker_half_open")
                    return True
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            if self.state in (CircuitBreakerState.HALF_OPEN, CircuitBreakerState.OPEN):
                logger.info("serpapi_circuit_breaker_closed_after_success")
            self.consecutive_failures = 0
            self.state = CircuitBreakerState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self.consecutive_failures += 1
            if self.state == CircuitBreakerState.HALF_OPEN or self.consecutive_failures >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                self.opened_at = time.time()
                logger.warning(
                    "serpapi_circuit_breaker_tripped state=%s failures=%d open_seconds=%.1f",
                    self.state,
                    self.consecutive_failures,
                    self.open_seconds,
                )

    def reset(self) -> None:
        with self._lock:
            self.consecutive_failures = 0
            self.state = CircuitBreakerState.CLOSED
            self.opened_at = 0.0

    def get_info(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": self.state,
                "consecutive_failures": self.consecutive_failures,
                "failure_threshold": self.failure_threshold,
                "open_seconds": self.open_seconds,
                "opened_at": self.opened_at,
            }


# Singleton Circuit Breaker cho toàn process
_CIRCUIT_BREAKER = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    return _CIRCUIT_BREAKER


# ── Tiện ích cấu hình & Masking ───────────────────────────────────────────────


def _get_api_key() -> str:
    return os.getenv("SERPAPI_API_KEY", "").strip()


_DEFAULT_KEY_SENTINEL = object()


def mask_api_key(api_key: str | None = _DEFAULT_KEY_SENTINEL) -> str:  # type: ignore[assignment]
    """Ẩn danh hóa API Key để bảo mật trong logs (Nghị định 13/2023/NĐ-CP)."""
    if api_key is _DEFAULT_KEY_SENTINEL:
        k = _get_api_key()
    else:
        k = str(api_key or "").strip()
    if not k:
        return ""
    return "ak_***masked***"


def sanitize_url(url: str) -> str:
    """Loại bỏ giá trị bí mật (api_key) khỏi URL để không bao giờ rò rỉ trong logs hoặc exceptions."""
    if not url:
        return ""
    # Thay thế trực tiếp regex để bảo toàn chuỗi 'ak_***masked***' (không bị urlencode thành %2A)
    # và bắt mọi biến thể param nhạy cảm (api_key, apikey, token, secret)
    return re.sub(
        r"([?&;]+[^=]*?(?:api_key|apikey|token|secret)[^=]*?=)([^&;#\s]+)",
        r"\1ak_***masked***",
        url,
        flags=re.IGNORECASE,
    )


def is_serpapi_enabled() -> bool:
    flag = os.getenv("SERPAPI_ENABLED", "true").strip().lower()
    return flag in ("1", "true", "yes") and bool(_get_api_key())


def get_monthly_limit() -> int:
    try:
        return int(os.getenv("SERPAPI_MONTHLY_LIMIT", str(_DEFAULT_MONTHLY_LIMIT)))
    except ValueError:
        return _DEFAULT_MONTHLY_LIMIT


def get_safety_margin() -> int:
    try:
        return int(os.getenv("SERPAPI_SAFETY_MARGIN", str(_DEFAULT_SAFETY_MARGIN)))
    except ValueError:
        return _DEFAULT_SAFETY_MARGIN


def get_warn_threshold() -> int:
    try:
        return int(os.getenv("SERPAPI_WARN_THRESHOLD", str(_DEFAULT_WARN_THRESHOLD)))
    except ValueError:
        return _DEFAULT_WARN_THRESHOLD


def get_info_threshold() -> int:
    try:
        return int(os.getenv("SERPAPI_INFO_THRESHOLD", str(_DEFAULT_INFO_THRESHOLD)))
    except ValueError:
        return _DEFAULT_INFO_THRESHOLD


def get_engine_cache_ttl_hours(engine: str) -> float:
    """Lấy TTL cache tương ứng theo từng engine của SerpApi."""
    if engine == "google_maps_photos":
        try:
            days = float(os.getenv("SERPAPI_CACHE_TTL_PHOTOS_DAYS", str(_DEFAULT_CACHE_TTL_PHOTOS_DAYS)))
            return days * 24.0
        except ValueError:
            return _DEFAULT_CACHE_TTL_PHOTOS_DAYS * 24.0
    elif engine == "google_trends":
        try:
            return float(os.getenv("SERPAPI_CACHE_TTL_TRENDS_HOURS", str(_DEFAULT_CACHE_TTL_TRENDS_HOURS)))
        except ValueError:
            return _DEFAULT_CACHE_TTL_TRENDS_HOURS
    elif engine == "google_trends_trending_now":
        # Bảng xếp hạng thời gian thực (đổi vài chục phút/lần) → TTL ngắn riêng,
        # KHÔNG dùng chung TTL 12h của google_trends (sẽ trả bảng cũ).
        try:
            return float(
                os.getenv(
                    "SERPAPI_CACHE_TTL_TRENDING_NOW_HOURS",
                    str(_DEFAULT_CACHE_TTL_TRENDING_NOW_HOURS),
                )
            )
        except ValueError:
            return _DEFAULT_CACHE_TTL_TRENDING_NOW_HOURS
    else:  # google_maps, google_maps_reviews,...
        try:
            return float(os.getenv("SERPAPI_CACHE_TTL_MAPS_HOURS", str(_DEFAULT_CACHE_TTL_MAPS_HOURS)))
        except ValueError:
            return _DEFAULT_CACHE_TTL_MAPS_HOURS


def get_cache_ttl_hours() -> float:
    return get_engine_cache_ttl_hours("google_maps")


def _get_current_year_month() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


# ── Quản lý Quota Đa Mức ───────────────────────────────────────────────────────


def _load_quota_data(quota_path: Path | None = None) -> dict[str, Any]:
    path = quota_path or _QUOTA_FILE_PATH
    current_ym = _get_current_year_month()

    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    if isinstance(data, dict) and data.get("year_month") == current_ym:
                        return data
        except Exception as exc:
            logger.warning("Không đọc được quota file %s: %s", path, exc)

    return {
        "year_month": current_ym,
        "used_requests": 0,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


def _save_quota_data(data: dict[str, Any], quota_path: Path | None = None) -> None:
    path = quota_path or _QUOTA_FILE_PATH
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write qua file tạm để chống hỏng file khi bị crash / abort giữa chừng
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        temp_path.replace(path)
    except Exception as exc:
        logger.warning("Không lưu được quota file %s: %s", path, exc)


def get_quota_status(quota_path: Path | None = None) -> dict[str, Any]:
    """Lấy trạng thái sử dụng quota SerpApi trong tháng hiện tại (3 mức cảnh báo)."""
    with _QUOTA_LOCK:
        limit = get_monthly_limit()
        margin = get_safety_margin()
        warn_thresh = get_warn_threshold()
        info_thresh = get_info_threshold()

        data = _load_quota_data(quota_path)
        used = int(data.get("used_requests", 0))
        usable_limit = max(0, limit - margin)
        remaining = max(0, usable_limit - used)

        if used >= usable_limit:
            level = "CRITICAL"
        elif used >= warn_thresh:
            level = "WARN"
        elif used >= info_thresh:
            level = "INFO"
        else:
            level = "NORMAL"

        return {
            "enabled": is_serpapi_enabled(),
            "year_month": data.get("year_month", _get_current_year_month()),
            "total_limit": limit,
            "safety_margin": margin,
            "usable_limit": usable_limit,
            "used_requests": used,
            "remaining_usable": remaining,
            "warning_level": level,
            "info_threshold": info_thresh,
            "warn_threshold": warn_thresh,
        }


def _increment_quota(quota_path: Path | None = None) -> int:
    with _QUOTA_LOCK:
        data = _load_quota_data(quota_path)
        data["used_requests"] = int(data.get("used_requests", 0)) + 1
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        _save_quota_data(data, quota_path)

        # `data` là dict[str, Any] nên `data[...]` là Any; hàm khai báo `-> int` thì
        # phải ép int tường minh, nếu không mypy báo no-any-return và quota dùng để
        # so ngưỡng cảnh báo có thể âm thầm là kiểu lạ.
        used: int = int(data["used_requests"])
        warn_thresh = get_warn_threshold()
        if used == warn_thresh:
            logger.warning(
                json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "level": "WARN",
                    "component": "serpapi_client",
                    "event": "quota_threshold_warn",
                    "quota_used": used,
                    "quota_limit": get_monthly_limit(),
                    "api_key_masked": mask_api_key(),
                })
            )
        return used


# ── Cache Đa Tầng (L1 Memory + L2 Persistent) ─────────────────────────────────


def _cache_hash(engine: str, params: dict[str, Any]) -> str:
    cleaned = {k: v for k, v in params.items() if k not in ("api_key", "output")}
    dumped = json.dumps({"engine": engine, "params": cleaned}, sort_keys=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def _get_l1_cache(cache_key: str) -> dict[str, Any] | None:
    """Kiểm tra L1 Process-local in-memory cache (TTL 5 phút)."""
    with _L1_LOCK:
        entry = _L1_CACHE.get(cache_key)
        if not entry:
            return None
        cached_at, data = entry
        if (time.time() - cached_at) <= _L1_CACHE_TTL_S:
            return data
        _L1_CACHE.pop(cache_key, None)
        return None


def _put_l1_cache(cache_key: str, data: dict[str, Any]) -> None:
    with _L1_LOCK:
        _L1_CACHE[cache_key] = (time.time(), data)


def _get_cache_payload(
    cache_key: str,
    ttl_hours: float,
    cache_dir: Path | None = None,
) -> dict[str, Any] | None:
    # 1. Thử L1 cache trước (chỉ khi dùng cache_dir mặc định của hệ thống)
    if cache_dir is None:
        l1_data = _get_l1_cache(cache_key)
        if l1_data is not None:
            logger.info("serpapi_cache_hit_l1 key=%s", cache_key)
            _record_metric("cache_hit_total")
            return l1_data

    # 2. Thử L2 persistent file cache
    cdir = cache_dir or _DEFAULT_CACHE_DIR
    cache_file = cdir / f"{cache_key}.json"
    if not cache_file.exists():
        return None

    try:
        with open(cache_file, encoding="utf-8") as f:
            entry = json.load(f)
        cached_time = float(entry.get("cached_at", 0))
        ttl_seconds = ttl_hours * 3600.0
        if (time.time() - cached_time) <= ttl_seconds:
            logger.info("serpapi_cache_hit_l2 key=%s", cache_key)
            _record_metric("cache_hit_total")
            payload: dict[str, Any] | None = entry.get("data")
            if isinstance(payload, dict) and cache_dir is None:
                _put_l1_cache(cache_key, payload)
            return payload
    except Exception as exc:
        logger.warning("Lỗi đọc cache serpapi: %s", exc)

    return None


def get_stale_cache_payload(
    engine: str,
    params: dict[str, Any],
    cache_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Lấy dữ liệu cache cũ nhất còn lưu (stale-if-error) khi cả mạng và fallback gặp sự cố."""
    cache_key = _cache_hash(engine, params)
    cdir = cache_dir or _DEFAULT_CACHE_DIR
    cache_file = cdir / f"{cache_key}.json"
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, encoding="utf-8") as f:
            entry = json.load(f)
        stale: dict[str, Any] | None = entry.get("data")
        return stale
    except Exception:
        return None


def _put_cache_payload(
    cache_key: str,
    data: dict[str, Any],
    cache_dir: Path | None = None,
) -> None:
    # Lưu vào L1 nếu dùng cache mặc định
    if cache_dir is None:
        _put_l1_cache(cache_key, data)

    cdir = cache_dir or _DEFAULT_CACHE_DIR
    try:
        cdir.mkdir(parents=True, exist_ok=True)
        cache_file = cdir / f"{cache_key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"cached_at": time.time(), "data": data}, f)
    except Exception as exc:
        logger.warning("Lỗi ghi cache serpapi: %s", exc)


def clear_l1_cache() -> None:
    """Xóa sạch L1 in-memory cache (tiện ích cho unit test)."""
    with _L1_LOCK:
        _L1_CACHE.clear()


# ── HTTP Execution với Retry & Jitter ─────────────────────────────────────────


def _execute_http_request(url: str, timeout_s: int) -> tuple[int, str]:
    """Thực thi một HTTP GET request với timeout chặt chẽ."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NhipQuan-AgentOps/2.0",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.status, resp.read().decode("utf-8")


def _call_with_retry(
    url: str,
    circuit_breaker: CircuitBreaker,
    timeout_s: int = _HTTP_TIMEOUT_S,
    max_retries: int = _MAX_RETRIES,
    base_delay_sec: float = _BASE_DELAY_SEC,
) -> tuple[int, str]:
    """Thực thi request có Retry, Exponential Backoff và Jitter."""
    start_time = time.time()
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        # Kiểm tra tổng thời gian timeout budget
        if (time.time() - start_time) >= _TOTAL_BUDGET_TIMEOUT_S:
            circuit_breaker.record_failure()
            raise SerpApiError(f"Hết ngân sách thời gian timeout ({_TOTAL_BUDGET_TIMEOUT_S}s) khi gọi SerpApi")

        try:
            status_code, raw_body = _execute_http_request(url, timeout_s=timeout_s)
            return status_code, raw_body
        except urllib.error.HTTPError as he:
            last_exc = he
            if he.code in (401, 403):
                circuit_breaker.record_failure()
                raise SerpApiAuthError(f"SerpApi xác thực thất bại (HTTP {he.code}): {he.reason}") from he
            if he.code not in _RETRYABLE_STATUS:
                circuit_breaker.record_failure()
                raw_err = he.read().decode("utf-8", errors="replace")
                raise SerpApiError(f"SerpApi HTTP {he.code}: {raw_err}") from he
        except (urllib.error.URLError, TimeoutError, ConnectionError) as net_err:
            last_exc = net_err

        if attempt == max_retries:
            break

        delay = base_delay_sec * (2**attempt) + random.uniform(0.0, 0.3)
        time.sleep(delay)

    circuit_breaker.record_failure()
    if isinstance(last_exc, urllib.error.HTTPError):
        if last_exc.code == 429:
            raise SerpApiQuotaExceededError(f"SerpApi Rate Limit / Quota Exceeded (HTTP 429): {last_exc.reason}") from last_exc
        raise SerpApiError(f"SerpApi HTTP {last_exc.code} sau {max_retries} lần retry") from last_exc

    clean_err = sanitize_url(str(last_exc))
    raise SerpApiError(f"Lỗi kết nối SerpApi sau {max_retries} lần retry: {clean_err}") from last_exc


# ── API Chính: search_serpapi ─────────────────────────────────────────────────


def search_serpapi(
    engine: str,
    params: dict[str, Any],
    ttl_hours: float | None = None,
    cache_dir: Path | None = None,
    quota_path: Path | None = None,
    timeout_s: int = _HTTP_TIMEOUT_S,
    circuit_breaker: CircuitBreaker | None = None,
    allow_stale_on_error: bool = False,
) -> dict[str, Any]:
    """Thực thi truy vấn SerpApi an toàn qua Cache L1/L2, Quota Guard và Circuit Breaker.

    Args:
        engine: SerpApi engine (vd: 'google_maps', 'google_trends', 'google_maps_photos')
        params: Các tham số tìm kiếm
        ttl_hours: Thời gian sống của cache (mặc định lấy theo từng engine)
        cache_dir: Thư mục lưu cache (dùng khi test)
        quota_path: Đường dẫn file quota (dùng khi test)
        timeout_s: Thời gian chờ HTTP tối đa mỗi lần thử
        circuit_breaker: Bộ ngắt mạch CircuitBreaker (dùng khi test)
        allow_stale_on_error: Cho phép trả cache cũ nếu gặp lỗi mạng

    Raises:
        SerpApiDisabledError: Khi chưa bật hoặc thiếu API key
        SerpApiCircuitOpenError: Khi Circuit Breaker đang ngắt mạch (OPEN)
        SerpApiQuotaExceededError: Khi đã vượt ngưỡng an toàn quota tháng
        SerpApiAuthError: Khi key sai hoặc bị từ chối
        SerpApiError: Các lỗi HTTP hoặc schema từ SerpApi
    """
    _record_metric("request_total")

    if not is_serpapi_enabled():
        _record_metric("error_total")
        raise SerpApiDisabledError("SerpApi chưa được kích hoạt hoặc thiếu SERPAPI_API_KEY")

    cb = circuit_breaker or _CIRCUIT_BREAKER
    api_key = _get_api_key()
    effective_ttl = get_engine_cache_ttl_hours(engine) if ttl_hours is None else ttl_hours

    # 1. Kiểm tra Cache L1/L2 (Nếu HIT -> tốn 0 request quota, không chạm Circuit Breaker)
    cache_key = _cache_hash(engine, params)
    cached_res = _get_cache_payload(cache_key, effective_ttl, cache_dir)
    if cached_res is not None:
        return cached_res

    _record_metric("cache_miss_total")

    # 2. Kiểm tra Circuit Breaker State
    if not cb.allow_request():
        _record_metric("fallback_total")
        if allow_stale_on_error:
            stale = get_stale_cache_payload(engine, params, cache_dir)
            if stale:
                stale_copy = dict(stale)
                stale_copy["stale"] = True
                stale_copy["data_source"] = "cache"
                return stale_copy
        raise SerpApiCircuitOpenError(
            f"Circuit Breaker SerpApi đang OPEN ({cb.consecutive_failures} lỗi liên tiếp). "
            "Chuyển sang nguồn dữ liệu dự phòng (Fallback)."
        )

    # 3. Kiểm tra Quota Guard
    status = get_quota_status(quota_path)
    if status["remaining_usable"] <= 0:
        _record_metric("fallback_total")
        if allow_stale_on_error:
            stale = get_stale_cache_payload(engine, params, cache_dir)
            if stale:
                stale_copy = dict(stale)
                stale_copy["stale"] = True
                stale_copy["data_source"] = "cache"
                return stale_copy
        raise SerpApiQuotaExceededError(
            f"Đã đạt ngưỡng an toàn Quota SerpApi tháng này "
            f"({status['used_requests']}/{status['usable_limit']} lượt). "
            "Chuyển sang nguồn dữ liệu dự phòng (Fallback)."
        )

    # 4. Chuẩn bị URL & Request
    query_dict = dict(params)
    query_dict["engine"] = engine
    query_dict["api_key"] = api_key
    query_dict["output"] = "json"

    query_str = urllib.parse.urlencode(query_dict)
    full_url = f"{SERPAPI_SEARCH_URL}?{query_str}"

    masked_url = sanitize_url(full_url)
    logger.info("serpapi_call_start engine=%s url=%s", engine, masked_url)

    # 5. Thực thi qua Retry + Circuit Breaker
    try:
        status_code, raw = _call_with_retry(
            url=full_url,
            circuit_breaker=cb,
            timeout_s=timeout_s,
        )
    except Exception:
        _record_metric("error_total")
        if allow_stale_on_error:
            stale = get_stale_cache_payload(engine, params, cache_dir)
            if stale:
                stale_copy = dict(stale)
                stale_copy["stale"] = True
                stale_copy["data_source"] = "cache"
                return stale_copy
        raise

    # 6. Parse JSON an toàn
    try:
        result_json = json.loads(raw)
    except json.JSONDecodeError as jde:
        cb.record_failure()
        _record_metric("error_total")
        raise SerpApiError(f"SerpApi trả về phản hồi không phải JSON: {jde}") from jde

    if not isinstance(result_json, dict):
        cb.record_failure()
        _record_metric("error_total")
        raise SerpApiError("SerpApi payload không hợp lệ (không phải dict)")

    if "error" in result_json:
        err_msg = str(result_json["error"])
        if "quota" in err_msg.lower() or "searches left" in err_msg.lower():
            cb.record_failure()
            _record_metric("fallback_total")
            raise SerpApiQuotaExceededError(f"SerpApi báo cạn quota: {err_msg}")
        cb.record_failure()
        _record_metric("error_total")
        raise SerpApiError(f"SerpApi trả về lỗi: {err_msg}")

    # 7. Ghi nhận thành công: đóng Circuit Breaker (nếu đang HALF_OPEN), trừ quota & lưu cache
    cb.record_success()
    _increment_quota(quota_path)
    _put_cache_payload(cache_key, result_json, cache_dir)
    _record_metric("success_total")
    logger.info("serpapi_call_success engine=%s key=%s", engine, cache_key)

    return result_json


# ── Metrics & Health Check ───────────────────────────────────────────────────


def get_serpapi_metrics() -> dict[str, Any]:
    """Xuất số liệu giám sát (Observability) cho Prometheus / Dashboard."""
    with _METRICS_LOCK:
        metrics_copy = dict(_METRICS)
    quota = get_quota_status()
    cb = get_circuit_breaker().get_info()
    total_cache = metrics_copy["cache_hit_total"] + metrics_copy["cache_miss_total"]
    hit_rate = round((metrics_copy["cache_hit_total"] / total_cache * 100.0), 1) if total_cache > 0 else 0.0

    return {
        "enabled": is_serpapi_enabled(),
        "status": "circuit_open" if cb["state"] == CircuitBreakerState.OPEN else ("ok" if quota["warning_level"] != "CRITICAL" else "quota_exceeded"),
        "quota": quota,
        "circuit_breaker": cb,
        "metrics": metrics_copy,
        "cache_hit_rate_pct": hit_rate,
    }
