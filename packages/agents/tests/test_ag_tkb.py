"""Tests for AG-TKB extract in replay mode and fail-closed live."""

from __future__ import annotations

from ca_agents.ag_tkb import extract_tkb
from ca_agents.llm import LlmResult


def test_extract_known_fixture_has_spans() -> None:
    result = extract_tkb("tkb_01")
    assert result["spans"], "tkb_01 should have spans"
    assert result["confidence"] >= 0.7
    assert result["blur"] is False
    assert result["mode"] == "replay"


def test_extract_blur_fixture_low_confidence() -> None:
    result = extract_tkb("tkb_01_blur")
    assert result["blur"] is True
    assert result["confidence"] < 0.7


def test_extract_returns_required_keys() -> None:
    result = extract_tkb("tkb_02")
    for key in ("rows", "confidence", "spans", "blur"):
        assert key in result, f"missing key: {key}"


def test_extract_unknown_id_returns_empty_spans() -> None:
    result = extract_tkb("tkb_unknown_xyz")
    assert result["rows"] == []
    assert result["spans"] == []
    assert result["confidence"] < 0.7


def test_extract_live_parses_llm_json(monkeypatch: object) -> None:
    def fake_complete(**_k: object) -> LlmResult:
        return LlmResult(
            ok=True,
            text='{"khoang_ban":[{"thu":"T2","start":"07:30","end":"11:00"}],"doc_duoc":true}',
            provider="groq",
            reason="ok",
        )

    monkeypatch.setattr("ca_agents.ag_tkb.extract.complete", fake_complete)  # type: ignore[attr-defined]
    result = extract_tkb("tkb_01", mode="live")
    assert result["mode"] == "live"
    assert result["provider"] == "groq"
    assert result["spans"] == [{"day": "T2", "start": "07:30", "end": "11:00"}]
    assert result["escalate"] is False


def test_extract_live_fail_closed(monkeypatch: object) -> None:
    def fake_complete(**_k: object) -> LlmResult:
        return LlmResult(ok=False, text="", provider="tu_choi", reason="all_down")

    monkeypatch.setattr("ca_agents.ag_tkb.extract.complete", fake_complete)  # type: ignore[attr-defined]
    result = extract_tkb("tkb_01", mode="live")
    assert result["rows"] == []
    assert result["escalate"] is True
    assert result["provider"] == "tu_choi"


def test_extract_live_drops_invalid_hours(monkeypatch: object) -> None:
    def fake_complete(**_k: object) -> LlmResult:
        return LlmResult(
            ok=True,
            text='{"khoang_ban":[{"thu":"T2","start":"99:99","end":"xx"}],"doc_duoc":true}',
            provider="groq",
            reason="ok",
        )

    monkeypatch.setattr("ca_agents.ag_tkb.extract.complete", fake_complete)  # type: ignore[attr-defined]
    result = extract_tkb("tkb_01", mode="live")
    assert result["rows"] == []
    assert result["escalate"] is True
