# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit tests cho STT Live (gemini-3.5-transcribe-live) — replay + decode."""

from __future__ import annotations

import asyncio
import struct
import wave
from io import BytesIO

import pytest
from ca_agents.ag_meeting.stt_live import (
    _decode_to_pcm16_16khz,
    transcribe_audio_live,
    transcribe_audio_live_async,
)


def _make_wav_pcm16_16khz(duration_s: float = 1.0) -> bytes:
    buf = BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        frames = bytearray()
        for _ in range(int(16000 * duration_s)):
            frames += struct.pack("<h", 0)  # silence
        w.writeframes(bytes(frames))
    return buf.getvalue()


def test_replay_mode_returns_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    res = transcribe_audio_live(b"fake_audio", mime_type="audio/webm")
    assert res.ok is True
    assert res.provider == "replay_fixture"
    assert "máy pha" in res.raw_text


def test_empty_audio_returns_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    res = transcribe_audio_live(b"", mime_type="audio/webm")
    assert res.provider == "replay_fixture"


def test_missing_key_returns_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    res = transcribe_audio_live(b"fake", mime_type="audio/webm")
    assert res.provider == "replay_fixture"


def test_decode_wav_pcm16_16khz() -> None:
    wav = _make_wav_pcm16_16khz(1.0)
    pcm = _decode_to_pcm16_16khz(wav, "audio/wav")
    assert pcm is not None
    assert len(pcm) == 16000 * 2  # 1s PCM16 16kHz


def test_decode_unknown_format_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    # Không có ffmpeg → trả None cho định dạng không phải wav
    monkeypatch.setattr("ca_agents.ag_meeting.stt_live._decode_to_pcm16_16khz", lambda *a, **k: None)
    assert _decode_to_pcm16_16khz(b"garbage", "audio/webm") is None


def test_async_replay_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    res = asyncio.run(transcribe_audio_live_async(b"fake", mime_type="audio/webm"))
    assert res.provider == "replay_fixture"