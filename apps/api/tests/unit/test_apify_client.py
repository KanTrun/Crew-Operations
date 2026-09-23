# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore,arg-type"
"""Unit tests cho apify_client.py — mock toàn bộ HTTP."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from ca_agents.clients import apify_client
from ca_agents.clients.apify_client import ApifyError, get_apify_usage, run_actor_sync

# ─── Helpers ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_usage_cache():
    """Cache hạn mức là state cấp module — xoá trước mỗi test để test độc lập."""
    apify_client._usage_cache.clear()
    yield
    apify_client._usage_cache.clear()


def _mock_response(body: bytes | None = None) -> MagicMock:
    """Tạo mock context-manager cho urlopen."""
    m = MagicMock()
    m.__enter__ = lambda s: s
    m.__exit__ = lambda s, *a: None
    m.read = lambda: body if body is not None else b""
    return m


def _patch_urlopen(monkeypatch, responses: list[bytes | Exception]):
    """Patch urllib.request.urlopen với list responses tuần tự."""
    iterator = iter(responses)

    def fake(req, **kwargs):
        nxt = next(iterator)
        if isinstance(nxt, Exception):
            raise nxt
        return _mock_response(nxt)

    monkeypatch.setattr("ca_agents.clients.apify_client.urllib.request.urlopen", fake)


# ─── Tests ──────────────────────────────────────────────────────────


def test_missing_token_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    with pytest.raises(ApifyError, match="APIFY_TOKEN chưa cấu hình"):
        run_actor_sync("clockworks/test", {"x": 1})


def test_start_fail_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    _patch_urlopen(monkeypatch, [ConnectionError("boom")])
    with pytest.raises(ApifyError, match="Không start được actor"):
        run_actor_sync("clockworks/test", {"x": 1})


def test_run_succeeded_returns_items(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    items = [{"id": "v1", "text": "a"}, {"id": "v2", "text": "b"}]
    responses = [
        json.dumps({"data": {"id": "run_123"}}).encode(),  # start
        json.dumps({"data": {"status": "SUCCEEDED", "defaultDatasetId": "ds1"}}).encode(),
        json.dumps(items).encode(),  # dataset
    ]
    _patch_urlopen(monkeypatch, responses)
    result = run_actor_sync("clockworks/test", {"x": 1}, timeout_s=10)
    assert result == items


def test_run_failed_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    responses = [
        json.dumps({"data": {"id": "r1"}}).encode(),
        json.dumps({"data": {"status": "FAILED"}}).encode(),
    ]
    _patch_urlopen(monkeypatch, responses)
    with pytest.raises(ApifyError, match="status=FAILED"):
        run_actor_sync("clockworks/test", {"x": 1}, timeout_s=10)


def test_run_aborted_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    responses = [
        json.dumps({"data": {"id": "r1"}}).encode(),
        json.dumps({"data": {"status": "ABORTED"}}).encode(),
    ]
    _patch_urlopen(monkeypatch, responses)
    with pytest.raises(ApifyError, match="status=ABORTED"):
        run_actor_sync("clockworks/test", {"x": 1}, timeout_s=10)


def test_empty_dataset_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    responses = [
        json.dumps({"data": {"id": "r1"}}).encode(),
        json.dumps({"data": {"status": "SUCCEEDED", "defaultDatasetId": "ds1"}}).encode(),
        json.dumps([]).encode(),
    ]
    _patch_urlopen(monkeypatch, responses)
    with pytest.raises(ApifyError, match="rỗng"):
        run_actor_sync("clockworks/test", {"x": 1}, timeout_s=10)


def test_polling_timeout_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    # Start OK, sau đó poll luôn RUNNING nhưng timeout rất nhanh
    responses = [
        json.dumps({"data": {"id": "r1"}}).encode(),
        json.dumps({"data": {"status": "RUNNING"}}).encode(),
    ]
    _patch_urlopen(monkeypatch, responses)
    with pytest.raises(ApifyError, match="timeout"):
        run_actor_sync("clockworks/test", {"x": 1}, timeout_s=0)


def test_polling_eventually_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    items = [{"id": "v1"}]
    responses = [
        json.dumps({"data": {"id": "r1"}}).encode(),
        json.dumps({"data": {"status": "RUNNING"}}).encode(),
        json.dumps({"data": {"status": "RUNNING"}}).encode(),
        json.dumps({"data": {"status": "SUCCEEDED", "defaultDatasetId": "ds1"}}).encode(),
        json.dumps(items).encode(),
    ]
    _patch_urlopen(monkeypatch, responses)
    result = run_actor_sync("clockworks/test", {"x": 1}, timeout_s=10)
    assert result == items


def test_log_does_not_leak_token(caplog) -> None:
    """Đảm bảo token không bao giờ xuất hiện trong log output."""
    import logging

    caplog.set_level(logging.DEBUG)
    token_value = "this_is_a_secret_token_12345"
    with patch(
        "ca_agents.clients.apify_client.urllib.request.urlopen",
        side_effect=ConnectionError("boom"),
    ):
        try:
            with patch.dict("os.environ", {"APIFY_TOKEN": token_value}):
                run_actor_sync("clockworks/test", {"x": 1})
        except ApifyError:
            pass
    # Token không được leak
    for record in caplog.records:
        assert token_value not in record.getMessage()


# ─── get_apify_usage — fail-closed (ADR-008) ────────────────────────


def test_usage_without_token_is_unmeasured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Không có token → KHÔNG bịa số, mọi chỉ số tiền là None."""
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    u = get_apify_usage()
    assert u["has_token"] is False
    assert u["usage_measured"] is False
    assert u["usage_usd"] is None
    assert u["remaining_usd"] is None
    assert u["monthly_limit_usd"] is None
    assert u["usage_percent"] is None
    assert "APIFY_TOKEN" in u["note"]


def test_usage_reads_real_limits_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Đọc số thật từ /users/me/limits — dùng đúng hạn mức $10, không hardcode $5."""
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    responses = [
        json.dumps(
            {"data": {"username": "Sin21", "plan": {"id": "FREE", "maxMonthlyUsageUsd": 10}}}
        ).encode(),
        json.dumps(
            {
                "data": {
                    "monthlyUsageCycle": {
                        "startAt": "2026-08-30T00:00:00.000Z",
                        "endAt": "2026-09-29T23:59:59.999Z",
                    },
                    "limits": {"maxMonthlyUsageUsd": 10, "maxMonthlyActorComputeUnits": 625},
                    "current": {"monthlyUsageUsd": 0.4094, "monthlyActorComputeUnits": 0},
                }
            }
        ).encode(),
    ]
    _patch_urlopen(monkeypatch, responses)
    u = get_apify_usage()
    assert u["username"] == "Sin21"
    assert u["plan_id"] == "FREE"
    assert u["monthly_limit_usd"] == 10.0
    assert u["usage_usd"] == 0.4094
    assert u["remaining_usd"] == 9.5906
    assert u["usage_percent"] == 4.1
    assert u["usage_measured"] is True
    assert u["usage_source"] == "users/me/limits"
    assert u["status_label"] == "Hoạt động bình thường"
    assert "$10.00" not in u["plan"]  # tiền chỉ nằm ở monthly_limit_usd


def test_usage_limits_failure_never_fabricates_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Limits API lỗi → usage_measured=False, KHÔNG trả 0.0 giả (đây là bug gốc)."""
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    responses = [
        json.dumps(
            {"data": {"username": "Sin21", "plan": {"id": "FREE", "maxMonthlyUsageUsd": 10}}}
        ).encode(),
        ConnectionError("limits boom"),
    ]
    _patch_urlopen(monkeypatch, responses)
    u = get_apify_usage()
    assert u["usage_measured"] is False
    assert u["usage_usd"] is None
    assert u["remaining_usd"] is None
    assert u["usage_percent"] is None
    assert u["status_label"] == "Không đọc được số liệu sử dụng"
    assert "console.apify.com" in u["note"]


def test_usage_over_quota_labels_correctly(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vượt hạn mức phải báo đúng, không kẹp remaining âm."""
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    responses = [
        json.dumps(
            {"data": {"username": "Sin21", "plan": {"id": "FREE", "maxMonthlyUsageUsd": 10}}}
        ).encode(),
        json.dumps(
            {
                "data": {
                    "limits": {"maxMonthlyUsageUsd": 10},
                    "current": {"monthlyUsageUsd": 12.5},
                }
            }
        ).encode(),
    ]
    _patch_urlopen(monkeypatch, responses)
    u = get_apify_usage()
    assert u["usage_percent"] == 125.0
    assert u["remaining_usd"] == 0.0
    assert u["status_label"] == "Đã vượt hạn mức"


def test_usage_unknown_plan_still_reports_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """plan.id lạ → vẫn gọi đúng tên gói, tiền hạn mức nằm ở field riêng."""
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    responses = [
        json.dumps(
            {"data": {"username": "u1", "plan": {"id": "STARTER", "maxMonthlyUsageUsd": 39}}}
        ).encode(),
        json.dumps(
            {"data": {"limits": {"maxMonthlyUsageUsd": 39}, "current": {"monthlyUsageUsd": 1.0}}}
        ).encode(),
    ]
    _patch_urlopen(monkeypatch, responses)
    u = get_apify_usage()
    assert u["plan"] == "Apify Starter"
    assert u["monthly_limit_usd"] == 39.0


# ─── Cache & cạn hạn mức ────────────────────────────────────────────


def _limits_ok_payload(usage_usd: float, limit: float = 10.0) -> bytes:
    return json.dumps(
        {
            "data": {
                "limits": {"maxMonthlyUsageUsd": limit, "maxMonthlyActorComputeUnits": 625},
                "current": {"monthlyUsageUsd": usage_usd, "monthlyActorComputeUnits": 10},
                "monthlyUsageCycle": {"endAt": "2026-09-29T23:59:59.999Z"},
            }
        }
    ).encode()


def test_usage_second_call_hits_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lần 2 KHÔNG gọi lại Apify — trang gọi nhiều lần, không đập vào API mỗi lượt."""
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    profile = json.dumps({"data": {"username": "Sin21", "plan": {"id": "FREE"}}}).encode()
    _patch_urlopen(monkeypatch, [profile, _limits_ok_payload(1.0)])

    first = get_apify_usage()
    assert first["cached"] is False
    assert first["usage_usd"] == 1.0

    # Không nạp thêm response → nếu còn gọi mạng, StopIteration sẽ nổ.
    second = get_apify_usage()
    assert second["cached"] is True
    assert second["usage_usd"] == 1.0


def test_usage_refresh_bypasses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """refresh=True (nút 'Kiểm tra số dư') phải đọc lại số mới nhất."""
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    profile = json.dumps({"data": {"username": "Sin21", "plan": {"id": "FREE"}}}).encode()
    _patch_urlopen(
        monkeypatch,
        [profile, _limits_ok_payload(1.0), profile, _limits_ok_payload(4.2)],
    )

    get_apify_usage()
    fresh = get_apify_usage(refresh=True)
    assert fresh["cached"] is False
    assert fresh["usage_usd"] == 4.2
    assert fresh["remaining_usd"] == 5.8


def test_usage_cache_separates_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Đổi token phải đọc lại — không trả số của tài khoản cũ."""
    monkeypatch.setenv("APIFY_TOKEN", "token_a")
    _patch_urlopen(
        monkeypatch,
        [
            json.dumps({"data": {"username": "A", "plan": {"id": "FREE"}}}).encode(),
            _limits_ok_payload(1.0),
            json.dumps({"data": {"username": "B", "plan": {"id": "FREE"}}}).encode(),
            _limits_ok_payload(7.0),
        ],
    )
    assert get_apify_usage()["username"] == "A"

    monkeypatch.setenv("APIFY_TOKEN", "token_b")
    other = get_apify_usage()
    assert other["username"] == "B"
    assert other["usage_usd"] == 7.0


def test_usage_not_cached_when_unmeasured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lỗi mạng là tạm thời — không cache để lần sau còn thử lại."""
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    _patch_urlopen(
        monkeypatch,
        [
            json.dumps({"data": {"username": "Sin21", "plan": {"id": "FREE"}}}).encode(),
            ConnectionError("limits down"),
        ],
    )
    assert get_apify_usage()["usage_measured"] is False
    assert apify_client._usage_cache == {}


def test_usage_flags_quota_exhausted_at_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chạm 100% → quota_exhausted=True để chuỗi cào biết mà dừng gọi Apify."""
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    _patch_urlopen(
        monkeypatch,
        [
            json.dumps({"data": {"username": "Sin21", "plan": {"id": "FREE"}}}).encode(),
            _limits_ok_payload(10.0),
        ],
    )
    u = get_apify_usage()
    assert u["quota_exhausted"] is True
    assert u["status_label"] == "Đã vượt hạn mức"
    assert "chạm trần hạn mức" in u["note"]
    assert "2026-09-29" in u["note"]


def test_usage_under_limit_is_not_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dưới trần thì cờ phải là False — nếu không, chuỗi cào tự khoá oan."""
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    _patch_urlopen(
        monkeypatch,
        [
            json.dumps({"data": {"username": "Sin21", "plan": {"id": "FREE"}}}).encode(),
            _limits_ok_payload(0.41),
        ],
    )
    u = get_apify_usage()
    assert u["quota_exhausted"] is False
    assert u["status_label"] == "Hoạt động bình thường"


# ─── Guard cạn hạn mức ở tầng actor run ─────────────────────────────


def test_actor_run_blocked_when_quota_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Biết chắc đã cạn hạn mức → không gọi HTTP, rớt tầng ngay."""
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    _patch_urlopen(
        monkeypatch,
        [
            json.dumps({"data": {"username": "Sin21", "plan": {"id": "FREE"}}}).encode(),
            _limits_ok_payload(10.0),
        ],
    )
    assert get_apify_usage()["quota_exhausted"] is True

    # Không nạp response nào → nếu có gọi mạng, StopIteration sẽ nổ.
    with pytest.raises(ApifyError, match="cạn hạn mức"):
        run_actor_sync("clockworks/test", {"x": 1})


def test_actor_run_proceeds_when_under_quota(monkeypatch: pytest.MonkeyPatch) -> None:
    """Còn hạn mức → chạy bình thường, guard không được chặn oan."""
    monkeypatch.setenv("APIFY_TOKEN", "test_token")
    _patch_urlopen(
        monkeypatch,
        [
            json.dumps({"data": {"username": "Sin21", "plan": {"id": "FREE"}}}).encode(),
            _limits_ok_payload(0.41),
            json.dumps({"data": {"id": "run_1"}}).encode(),
            json.dumps({"data": {"status": "SUCCEEDED", "defaultDatasetId": "ds1"}}).encode(),
            json.dumps([{"id": "v1"}]).encode(),
        ],
    )
    assert get_apify_usage()["quota_exhausted"] is False
    assert run_actor_sync("clockworks/test", {"x": 1}, timeout_s=10) == [{"id": "v1"}]
