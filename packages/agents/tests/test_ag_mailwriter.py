from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from ca_agents.ag_mailwriter import (
    draft_email,
    evaluate_gmail,
    extract_style_preferences,
    feedback_diff,
    format_style_prompt,
    run_gmail_reflection,
)
from ca_agents.llm import LlmResult


def test_draft_email_replay_deterministic() -> None:
    with patch.dict(os.environ, {"CA_AGENT_MODE": "replay"}):
        draft = draft_email("nhắc mai đi làm đúng 7h sáng", recipient_name="Minh", recipient_email="minh@gmail.com")
        assert "[Nhịp Quán]" in draft.subject
        assert "Thân gửi Minh," in draft.body
        assert "nhắc mai đi làm đúng 7h sáng" in draft.body
        assert "Ban Quản Lý Nhịp Quán" in draft.body
        assert draft.recipient_email == "minh@gmail.com"


def test_draft_email_with_shift_ops_context() -> None:
    with patch.dict(os.environ, {"CA_AGENT_MODE": "replay"}):
        shift_ctx = {
            "type": "shift",
            "ca_ten": "Ca sáng",
            "gio": "07:00 - 12:00",
            "ngay": "04/09/2026",
            "vi_tri": "Pha chế (Barista)",
            "dong_doi": ["Lan"],
        }
        draft = draft_email(
            "nhắc mai đi làm",
            recipient_name="Minh",
            ops_context=shift_ctx,
        )
        assert "Ca sáng" in draft.subject
        assert "07:00 - 12:00" in draft.body
        assert "Pha chế (Barista)" in draft.body
        assert "Bạn cùng ca: Lan" in draft.body
        assert draft.ops_context_used == shift_ctx


def test_draft_email_with_inventory_ops_context() -> None:
    with patch.dict(os.environ, {"CA_AGENT_MODE": "replay"}):
        inv_ctx = {
            "type": "inventory",
            "mat_hang": "Sữa tươi tiệt trùng",
            "ton_kho": 4,
            "dvt": "hộp",
            "nguong": 10,
        }
        draft = draft_email(
            "cảnh báo kiểm kho sữa",
            recipient_name="Lan",
            ops_context=inv_ctx,
        )
        assert "Cảnh báo tồn kho" in draft.subject
        assert "Sữa tươi tiệt trùng" in draft.body
        assert "4 hộp" in draft.body
        assert "10 hộp" in draft.body


def test_style_extractor_and_tone_memory() -> None:
    orig = "Thân gửi Minh,\n\nNội dung công việc...\n\nTrân trọng,\nBan Quản Lý"
    amended = "Chào em Minh,\n\nNhớ mai qua quán sớm nha.\n\nThân mến,\nAnh Hùng - Chủ quán"

    prefs = extract_style_preferences(orig, amended)
    assert prefs["greeting_style"] == "Chào em"
    assert "Anh Hùng" in prefs["signoff_name"]

    style_prompt = format_style_prompt(prefs)
    assert 'Chào em [Tên nhân viên]' in style_prompt
    assert 'Anh Hùng' in style_prompt


def test_draft_email_with_learned_style_memory() -> None:
    with patch.dict(os.environ, {"CA_AGENT_MODE": "replay"}):
        style_mem = {
            "greeting_style": "Chào em",
            "signoff_name": "Anh Hùng - Chủ quán",
        }
        draft = draft_email(
            "nhắc đi làm ca sáng",
            recipient_name="Minh",
            style_memory=style_mem,
        )
        assert "Chào em Minh," in draft.body
        assert "Anh Hùng - Chủ quán" in draft.body
        assert draft.has_learned_style is True


def test_draft_email_applies_only_active_style_rules() -> None:
    active_rule = {"rule": {"text": "Dùng lời chào 'Chào em' cho email nội bộ."}}
    # Quy tắc pending (chưa duyệt) không được truyền vào active_style_rules —
    # chính là thứ test này kiểm chứng phải bị bỏ qua.
    with patch.dict(os.environ, {"CA_AGENT_MODE": "replay"}):
        baseline = draft_email("nhắc đi làm", recipient_name="Minh")
        active = draft_email("nhắc đi làm", recipient_name="Minh", active_style_rules=[active_rule])
        pending = draft_email("nhắc đi làm", recipient_name="Minh", active_style_rules=[])
    assert baseline.body.startswith("Thân gửi Minh,")
    assert active.body.startswith("Chào em Minh,")
    assert pending.body == baseline.body


def test_gmail_reflection_proposes_pending_style_rule_with_edit_evidence() -> None:
    feedback = [
        {
            "id": f"feedback-{index}", "store_id": "quan_01", "channel": "gmail",
            "type": "manager_edit", "materially_edited": True,
            "final": {"body": "Chào em Minh,\n\nNhớ nhận ca.\n\nAnh Hùng - Chủ quán"},
        }
        for index in range(3)
    ]
    report = run_gmail_reflection(store_id="quan_01", feedback_events=feedback)
    proposal = report["proposal"]
    assert proposal is not None
    assert proposal["status"] == "pending"
    assert proposal["evidence_ids"] == ["feedback-0", "feedback-1", "feedback-2"]
    assert proposal["evidence_count"] == 3
    assert report["metrics"]["edit_rate"] == 1.0


def test_gmail_reflection_does_not_propose_without_minimum_evidence() -> None:
    feedback = [
        {
            "id": "feedback-1", "store_id": "quan_01", "channel": "gmail",
            "type": "manager_edit", "materially_edited": True,
            "final": {"body": "Chào em Minh,\n\nNhớ nhận ca.\n\nAnh Hùng - Chủ quán"},
        },
        {
            "id": "feedback-2", "store_id": "quan_01", "channel": "gmail",
            "type": "manager_edit", "materially_edited": True,
            "final": {"body": "Thân gửi Minh,\n\nNhớ nhận ca.\n\nBan Quản Lý"},
        },
    ]
    assert run_gmail_reflection(store_id="quan_01", feedback_events=feedback)["proposal"] is None


def test_draft_email_live_with_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "live")

    fake_json = (
        '{"subject": "[Nhịp Quán] Lịch họp toàn thể quán", '
        '"body": "Thân gửi các bạn,\\nQuán tổ chức họp vào 8h sáng mai.\\nTrân trọng,", '
        '"tone": "lich_su", "summary": "Bản nháp họp"}'
    )
    with patch("ca_agents.ag_mailwriter.writer.complete", return_value=LlmResult(ok=True, text=fake_json, provider="mock", reason="")):
        draft = draft_email("họp quán 8h sáng mai", recipient_name="Cả đội")
        assert draft.subject == "[Nhịp Quán] Lịch họp toàn thể quán"
        assert "Thân gửi các bạn" in draft.body


def test_gmail_quality_gate_uses_versioned_score_and_all_critical_dimensions() -> None:
    result = evaluate_gmail(
        recipients=["minh@example.com"],
        subject="[Nhịp Quán] Nhắc lịch ca",
        body="Thân gửi Minh,\n\nBạn vui lòng nhận ca sáng.\n\nTrân trọng,\nBan Quản Lý Nhịp Quán",
    )
    assert result.passed is True
    assert result.action == "send"
    assert result.score == 1.0
    assert result.threshold_version == "gmail-v1"


def test_gmail_quality_gate_blocks_hard_fail_and_queues_review_flags() -> None:
    blocked = evaluate_gmail(
        recipients=["not-an-email"], subject="[Nhịp Quán] Test", body="Thân gửi Minh,\napi_key=secret\nTrân trọng",
    )
    assert blocked.passed is False
    assert blocked.action == "block"
    assert {"invalid_recipient", "internal_data_exposure"}.issubset(blocked.hard_fail_flags)
    review = evaluate_gmail(
        recipients=["minh@example.com"], subject="Nhắc việc [TODO]", body="Thân gửi Minh,\nHoàn tiền cho khách.\nTrân trọng",
    )
    assert review.passed is True
    assert review.action == "queue_review"
    assert {"missing_store_subject_prefix", "placeholder", "financial_commitment"}.issubset(review.flags)


def test_feedback_diff_records_exact_subject_and_body_edits() -> None:
    diff = feedback_diff("[Nhịp Quán] Cũ", "Nội dung cũ", "[Nhịp Quán] Mới", "Nội dung mới")
    assert diff["edited_fields"] == ["subject", "body"]
    assert diff["materially_edited"] is True
    assert diff["original"]["body"] == "Nội dung cũ"
