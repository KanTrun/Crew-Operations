from __future__ import annotations

from ca_api.interfaces.http.main import app
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def test_health_reports_replay_in_pytest() -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["agent_mode"] == "replay"


def test_llm_status_requires_auth() -> None:
    assert client.get("/api/v1/llm/status").status_code == 401
    body = client.get("/api/v1/llm/status", headers=headers(client, "lan")).json()
    assert body["mode"] == "replay"
    assert body["sop_explain_brief"] == "deterministic"
    assert set(body["providers"]) == {"groq", "gemini", "openrouter", "ollama"}


def test_tkb_extract_replay() -> None:
    r = client.post(
        "/api/v1/tkb/extract",
        json={"image_path_or_id": "tkb_01"},
        headers=headers(client, "lan"),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "replay"
    assert body["spans"]
