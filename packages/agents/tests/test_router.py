"""Tests for FreeTierRouter — 5-provider live order + replay."""

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


def test_live_order_skip_groq_gives_openrouter() -> None:
    router = FreeTierRouter(mode="live")
    d = router.choose("text:foo", exhausted={"groq"})
    assert d.provider == "openrouter"


def test_live_order_skip_two() -> None:
    router = FreeTierRouter(mode="live")
    d = router.choose("text:foo", exhausted={"groq", "openrouter"})
    assert d.provider == "bai"


def test_live_order_skip_three() -> None:
    router = FreeTierRouter(mode="live")
    d = router.choose("text:foo", exhausted={"groq", "openrouter", "bai"})
    assert d.provider == "ollama"


def test_live_order_skip_four() -> None:
    router = FreeTierRouter(mode="live")
    d = router.choose("text:foo", exhausted={"groq", "openrouter", "bai", "ollama"})
    assert d.provider == "tu_choi"


def test_all_exhausted_returns_tu_choi() -> None:
    router = FreeTierRouter(mode="live")
    d = router.choose("text:foo", exhausted={"groq", "openrouter", "bai", "ollama"})
    assert d.provider == "tu_choi"
    assert "escalate" in d.reason


def test_vision_order_includes_bai() -> None:
    router = FreeTierRouter(mode="live")
    d = router.choose("vision:tkb", exhausted={"gemini", "openrouter", "groq"})
    assert d.provider == "bai"

