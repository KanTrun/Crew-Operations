from __future__ import annotations

import json
from pathlib import Path
import pytest
from ca_contracts import (
    ActionProposal,
    ActionProposalStatus,
    CopilotContext,
    CopilotIntent,
    CopilotMessage,
    CopilotResponse,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = ROOT / "packages" / "contracts" / "schema"


def test_copilot_schema_files_exist() -> None:
    msg_schema = json.loads((SCHEMA_DIR / "CopilotMessage.json").read_text(encoding="utf-8"))
    prop_schema = json.loads((SCHEMA_DIR / "ActionProposal.json").read_text(encoding="utf-8"))
    assert msg_schema["title"] == "CopilotMessage"
    assert prop_schema["title"] == "ActionProposal"


def test_copilot_pydantic_models() -> None:
    ctx = CopilotContext(
        store_id="quan_01",
        user_id="nv_01",
        user_role="quan_ly",
        active_date="2026-09-01",
        channel="web",
    )
    msg = CopilotMessage(message="Xếp lịch tuần sau", context=ctx)
    assert msg.context.user_role == "quan_ly"

    prop = ActionProposal(
        action_id="act_001",
        intent=CopilotIntent.SCHEDULE_SOLVE,
        status=ActionProposalStatus.draft,
        summary="Xếp lịch tuần 36",
        store_id="quan_01",
        created_by="nv_01",
        confidence=0.95,
        data_snapshot_hash="hash_123",
        expires_at="2026-09-01T12:00:00Z",
    )
    assert prop.intent == CopilotIntent.SCHEDULE_SOLVE
    assert prop.requires_confirmation is True

    resp = CopilotResponse(
        reply_text="Đã xếp lịch xong",
        intent=CopilotIntent.SCHEDULE_SOLVE,
        confidence=0.95,
        action_proposal=prop,
    )
    assert resp.action_proposal.action_id == "act_001"
