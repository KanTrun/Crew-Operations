"""Thin wrapper around Apify REST API v2.

Sync (blocking) version. Token lấy từ env `APIFY_TOKEN`.

Public API:
    ApifyError                              -- raise khi actor fail / timeout / quota / token sai.
    run_actor_sync(actor_id, payload, timeout_s) -> list[dict]
    get_apify_usage(refresh=False)          -> dict   -- hạn mức + mức dùng thật (fail-closed).
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

APIFY_BASE = "https://api.apify.com/v2"
_DEFAULT_TIMEOUT_S = int(os.getenv("TIKTOK_APIFY_TIMEOUT_S", "90"))
_POLL_INTERVAL_S = 2.0
# Poll lỗi mạng đơn lẻ KHÔNG có nghĩa actor run đã chết → retry vài lần trước
# khi bỏ (xem `run_actor_sync`). 3 lần × 2s = 6s chịu lỗi tạm thời.
_MAX_POLL_ERRORS = 3
_HTTP_TIMEOUT_START_S = 10
_HTTP_TIMEOUT_POLL_S = 5
_HTTP_TIMEOUT_DATASET_S = 10
_HTTP_TIMEOUT_USAGE_S = 8

# Cache kết quả hạn mức — trang `/page-quan` gọi mỗi lần load/đổi tab, không
# nên đập vào Apify mỗi lượt (rate limit + chậm). "Kiểm tra số dư" của người
# dùng đi qua `refresh=True` để bỏ cache.
_USAGE_CACHE_TTL_S = float(os.getenv("APIFY_USAGE_CACHE_TTL_S", "120") or 120)
_usage_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _cache_key() -> str:
    """Khoá cache theo token — đổi token phải đọc lại, không dùng số của chủ cũ."""
    return os.getenv("APIFY_TOKEN", "").strip()


class ApifyError(Exception):
    """Raised khi Apify actor chạy fail / timeout / quota hết / token sai."""


def _get_token() -> str:
    token = os.getenv("APIFY_TOKEN", "").strip()
    if not token:
        raise ApifyError("APIFY_TOKEN chưa cấu hình trong env")
    return token


def _http_json(url: str, body: dict[str, Any] | None = None, timeout: int = 10) -> Any:
    """HTTP wrapper trả về parsed JSON."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    if not raw:
        return None
    return json.loads(raw)


def run_actor_sync(
    actor_id: str,
    payload: dict[str, Any],
    timeout_s: int = _DEFAULT_TIMEOUT_S,
) -> list[dict[str, Any]]:
    """
    Start actor run → poll đến khi SUCCEEDED → trả dataset items.

    Dừng sớm khi đã biết hạn mức tháng đã cạn (cache ``get_apify_usage``): actor
    run sẽ bị Apify từ chối ở bước start, tốn 1 vòng HTTP vô ích và làm chậm
    cả chuỗi cào. Raise ``ApifyError`` để caller rớt xuống tầng miễn phí ngay.

    Raises:
        ApifyError: token missing, hạn mức đã cạn, start fail,
                    status FAIL/ABORT/TIMEOUT, poll timeout, dataset rỗng.

    Returns:
        list[dict]: dataset items (rỗng thì raise, không trả []).
    """
    token = _get_token()

    cached = _read_usage_cache()
    if cached is not None and cached.get("quota_exhausted"):
        raise ApifyError(
            "Apify đã cạn hạn mức tháng — chuyển sang nguồn miễn phí. "
            f"{cached.get('note', '')}".strip()
        )

    encoded_actor = urllib.parse.quote(actor_id, safe="~")
    start_url = f"{APIFY_BASE}/acts/{encoded_actor}/runs?token={token}"

    # 1. Start run
    try:
        started = _http_json(start_url, body=payload, timeout=_HTTP_TIMEOUT_START_S)
    except Exception as e:  # noqa: BLE001
        raise ApifyError(f"Không start được actor: {type(e).__name__}: {e}") from e
    if not started or "data" not in started:
        raise ApifyError(f"Apify response không hợp lệ: {started!r}")
    run_id = started["data"]["id"]
    logger.info("apify_run_started run_id=%s actor=%s", run_id, actor_id)

    # 2. Poll status
    status_url = f"{APIFY_BASE}/actor-runs/{run_id}?token={token}"
    deadline = time.monotonic() + timeout_s
    dataset_id: str | None = None
    poll_errors = 0
    while True:
        if time.monotonic() >= deadline:
            raise ApifyError(f"Apify run {run_id} timeout sau {timeout_s}s")
        try:
            poll = _http_json(status_url, timeout=_HTTP_TIMEOUT_POLL_S)
        except Exception as e:  # noqa: BLE001
            # Poll là read-only, lỗi mạng/timeout đơn lẻ KHÔNG có nghĩa run đã
            # chết (actor vẫn tiếp tục chạy phía Apify). Bỏ luôn cả actor run vì
            # 1 lần timeout 5s làm mất data thật + vẫn bị tính CU — retry tối đa
            # 3 lần liên tiếp rồi mới bỏ (đo live 2026-09-24: run SUCCEEDED sau
            # 3 phút, nhưng lần poll đầu bị `TimeoutError: read operation timed out`).
            poll_errors += 1
            if poll_errors >= _MAX_POLL_ERRORS:
                raise ApifyError(
                    f"Lỗi poll status {poll_errors} lần liên tiếp: {type(e).__name__}: {e}"
                ) from e
            logger.warning(
                "apify_poll_retry run_id=%s attempt=%d error=%s",
                run_id,
                poll_errors,
                type(e).__name__,
            )
            time.sleep(_POLL_INTERVAL_S)
            continue
        if not poll or "data" not in poll:
            raise ApifyError(f"Apify poll response lỗi: {poll!r}")
        poll_errors = 0  # poll thành công → reset chuỗi lỗi liên tiếp
        run = poll["data"]
        status = run.get("status")
        if status == "SUCCEEDED":
            dataset_id = run.get("defaultDatasetId")
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise ApifyError(
                f"Apify run {run_id} status={status}"
                + (f" ({run.get('statusMessage')})" if run.get("statusMessage") else "")
            )
        time.sleep(_POLL_INTERVAL_S)

    if not dataset_id:
        raise ApifyError(f"Apify run {run_id} SUCCEEDED nhưng không có defaultDatasetId")

    # 3. Fetch dataset items
    items_url = f"{APIFY_BASE}/datasets/{dataset_id}/items?token={token}"
    try:
        items = _http_json(items_url, timeout=_HTTP_TIMEOUT_DATASET_S) or []
    except Exception as e:  # noqa: BLE001
        raise ApifyError(f"Lỗi fetch dataset items: {e}") from e
    if not items:
        raise ApifyError(f"Apify dataset {dataset_id} rỗng")
    logger.info("apify_run_done run_id=%s items=%d", run_id, len(items))
    return items


def _read_usage_cache() -> dict[str, Any] | None:
    """Trả bản ghi cache còn hạn (kèm cờ ``cached``), hoặc ``None`` nếu hết hạn."""
    key = _cache_key()
    hit = _usage_cache.get(key)
    if not hit:
        return None
    ts, payload = hit
    if time.monotonic() - ts > _USAGE_CACHE_TTL_S:
        _usage_cache.pop(key, None)
        return None
    return {**payload, "cached": True}


def _write_usage_cache(payload: dict[str, Any]) -> dict[str, Any]:
    """Ghi cache kết quả rồi trả lại chính nó.

    Chỉ cache khi **đo được** số thật, hoặc khi chưa cấu hình token (trạng thái
    tĩnh, khỏi dựng lại dict mỗi lượt). Lỗi mạng là tạm thời — cache lại thì
    người dùng phải chờ hết TTL mới thấy số đúng.
    """
    if payload.get("usage_measured") or not payload.get("has_token"):
        _usage_cache[_cache_key()] = (time.monotonic(), payload)
    return payload


def _plan_label(plan_id: str | None) -> str:
    """Tên gói đọc từ Apify.

    Chỉ trả **tên**; tiền hạn mức nằm ở ``monthly_limit_usd`` để không có hai
    nguồn số tiền có thể lệch nhau.
    """
    known = {
        "FREE": "Apify Free",
        "STARTER": "Apify Starter",
        "SCALE": "Apify Scale",
        "BUSINESS": "Apify Business",
        "ENTERPRISE": "Apify Enterprise",
    }
    if not plan_id:
        return "Không rõ gói"
    return known.get(plan_id.upper(), f"Gói {plan_id}")


def get_apify_usage(refresh: bool = False) -> dict[str, Any]:
    """Đọc hạn mức & mức dùng thật của tài khoản Apify (fail-closed).

    Nguồn dữ liệu — Apify API v2 chính thức:
        - ``GET /users/me``        → ``username``, ``plan.id``
        - ``GET /users/me/limits`` → hạn mức + mức dùng của chu kỳ tháng hiện tại

    Fail-closed (ADR-008): **không bao giờ bịa số**. Khi không đọc được mức dùng
    thật, ``usage_measured=False`` và ``usage_usd`` / ``remaining_usd`` /
    ``usage_percent`` trả ``None`` kèm ``note`` cảnh báo — lớp hiển thị phải tôn
    trọng cờ này thay vì in ra số 0 giả.

    Args:
        refresh: bỏ qua cache và đọc lại từ Apify (nút "Kiểm tra số dư").
            Mặc định dùng cache ``APIFY_USAGE_CACHE_TTL_S`` giây.
    """
    token = os.getenv("APIFY_TOKEN", "").strip()
    tiktok_actor = os.getenv("APIFY_TIKTOK_ACTOR_ID", "clockworks/tiktok-scraper")
    threads_actor = os.getenv("APIFY_THREADS_ACTOR_ID", "curious_coder/threads-scraper")

    if not refresh:
        cached = _read_usage_cache()
        if cached is not None:
            return cached

    if not token:
        no_token: dict[str, Any] = {
            "has_token": False,
            "username": "N/A",
            "plan": "Chưa cấu hình APIFY_TOKEN",
            "plan_id": None,
            "monthly_limit_usd": None,
            "usage_usd": None,
            "remaining_usd": None,
            "usage_percent": None,
            "status_label": "Chưa cấu hình Token — đang chạy 100% miễn phí",
            "usage_measured": False,
            "usage_source": "none",
            "usage_cycle_end_at": None,
            "cu_limit": None,
            "cu_used": None,
            "active_actors": [tiktok_actor, threads_actor],
            "note": "Chưa cấu hình APIFY_TOKEN — không có số liệu Apify để hiển thị.",
            "cached": False,
            "quota_exhausted": False,
        }
        return _write_usage_cache(no_token)

    username = "Apify User"
    plan_id: str | None = None
    limit_usd: float | None = None
    username_error: str | None = None

    # 1. Hồ sơ: username + plan.id (nhãn gói). KHÔNG hardcode giá ở đây.
    try:
        user_data = _http_json(f"{APIFY_BASE}/users/me?token={token}", timeout=5)
    except Exception as e:  # noqa: BLE001
        logger.warning("Lỗi fetch Apify user: %s", e)
        user_data = None
        username_error = f"{type(e).__name__}: {e}"

    if isinstance(user_data, dict):
        d = user_data.get("data")
        if isinstance(d, dict):
            username = str(d.get("username") or "Apify User")
            plan_obj = d.get("plan")
            if isinstance(plan_obj, dict):
                raw_id = plan_obj.get("id") or plan_obj.get("tier")
                plan_id = str(raw_id) if raw_id else None
                # Fallback hạn mức khi /users/me/limits không đọc được.
                raw_limit = plan_obj.get("maxMonthlyUsageUsd")
                if isinstance(raw_limit, (int, float)):
                    limit_usd = float(raw_limit)

    # 2. Hạn mức + mức dùng thật của chu kỳ hiện tại.
    usage_usd: float | None = None
    cu_limit: int | None = None
    cu_used: int | None = None
    cycle_end_at: str | None = None
    limits_error: str | None = None

    try:
        limits_data = _http_json(
            f"{APIFY_BASE}/users/me/limits?token={token}", timeout=_HTTP_TIMEOUT_USAGE_S
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Lỗi fetch Apify limits: %s", e)
        limits_data = None
        limits_error = f"{type(e).__name__}: {e}"

    if isinstance(limits_data, dict):
        ld = limits_data.get("data")
        if isinstance(ld, dict):
            limits_obj = ld.get("limits")
            if isinstance(limits_obj, dict):
                raw_limit = limits_obj.get("maxMonthlyUsageUsd")
                if isinstance(raw_limit, (int, float)):
                    limit_usd = float(raw_limit)
                raw_cu_limit = limits_obj.get("maxMonthlyActorComputeUnits")
                if isinstance(raw_cu_limit, (int, float)):
                    cu_limit = int(raw_cu_limit)
            current_obj = ld.get("current")
            if isinstance(current_obj, dict):
                raw_usage = current_obj.get("monthlyUsageUsd")
                if isinstance(raw_usage, (int, float)):
                    usage_usd = float(raw_usage)
                raw_cu_used = current_obj.get("monthlyActorComputeUnits")
                if isinstance(raw_cu_used, (int, float)):
                    cu_used = int(raw_cu_used)
            cycle_obj = ld.get("monthlyUsageCycle")
            if isinstance(cycle_obj, dict):
                raw_end = cycle_obj.get("endAt")
                cycle_end_at = str(raw_end) if raw_end else None

    # 3. Tính toán — chỉ khi đã có số thật.
    usage_measured = usage_usd is not None
    remaining_usd: float | None = None
    pct: float | None = None
    if usage_usd is not None and limit_usd is not None and limit_usd > 0:
        remaining_usd = max(0.0, limit_usd - usage_usd)
        pct = round(usage_usd / limit_usd * 100, 1)

    if not usage_measured:
        status_label = "Không đọc được số liệu sử dụng"
    elif pct is None:
        status_label = "Có token — chưa rõ hạn mức"
    elif pct < 80:
        status_label = "Hoạt động bình thường"
    elif pct < 100:
        status_label = "Sắp hết hạn mức"
    else:
        status_label = "Đã vượt hạn mức"

    # Cạn hạn mức ⇒ caller (chuỗi cào) phải dừng gọi Apify, không để actor
    # fail giữa lượt cào rồi mất luôn dữ liệu.
    quota_exhausted = usage_measured and pct is not None and pct >= 100

    note_parts: list[str] = []
    if not usage_measured:
        detail = limits_error or username_error or "API không trả dữ liệu"
        note_parts.append(
            f"Không đọc được mức sử dụng thật từ Apify ({detail}) — "
            "xem số chính xác tại console.apify.com/billing/historical-usage"
        )
    if quota_exhausted:
        note_parts.append(
            "Đã chạm trần hạn mức tháng — Apify sẽ từ chối actor run mới cho tới khi "
            "sang chu kỳ kế tiếp; chuyển sang phương thức cào miễn phí."
        )
    if cu_limit is not None and cu_used is not None:
        note_parts.append(f"Compute Units: {cu_used}/{cu_limit} CU trong chu kỳ")
    if quota_exhausted and cycle_end_at:
        note_parts.append(f"Chu kỳ reset lúc {cycle_end_at}")

    result: dict[str, Any] = {
        "has_token": True,
        "username": username,
        "plan": _plan_label(plan_id),
        "plan_id": plan_id,
        "monthly_limit_usd": limit_usd,
        "usage_usd": round(usage_usd, 4) if usage_usd is not None else None,
        "remaining_usd": round(remaining_usd, 4) if remaining_usd is not None else None,
        "usage_percent": pct,
        "status_label": status_label,
        "usage_measured": usage_measured,
        "usage_source": "users/me/limits" if usage_measured else "unavailable",
        "usage_cycle_end_at": cycle_end_at,
        "cu_limit": cu_limit,
        "cu_used": cu_used,
        "active_actors": [tiktok_actor, threads_actor],
        "note": " · ".join(note_parts),
        "cached": False,
        "quota_exhausted": quota_exhausted,
    }
    return _write_usage_cache(result)
