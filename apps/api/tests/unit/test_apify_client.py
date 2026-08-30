"""Unit tests cho apify_client.py — mock toàn bộ HTTP."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from ca_agents.clients.apify_client import ApifyError, run_actor_sync


# ─── Helpers ────────────────────────────────────────────────────────


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
        json.dumps({"data": {"id": "run_123"}}).encode(),                # start
        json.dumps({"data": {"status": "SUCCEEDED", "defaultDatasetId": "ds1"}}).encode(),
        json.dumps(items).encode(),                                       # dataset
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