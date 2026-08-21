"""Tests for FreeTierRouter — 4-provider live order + replay."""

from __future__ import annotations

from ca_agents.router import FreeTierRouter


def test_replay_mode_always_replay() -> None:
    router = FreeTierRouter(mode="replay")
    for task in ("vision:foo", "text:bar", ""):
        d = router.choose(task)
        assert d.provider == "replay"


def test_live_order_first_is_groq() -> None:
    router = FreeTierRouter(mode="live")
    d = router.choose("text:foo")
    assert d.provider == "groq"


def test_live_order_skip_groq_gives_gemini() -> None:
    router = FreeTierRouter(mode="live")
    d = router.choose("text:foo", exhausted={"groq"})
    assert d.provider == "gemini"


def test_live_order_skip_two() -> None:
    router = FreeTierRouter(mode="live")
    d = router.choose("text:foo", exhausted={"groq", "gemini"})
    assert d.provider == "openrouter"


def test_live_order_skip_three() -> None:
    router = FreeTierRouter(mode="live")
    d = router.choose("text:foo", exhausted={"groq", "gemini", "openrouter"})
    assert d.provider == "ollama"


def test_all_exhausted_returns_tu_choi() -> None:
    router = FreeTierRouter(mode="live")
    d = router.choose("text:foo", exhausted={"groq", "gemini", "openrouter", "ollama"})
    assert d.provider == "tu_choi"
    assert "escalate" in d.reason
