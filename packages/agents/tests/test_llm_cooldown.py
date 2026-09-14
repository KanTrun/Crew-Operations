"""Tests for LLM model and provider cooldown handling during rate limits."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from ca_agents import llm


def test_active_model_list_skips_cooldown() -> None:
    defaults = ("m-high", "m-mid", "m-low")
    llm._MODEL_COOLDOWNS["m-high"] = time.time() + 60.0

    active = llm._active_model_list("TEST_MODEL", defaults)
    assert active == ["m-mid", "m-low"]

    # If all are in cooldown, falls back to trying all
    llm._MODEL_COOLDOWNS["m-mid"] = time.time() + 60.0
    llm._MODEL_COOLDOWNS["m-low"] = time.time() + 60.0
    active_all = llm._active_model_list("TEST_MODEL", defaults)
    assert active_all == ["m-high", "m-mid", "m-low"]

    # Cleanup
    llm._MODEL_COOLDOWNS.clear()


def test_complete_skips_provider_on_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setenv("GROQ_API_KEY", "sk-groq")
    monkeypatch.setenv("GEMINI_API_KEY", "sk-gemini")

    # Put groq on cooldown
    llm._PROVIDER_COOLDOWNS["groq"] = time.time() + 60.0

    with patch("ca_agents.llm._call_provider", return_value='{"ok": true}') as mock_call:
        res = llm.complete(system="s", user="u", json_mode=True)
        assert res.ok is True
        assert res.provider == "gemini"
        mock_call.assert_called_once()
        assert mock_call.call_args[0][0] == "gemini"

    # Cleanup
    llm._PROVIDER_COOLDOWNS.clear()
