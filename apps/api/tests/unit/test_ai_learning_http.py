from __future__ import annotations

from ca_api.ai_learning.repository import AILearningRepository
from ca_api.interfaces.http.main import app
from ca_contracts import AIFeedbackEvent, AIGenerationRecord
from fastapi.testclient import TestClient

from unit.auth_util import headers


client = TestClient(app)


def test_feedback_rejects_unknown_contract_values() -> None:
    response = client.post(
        "/api/v1/ai/feedback",
        json={"generation_id": "unknown", "channel": "gmail", "type": "approve_everything"},
        headers=headers(client, "lan"),
    )
    assert response.status_code == 422


def _seed_edit_feedback() -> None:
    repository = AILearningRepository()
    for index in range(3):
        generation_id = f"http-generation-{index}"
        assert repository.save(AIGenerationRecord(
            id=generation_id, store_id="quan_01", channel="gmail", request_kind="gmail_request",
            draft={"body": "Nhắc nhận ca"}, context_snapshot_hash=f"ctx-{index}", agent_version="test",
            prompt_version="test", rule_version="none", rollout_bucket="control",
            model={"provider": "test", "model_id": "test", "temperature": 0, "tool_context_hash": "test"},
            policy_action="queue_review", idempotency_key=f"http-generation:{index}", created_at=f"2026-09-0{index + 1}T10:00:00Z",
        ))
        assert repository.save(AIFeedbackEvent(
            id=f"http-feedback-{index}", store_id="quan_01", generation_id=generation_id, channel="gmail",
            type="manager_edit", original={"body": "Thân gửi Minh"},
            final={"body": "Chào em Minh,\n\nNhớ nhận ca.\n\nAnh Hùng - Chủ quán"}, materially_edited=True,
            actor_role="quan_ly", idempotency_key=f"http-feedback:{index}", created_at=f"2026-09-0{index + 1}T10:01:00Z",
        ))


def test_owner_can_run_reflection_and_activate_proposal() -> None:
    _seed_edit_feedback()
    manager_headers = headers(client, "lan")
    owner_headers = headers(client, "hung")
    reflection = client.post("/api/v1/ai/reflection/gmail/run", headers=manager_headers)
    assert reflection.status_code == 200, reflection.text
    proposal_id = reflection.json()["proposal_id"]
    assert proposal_id
    assert client.post(f"/api/v1/ai/rules/proposals/{proposal_id}/approve", headers=manager_headers).status_code == 403
    assert client.post(f"/api/v1/ai/rules/proposals/{proposal_id}/approve", headers=owner_headers).status_code == 200
    active = client.post(f"/api/v1/ai/rules/proposals/{proposal_id}/activate", headers=owner_headers)
    assert active.status_code == 200
    listed = client.get("/api/v1/ai/rules/proposals?channel=gmail&status=active", headers=manager_headers)
    assert proposal_id in [item["id"] for item in listed.json()["items"]]


def test_operations_controls_are_owner_gated() -> None:
    manager_headers = headers(client, "lan")
    owner_headers = headers(client, "hung")
    assert client.get("/api/v1/ai/operations/status", headers=manager_headers).status_code == 200
    assert client.get("/api/v1/ai/retention/dry-run", headers=manager_headers).status_code == 403
    response = client.post(
        "/api/v1/ai/operations/circuit-breaker", json={"channel": "gmail", "open": True}, headers=owner_headers,
    )
    assert response.status_code == 200
    assert response.json()["open"] is True


def test_gmail_circuit_breaker_blocks_send(monkeypatch) -> None:
    owner_headers = headers(client, "hung")
    manager_headers = headers(client, "lan")
    client.post("/api/v1/ai/operations/circuit-breaker", json={"channel": "gmail", "open": True}, headers=owner_headers)
    response = client.post(
        "/api/v1/mail/send",
        json={"to_nv_ids": ["nv_03"], "subject": "[Nhịp Quán] Test", "body": "Thân gửi Minh,\n\nNội dung.\n\nTrân trọng,\nBan Quản Lý Nhịp Quán"},
        headers=manager_headers,
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "ai_circuit_breaker_open"
    client.post("/api/v1/ai/operations/circuit-breaker", json={"channel": "gmail", "open": False}, headers=owner_headers)