"""Thin wrapper around Apify REST API v2.

Sync (blocking) version. Token lấy từ env `APIFY_TOKEN`.

Public API:
    ApifyError                    -- raise khi actor fail / timeout / quota / token sai.
    run_actor_sync(actor_id, payload, timeout_s) -> list[dict]
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
_HTTP_TIMEOUT_START_S = 10
_HTTP_TIMEOUT_POLL_S = 5
_HTTP_TIMEOUT_DATASET_S = 10


class ApifyError(Exception):
    """Raised khi Apify actor chạy fail / timeout / quota hết / token sai."""


def _get_token() -> str:
    token = os.getenv("APIFY_TOKEN", "").strip()
    if not token:
        raise ApifyError("APIFY_TOKEN chưa cấu hình trong env")
    return token


def _http_json(url: str, body: dict | None = None, timeout: int = 10) -> Any:
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

    Raises:
        ApifyError: token missing, start fail, status FAIL/ABORT/TIMEOUT,
                    poll timeout, dataset rỗng.

    Returns:
        list[dict]: dataset items (rỗng thì raise, không trả []).
    """
    token = _get_token()
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
    while True:
        if time.monotonic() >= deadline:
            raise ApifyError(f"Apify run {run_id} timeout sau {timeout_s}s")
        try:
            poll = _http_json(status_url, timeout=_HTTP_TIMEOUT_POLL_S)
        except Exception as e:  # noqa: BLE001
            raise ApifyError(f"Lỗi poll status: {type(e).__name__}: {e}") from e
        if not poll or "data" not in poll:
            raise ApifyError(f"Apify poll response lỗi: {poll!r}")
        run = poll["data"]
        status = run.get("status")
        if status == "SUCCEEDED":
            dataset_id = run.get("defaultDatasetId")
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise ApifyError(f"Apify run {run_id} status={status}")
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


def get_apify_usage() -> dict[str, Any]:
    """Fetch current Apify quota, monthly spend & usage status."""
    token = os.getenv("APIFY_TOKEN", "").strip()
    tiktok_actor = os.getenv("APIFY_TIKTOK_ACTOR_ID", "clockworks/tiktok-scraper")
    threads_actor = os.getenv("APIFY_THREADS_ACTOR_ID", "curious_coder/threads-scraper")

    if not token:
        return {
            "has_token": False,
            "username": "N/A",
            "plan": "Chưa cấu hình APIFY_TOKEN",
            "monthly_limit_usd": 5.0,
            "usage_usd": 0.0,
            "remaining_usd": 5.0,
            "usage_percent": 0.0,
            "status_label": "Chưa cấu hình Token (Đang chạy 100% Miễn Phí)",
            "active_actors": [tiktok_actor, threads_actor],
        }

    try:
        user_url = f"{APIFY_BASE}/users/me?token={token}"
        user_data = _http_json(user_url, timeout=5)
        if user_data and "data" in user_data:
            d = user_data["data"]
            plan_obj = d.get("plan", {})
            plan_name = plan_obj.get("name") or "Free Tier ($5.00/tháng)"
            limit_usd = float(plan_obj.get("maxMonthlyUsageUsd", 5.0))
            usage_usd = float(d.get("currentMonthlyUsageUsd", 0.0))
            remaining_usd = max(0.0, limit_usd - usage_usd)
            pct = round((usage_usd / limit_usd * 100), 1) if limit_usd > 0 else 0.0

            status_label = (
                "Hoạt động bình thường"
                if pct < 80
                else ("Sắp hết hạn mức" if pct < 100 else "Đã vượt hạn mức")
            )
            return {
                "has_token": True,
                "username": d.get("username", "user"),
                "plan": plan_name,
                "monthly_limit_usd": limit_usd,
                "usage_usd": round(usage_usd, 3),
                "remaining_usd": round(remaining_usd, 3),
                "usage_percent": pct,
                "status_label": status_label,
                "active_actors": [tiktok_actor, threads_actor],
            }
    except Exception as e:
        logger.warning("Lỗi fetch Apify usage: %s", e)

    return {
        "has_token": True,
        "username": "Apify User",
        "plan": "Free Tier ($5.00/tháng)",
        "monthly_limit_usd": 5.0,
        "usage_usd": 0.0,
        "remaining_usd": 5.0,
        "usage_percent": 0.0,
        "status_label": "Đang kết nối (Chế độ dự phòng)",
        "active_actors": [tiktok_actor, threads_actor],
    }

