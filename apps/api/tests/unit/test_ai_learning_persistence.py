from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
import ca_api.persist as persist
from ca_api.ai_learning.redaction import redact_record
from ca_api.ai_learning.repository import AILearningRepository
from ca_api.ai_learning.security import configure_data_protection, minimal_data_mode
from ca_api.interfaces.http.channels import _record_fb_feedback
from ca_contracts import AIEvaluation, AIFeedbackEvent, AIGenerationRecord, AIRuleProposal


@pytest.fixture(autouse=True)
def _reset_data_protection_after_test():
    yield
    configure_data_protection()


def _generation(store_id: str, record_id: str, idempotency_key: str) -> AIGenerationRecord:
    return AIGenerationRecord(
        id=record_id, store_id=store_id, channel="gmail", request_kind="gmail_request",
        draft={"body": "Liên hệ minh@example.com số 0912345678"}, context_snapshot_hash="ctx",
        agent_version="mail-v1", prompt_version="prompt-v1", rule_version="none", rollout_bucket="control",
        model={"provider": "replay", "model_id": "replay", "temperature": 0, "tool_context_hash": "tool"},
        policy_action="queue_review", idempotency_key=idempotency_key, created_at="2026-09-04T10:00:00Z",
    )


def _feedback(store_id: str, record_id: str, generation_id: str, idempotency_key: str) -> AIFeedbackEvent:
    return AIFeedbackEvent(
        id=record_id, store_id=store_id, generation_id=generation_id, channel="gmail",
        type="manager_approve", actor_role="quan_ly", idempotency_key=idempotency_key,
        created_at="2026-09-04T10:01:00Z",
    )


def _evaluation(store_id: str, record_id: str, generation_id: str, idempotency_key: str) -> AIEvaluation:
    return AIEvaluation(
        id=record_id, store_id=store_id, generation_id=generation_id, channel="gmail",
        scores={"accuracy": 1, "safety": 1}, aggregate_score=1, passed=True,
        action="queue_review", threshold_version="quality-v1", calibration_version="calibration-v1",
        sample_count=1, evaluation_window="pre_send", evaluator="deterministic-v1",
        idempotency_key=idempotency_key, created_at="2026-09-04T10:02:00Z",
    )


def _proposal(store_id: str, record_id: str, evidence_id: str, idempotency_key: str) -> AIRuleProposal:
    return AIRuleProposal(
        id=record_id, store_id=store_id, channel="gmail", rule_type="style",
        rule={"text": "Ngắn gọn", "intent_scope": ["notify_shift"], "audience_scope": ["employee"], "priority": 1},
        evidence_count=1, evidence_ids=[evidence_id], confidence=0.9, version=1,
        idempotency_key=idempotency_key, created_at="2026-09-04T10:03:00Z", updated_at="2026-09-04T10:03:00Z",
    )


def test_init_db_migrates_legacy_users_before_fixture_seed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE users(username TEXT PRIMARY KEY, password_sha TEXT, role TEXT, nv_id TEXT, display_name TEXT)"
        )
    monkeypatch.setenv("NHIPQUAN_DB", str(database))
    persist.reset_init_flag()
    persist.init_db()
    with sqlite3.connect(database) as connection:
        columns = {column[1] for column in connection.execute("PRAGMA table_info(users)")}
        seeded = connection.execute("SELECT store_id FROM users WHERE username='lan'").fetchone()
    assert "store_id" in columns
    assert seeded == ("quan_01",)


def test_facebook_approval_feedback_links_to_same_store_conversation() -> None:
    repository = AILearningRepository()
    generation = AIGenerationRecord(
        id="facebook-generation", store_id="quan_a", channel="facebook", conversation_id="psid-1",
        request_kind="facebook_message", draft={"body": "Bản nháp"}, context_snapshot_hash="ctx",
        agent_version="fb-v1", prompt_version="fb-v1", rule_version="none", rollout_bucket="control",
        model={"provider": "replay", "model_id": "replay", "temperature": 0, "tool_context_hash": "tool"},
        policy_action="queue_review", idempotency_key="facebook-generation", created_at="2026-09-04T10:00:00Z",
    )
    assert repository.save(generation)
    _record_fb_feedback(
        store_id="quan_a", conversation_id="psid-1", feedback_type="manager_edit",
        original="Bản nháp", final="Bản quản lý sửa", actor_user_id="nv_01", actor_role="quan_ly",
        generation_id=generation.id,
    )
    feedback = repository.list("feedback", store_id="quan_a")
    assert len(feedback) == 1
    assert feedback[0]["generation_id"] == generation.id
    assert feedback[0]["materially_edited"] is True


def test_store_cannot_read_any_learning_record_from_another_store(monkeypatch) -> None:
    monkeypatch.setenv("NHIPQUAN_ENV", "development")
    configure_data_protection()
    repository = AILearningRepository()
    for store_id, suffix in (("quan_a", "a"), ("quan_b", "b")):
        generation = _generation(store_id, f"generation_{suffix}", f"generation_{suffix}")
        feedback = _feedback(store_id, f"feedback_{suffix}", generation.id, f"feedback_{suffix}")
        assert repository.save(generation)
        assert repository.save(feedback)
        assert repository.save(_evaluation(store_id, f"evaluation_{suffix}", generation.id, f"evaluation_{suffix}"))
        assert repository.save(_proposal(store_id, f"proposal_{suffix}", feedback.id, f"proposal_{suffix}"))
    for kind in ("generation", "feedback", "evaluation", "rule_proposal"):
        assert [item["store_id"] for item in repository.list(kind, store_id="quan_a")] == ["quan_a"]
        assert [item["store_id"] for item in repository.list(kind, store_id="quan_b")] == ["quan_b"]


def test_cross_tenant_generation_references_are_rejected_before_write() -> None:
    repository = AILearningRepository()
    assert repository.save(_generation("quan_a", "generation_a", "generation_a"))
    with pytest.raises(ValueError, match="cross_tenant_generation"):
        repository.save(_feedback("quan_b", "feedback_b", "generation_a", "feedback_b"))
    with pytest.raises(ValueError, match="cross_tenant_generation"):
        repository.save(_evaluation("quan_b", "evaluation_b", "generation_a", "evaluation_b"))
    assert repository.list("feedback", store_id="quan_b") == []
    assert repository.list("evaluation", store_id="quan_b") == []


def test_cross_tenant_proposal_evidence_is_rejected_before_write() -> None:
    repository = AILearningRepository()
    assert repository.save(_generation("quan_a", "generation_a", "generation_a"))
    assert repository.save(_feedback("quan_a", "feedback_a", "generation_a", "feedback_a"))
    with pytest.raises(ValueError, match="cross_tenant_evidence"):
        repository.save(_proposal("quan_b", "proposal_b", "feedback_a", "proposal_b"))
    assert repository.list("rule_proposal", store_id="quan_b") == []


def test_each_record_kind_is_idempotent() -> None:
    repository = AILearningRepository()
    generation = _generation("quan_a", "generation_1", "idem_generation")
    feedback = _feedback("quan_a", "feedback_1", generation.id, "idem_feedback")
    evaluation = _evaluation("quan_a", "evaluation_1", generation.id, "idem_evaluation")
    proposal = _proposal("quan_a", "proposal_1", feedback.id, "idem_proposal")
    for record in (generation, feedback, evaluation, proposal):
        assert repository.save(record)
        assert not repository.save(record)
    assert len(repository.list("generation", store_id="quan_a")) == 1
    assert len(repository.list("feedback", store_id="quan_a")) == 1
    assert len(repository.list("evaluation", store_id="quan_a")) == 1
    assert len(repository.list("rule_proposal", store_id="quan_a")) == 1


def test_rule_lifecycle_is_tenant_scoped_and_only_active_rules_are_injected() -> None:
    repository = AILearningRepository()
    generation = _generation("quan_a", "generation_rule", "generation_rule")
    feedback = _feedback("quan_a", "feedback_rule", generation.id, "feedback_rule")
    proposal = _proposal("quan_a", "proposal_rule", feedback.id, "proposal_rule")
    assert repository.save(generation)
    assert repository.save(feedback)
    assert repository.save(proposal)
    assert repository.get_rule_proposal(store_id="quan_b", proposal_id=proposal.id) is None
    assert repository.transition_rule_proposal(
        store_id="quan_b", proposal_id=proposal.id, target_status="approved", actor_id="owner_b",
        updated_at="2026-09-04T11:00:00Z",
    ) is None
    approved = repository.transition_rule_proposal(
        store_id="quan_a", proposal_id=proposal.id, target_status="approved", actor_id="owner_a",
        updated_at="2026-09-04T11:00:00Z",
    )
    assert approved and approved["status"] == "approved"
    assert repository.active_rules(store_id="quan_a", channel="gmail") == []
    active = repository.transition_rule_proposal(
        store_id="quan_a", proposal_id=proposal.id, target_status="active", actor_id="owner_a",
        updated_at="2026-09-04T11:01:00Z",
    )
    assert active and active["approved_by"] == "owner_a"
    assert [rule["id"] for rule in repository.active_rules(store_id="quan_a", channel="gmail")] == [proposal.id]
    paused = repository.transition_rule_proposal(
        store_id="quan_a", proposal_id=proposal.id, target_status="paused", actor_id="owner_a",
        updated_at="2026-09-04T11:02:00Z",
    )
    assert paused and paused["status"] == "paused"
    assert repository.active_rules(store_id="quan_a", channel="gmail") == []


def test_rule_conflicts_hold_same_scope_competing_directives_for_review() -> None:
    repository = AILearningRepository()
    generation = _generation("quan_conflict", "generation_conflict", "generation_conflict")
    feedback = _feedback("quan_conflict", "feedback_conflict", generation.id, "feedback_conflict")
    active = _proposal("quan_conflict", "rule_active", feedback.id, "rule_active")
    assert repository.save(generation)
    assert repository.save(feedback)
    assert repository.save(active)
    assert repository.transition_rule_proposal(
        store_id="quan_conflict", proposal_id=active.id, target_status="approved", actor_id="owner",
        updated_at="2026-09-04T11:00:00Z",
    )
    assert repository.transition_rule_proposal(
        store_id="quan_conflict", proposal_id=active.id, target_status="active", actor_id="owner",
        updated_at="2026-09-04T11:01:00Z",
    )
    candidate = _proposal("quan_conflict", "rule_candidate", feedback.id, "rule_candidate")
    candidate.rule.text = "Trang trọng"
    assert repository.save(candidate)
    assert [rule["id"] for rule in repository.rule_conflicts(candidate.model_dump(mode="json"))] == [active.id]


def test_redaction_removes_email_phone_and_secret_values_from_learning_payload() -> None:
    secret = "app-password-secret-123"
    redacted = redact_record(
        {"email": "minh@example.com", "phone": "0912345678", "token": secret, "nested": {"app_password": secret, "body": "minh@example.com 0912345678"}},
        minimal_data=False,
    )
    serialized = json.dumps(redacted, ensure_ascii=False)
    for value in ("minh@example.com", "0912345678", secret):
        assert value not in serialized
    assert "[email_redacted]" in serialized
    assert "[phone_redacted]" in serialized


def test_backup_snapshot_has_store_coverage_schema_and_checksum(tmp_path) -> None:
    repository = AILearningRepository()
    assert repository.save(_generation("quan_backup", "generation_backup", "generation_backup"))
    backup = repository.backup(store_id="quan_backup", directory=tmp_path)
    snapshot = json.loads(Path(backup["snapshot_path"]).read_text(encoding="utf-8"))
    manifest = json.loads(Path(backup["manifest_path"]).read_text(encoding="utf-8"))
    digest = hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert snapshot["store_id"] == "quan_backup"
    assert snapshot["schema_version"] == 1
    assert manifest["store_id"] == "quan_backup"
    assert manifest["checksum_sha256"] == digest == backup["checksum_sha256"]
    assert manifest["record_counts"]["generation"] == 1
    assert repository.verify_backup(snapshot_path=Path(backup["snapshot_path"]), manifest_path=Path(backup["manifest_path"]))
    Path(backup["snapshot_path"]).write_text("{}", encoding="utf-8")
    assert not repository.verify_backup(snapshot_path=Path(backup["snapshot_path"]), manifest_path=Path(backup["manifest_path"]))


def test_production_backup_requires_attested_encrypted_root(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("NHIPQUAN_ENV", "production")
    monkeypatch.setenv("NHIPQUAN_ENCRYPTED_VOLUME_VERIFIED", "true")
    monkeypatch.setenv("NHIPQUAN_ENCRYPTED_DATA_ROOT", str(tmp_path / "encrypted"))
    repository = AILearningRepository()
    assert repository.save(_generation("quan_backup", "generation_backup", "generation_backup"))
    with pytest.raises(ValueError, match="backup_outside_encrypted_root"):
        repository.backup(store_id="quan_backup", directory=tmp_path / "outside")
    backup = repository.backup(store_id="quan_backup", directory=tmp_path / "encrypted" / "backups")
    assert Path(backup["snapshot_path"]).is_file()


def test_unverified_production_uses_minimal_data(monkeypatch) -> None:
    monkeypatch.setenv("NHIPQUAN_ENV", "production")
    monkeypatch.delenv("NHIPQUAN_ENCRYPTED_VOLUME_VERIFIED", raising=False)
    assert not configure_data_protection()
    assert minimal_data_mode()
    repository = AILearningRepository()
    assert repository.save(_generation("quan_01", "minimal", "minimal-idem"))
    item = repository.list("generation", store_id="quan_01")[0]
    assert item["draft"]["body"].startswith("sha256:")
