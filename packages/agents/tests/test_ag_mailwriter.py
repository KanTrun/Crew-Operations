from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from ca_agents.ag_mailwriter import (
    draft_email,
    extract_style_preferences,
    format_style_prompt,
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
