# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit test cho STT Live Streaming (plan 260918 — streaming realtime)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from ca_agents.ag_meeting.stt_live_stream import (
    MeetingStreamSession,
    create_meeting_stream_session,
)


class FakeStreamWS:
    """Fake WebSocket cho MeetingStreamSession."""

    def __init__(self) -> None:
        self.sent: list[str | bytes] = []
        self.closed = False
        self._responses: list[dict[str, Any]] = [
            {"serverContent": {"interimInputTranscription": {"text": "Bài"}}},
            {"serverContent": {"finalInputTranscription": {"text": "Bài 1."}}},
            {"serverContent": {"turnComplete": True}},
        ]

    async def send(self, message: str | bytes) -> None:
        self.sent.append(message)

    async def recv(self) -> str:
        if self._responses:
            return json.dumps(self._responses.pop(0))
        raise TimeoutError

    async def close(self) -> None:
        self.closed = True


def test_create_session_replay_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    assert create_meeting_stream_session() is None


def test_create_session_live_returns_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    session = create_meeting_stream_session()
    assert session is not None
    assert isinstance(session, MeetingStreamSession)


def test_session_open_and_receive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    session = MeetingStreamSession("test-key")
    fake = FakeStreamWS()
    session._ws = fake

    async def exercise() -> None:
        # Setup đã có trong fake responses
        await session.send_audio(b"\x00\x00" * 100)
        t1 = await session.receive()
        assert t1 is not None
        assert t1.text == "Bài"
        assert t1.is_final is False
        t2 = await session.receive()
        assert t2 is not None
        assert t2.text == "Bài 1."
        assert t2.is_final is True
        t3 = await session.receive()
        assert t3 is None  # turnComplete → hết

    asyncio.run(exercise())


def test_session_end_audio() -> None:
    session = MeetingStreamSession("test-key")
    fake = FakeStreamWS()
    session._ws = fake

    async def exercise() -> None:
        await session.end_audio()
        # activityEnd được gửi
        assert any("activityEnd" in str(s) for s in fake.sent)

    asyncio.run(exercise())