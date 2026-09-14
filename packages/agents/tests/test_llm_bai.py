"""Tests for b.ai LLM provider integration."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from ca_agents import llm


def test_bai_provider_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BAI_API_KEY", "sk-test-bai-key")
    status = llm.provider_status()
    assert status.get("bai") is True


def test_bai_model_aliases() -> None:
    models = llm._model_list("BAI_MODEL", llm._BAI_MODELS)
    assert "qwen3.8-flash" in models
    assert "mimo-v2.5" in models
    assert "hy3" in models


def test_complete_routes_to_bai_when_others_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("BAI_API_KEY", "sk-test-bai-key")

    with patch("ca_agents.llm._call_provider", return_value='{"status": "ok"}') as mock_call:
        res = llm.complete(system="sys", user="usr", json_mode=True)
        assert res.ok is True
        assert res.provider == "bai"
        assert res.text == '{"status": "ok"}'
        mock_call.assert_called_once()
        assert mock_call.call_args[0][0] == "bai"
