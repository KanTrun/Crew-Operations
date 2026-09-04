from __future__ import annotations

from ca_api.ai_learning.repository import AILearningRepository
from ca_api.interfaces.http.main import app
from ca_contracts import AIFeedbackEvent, AIGenerationRecord
from fastapi.testclient import TestClient

from unit.auth_util import headers


client = TestClient(app)


def test_facebook_reflection_saves_pending_proposal_from_persisted_feedback() -> None:
    repository = AILearningRepository()
    generation = AIGenerationRecord(
        id="facebook-reflection-generation", store_id="quan_01", channel="facebook",
        conversation_id="psid-reflection", request_kind="facebook_message", draft={"body": "Bản nháp"},
        context_snapshot_hash="context", agent_version="fb-v1", prompt_version="fb-v1", rule_version="none",
        rollout_bucket="control", model={"provider": "replay", "model_id": "replay", "temperature": 0, "tool_context_hash": "context"},
        policy_action="queue_review", idempotency_key="facebook-reflection-generation", created_at="2026-09-04T10:00:00Z",
    )
    assert repository.save(generation)
    for index in range(3):
        assert repository.save(AIFeedbackEvent(
            id=f"facebook-reflection-feedback-{index}", store_id="quan_01", generation_id=generation.id,
            channel="facebook", type="manager_edit", original={"body": "Bản nháp"},
            final={"body": "Dạ Nhịp Quán xin chào mình ạ!\n\nEm hỗ trợ mình ngay."}, edited_fields=["body"],
            materially_edited=True, actor_role="quan_ly", idempotency_key=f"facebook-reflection-feedback-{index}",
            created_at=f"2026-09-04T10:0{index}:00Z",
        ))
    response = client.post("/api/v1/ai/reflection/facebook/run", headers=headers(client, "lan"))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["proposal_saved"] is True
    proposal = repository.get_rule_proposal(store_id="quan_01", proposal_id=result["proposal_id"])
    assert proposal is not None and proposal["status"] == "pending"