"""Unit & Integration tests cho Ops Explain API (plan 260918 mục 3)."""

from __future__ import annotations

import pytest
from ca_api.interfaces.http.main import app
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


@pytest.fixture(autouse=True)
def _pin_replay_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")


def test_explain_endpoint() -> None:
    ql = headers(client, "lan")
    res = client.post(
        "/api/v1/ops/explain",
        json={"cau_hoi": "Tại sao ca tối T6 có 2 pha chế?"},
        headers=ql,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert "chain" in body
    assert body["chain"]["cau_hoi"] == "Tại sao ca tối T6 có 2 pha chế?"


def test_explain_chains_endpoint() -> None:
    ql = headers(client, "lan")
    res = client.get("/api/v1/ops/explain/chains", headers=ql)
    assert res.status_code == 200, res.text
    assert "items" in res.json()


def test_explain_requires_auth() -> None:
    res = client.post("/api/v1/ops/explain", json={"cau_hoi": "Tại sao?"})
    assert res.status_code in (401, 403)


def test_reflect_endpoint() -> None:
    ql = headers(client, "lan")
    res = client.post(
        "/api/v1/ops/reflect",
        json={"cau_hoi": "Tuần này có gì bất thường?"},
        headers=ql,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert "result" in body
    assert "ket_luan" in body["result"]