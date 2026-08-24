"""Fail-closed JSON parse + skip providers with no keys."""

from __future__ import annotations

from ca_agents.llm import complete, parse_json_object


def test_parse_json_object_strips_fence() -> None:
    raw = '```json\n{"intent":"doi_ca"}\n```'
    assert parse_json_object(raw) == {"intent": "doi_ca"}


def test_parse_json_object_rejects_garbage() -> None:
    assert parse_json_object("not json") is None
    assert parse_json_object("[1,2]") is None


def test_complete_without_keys_escalates(monkeypatch: object) -> None:
    monkeypatch.setattr(
        "ca_agents.llm.provider_status",
        lambda: {"groq": False, "gemini": False, "openrouter": False, "ollama": False},
    )
    result = complete(system="x", user="y")
    assert result.ok is False
    assert result.provider == "tu_choi"
    assert result.text == ""
