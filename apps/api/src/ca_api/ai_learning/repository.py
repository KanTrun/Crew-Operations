"""Typed persistence boundary for AI Learning Loop records."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from ca_contracts import AIEvaluation, AIFeedbackEvent, AIGenerationRecord, AIRuleProposal

from ca_api.ai_learning.redaction import redact_record
from ca_api.ai_learning.security import configure_data_protection, minimal_data_mode
from ca_api.persist import (
    ai_learning_backup,
    ai_learning_list,
    ai_learning_save,
    ai_learning_snapshot,
    ai_learning_verify_backup,
    ai_rule_active_list,
    ai_rule_proposal_get,
    ai_rule_proposal_list,
    ai_rule_proposal_transition,
)

RecordKind = Literal["generation", "feedback", "evaluation", "rule_proposal"]
Record = AIGenerationRecord | AIFeedbackEvent | AIEvaluation | AIRuleProposal


class AILearningRepository:
    """All data reads require a store ID; callers cannot retrieve a global feed."""

    def save(self, record: Record) -> bool:
        if isinstance(record, AIGenerationRecord):
            kind: RecordKind = "generation"
        elif isinstance(record, AIFeedbackEvent):
            kind = "feedback"
        elif isinstance(record, AIEvaluation):
            kind = "evaluation"
        else:
            kind = "rule_proposal"
        configure_data_protection()
        return ai_learning_save(kind, redact_record(record.model_dump(mode="json"), minimal_data=minimal_data_mode()))

    def list(self, kind: RecordKind, *, store_id: str, limit: int = 50) -> list[dict[str, Any]]:
        return ai_learning_list(kind, store_id=store_id, limit=limit)

    def get_rule_proposal(self, *, store_id: str, proposal_id: str) -> dict[str, Any] | None:
        return ai_rule_proposal_get(store_id=store_id, proposal_id=proposal_id)

    def list_rule_proposals(
        self, *, store_id: str, channel: str | None = None, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        return ai_rule_proposal_list(store_id=store_id, channel=channel, status=status, limit=limit)

    def transition_rule_proposal(
        self, *, store_id: str, proposal_id: str, target_status: str, actor_id: str, updated_at: str,
        rejection_reason: str | None = None,
    ) -> dict[str, Any] | None:
        return ai_rule_proposal_transition(
            store_id=store_id,
            proposal_id=proposal_id,
            target_status=target_status,
            actor_id=actor_id,
            updated_at=updated_at,
            rejection_reason=rejection_reason,
        )

    def active_rules(self, *, store_id: str, channel: str, limit: int = 50) -> list[dict[str, Any]]:
        return ai_rule_active_list(store_id=store_id, channel=channel, limit=limit)

    def rule_conflicts(self, proposal: dict[str, Any]) -> list[dict[str, Any]]:
        """Find deterministic same-scope conflicts; ambiguous cases stay human-reviewed."""
        rule = proposal.get("rule") or {}
        text = " ".join(str(rule.get("text") or "").lower().split())
        intent_scope = set(rule.get("intent_scope") or [])
        audience_scope = set(rule.get("audience_scope") or [])
        priority = rule.get("priority")
        conflicts = []
        for active in self.active_rules(store_id=str(proposal["store_id"]), channel=str(proposal["channel"])):
            active_rule = active.get("rule") or {}
            active_text = " ".join(str(active_rule.get("text") or "").lower().split())
            same_scope = (
                intent_scope == set(active_rule.get("intent_scope") or [])
                and audience_scope == set(active_rule.get("audience_scope") or [])
            )
            without_negation = lambda value: value.removeprefix("không ").removeprefix("khong ").strip()
            contradictory = (
                (text.startswith(("không ", "khong ")) and without_negation(text) == active_text)
                or (active_text.startswith(("không ", "khong ")) and without_negation(active_text) == text)
            )
            priority_conflict = same_scope and priority == active_rule.get("priority") and text != active_text
            if same_scope and (contradictory or priority_conflict):
                conflicts.append(active)
        return conflicts

    def snapshot(self, *, store_id: str) -> dict[str, Any]:
        return ai_learning_snapshot(store_id=store_id)

    def backup(self, *, store_id: str, directory: Path | None = None) -> dict[str, Any]:
        return ai_learning_backup(store_id=store_id, directory=directory)

    def verify_backup(self, *, snapshot_path: Path, manifest_path: Path) -> bool:
        return ai_learning_verify_backup(snapshot_path=snapshot_path, manifest_path=manifest_path)