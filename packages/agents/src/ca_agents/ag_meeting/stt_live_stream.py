"""STT Live Streaming — session streaming realtime cho cuộc họp.

Nguồn: `plans/260918-y-tuong-dot-pha-nho.md` — streaming thật không cần chunking.

Mở WebSocket Gemini Live một lần, nhận audio chunk liên tục (theo tốc độ thực),
trả transcript realtime. Không giới hạn thời gian (không dồn token vì gửi theo
tốc độ thực).
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from dataclasses import dataclass
from typing import Any

from ca_agents.llm import agent_mode, ensure_dotenv

GEMINI_LIVE_ENDPOINT = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
)
GEMINI_TRANSCRIBE_LIVE_MODEL = "gemini-3.5-transcribe-live"
SETUP_TIMEOUT_SECONDS = 15.0


@dataclass
class StreamTranscript:
    """Một đoạn transcript realtime từ Gemini."""

    text: str
    is_final: bool = False


class MeetingStreamSession:
    """Session streaming realtime: nhận audio chunk, trả transcript liên tục."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._ws: Any = None
        self._transcripts: list[str] = []

    async def open(self) -> None:
        """Mở WebSocket Gemini Live + setup."""
        from websockets.asyncio.client import connect

        url = f"{GEMINI_LIVE_ENDPOINT}?key={self._api_key}"
        self._ws = await connect(url, max_size=8 * 1024 * 1024)
        await self._ws.send(
            json.dumps(
                {
                    "setup": {
                        "model": f"models/{GEMINI_TRANSCRIBE_LIVE_MODEL}",
                        "inputAudioTranscription": {},
                    }
                }
            )
        )
        # Đọc setupComplete
        while True:
            msg = await asyncio.wait_for(self._ws.recv(), timeout=SETUP_TIMEOUT_SECONDS)
            if isinstance(msg, bytes):
                msg = msg.decode("utf-8")
            data = json.loads(msg)
            if "setupComplete" in data:
                return
            if "error" in data:
                raise RuntimeError(f"setup_error:{data['error']}")

    async def send_audio(self, pcm16_16khz: bytes) -> None:
        """Gửi một chunk audio PCM16 16kHz lên Gemini (realtime)."""
        if self._ws is None:
            raise RuntimeError("session_not_open")
        await self._ws.send(
            json.dumps(
                {
                    "realtimeInput": {
                        "audio": {
                            "mimeType": "audio/pcm;rate=16000",
                            "data": base64.b64encode(pcm16_16khz).decode("ascii"),
                        }
                    }
                }
            )
        )

    async def end_audio(self) -> None:
        """Đánh dấu hết audio."""
        if self._ws is None:
            return
        await self._ws.send(json.dumps({"realtimeInput": {"activityEnd": {}}}))

    async def receive(self) -> StreamTranscript | None:
        """Nhận một event transcript realtime. Trả None khi hết."""
        if self._ws is None:
            return None
        try:
            msg = await asyncio.wait_for(self._ws.recv(), timeout=30.0)
        except TimeoutError:
            return None
        if isinstance(msg, bytes):
            msg = msg.decode("utf-8")
        data = json.loads(msg)
        if "serverContent" in data:
            sc = data["serverContent"]
            # interimInputTranscription — realtime
            if "interimInputTranscription" in sc:
                t = sc["interimInputTranscription"].get("text", "")
                if t:
                    return StreamTranscript(text=t, is_final=False)
            # finalInputTranscription — cuối đoạn
            if "finalInputTranscription" in sc:
                t = sc["finalInputTranscription"].get("text", "")
                if t:
                    self._transcripts.append(t)
                    return StreamTranscript(text=t, is_final=True)
            if sc.get("turnComplete"):
                return None
        if "error" in data:
            raise RuntimeError(f"error:{data['error']}")
        return None

    async def close(self) -> None:
        """Đóng WebSocket."""
        if self._ws is not None:
            ws, self._ws = self._ws, None
            await ws.close()

    @property
    def full_transcript(self) -> str:
        return " ".join(self._transcripts).strip()


def create_meeting_stream_session() -> MeetingStreamSession | None:
    """Tạo session streaming nếu có key Gemini. Trả None nếu không khả dụng."""
    ensure_dotenv()
    mode = agent_mode()
    if mode == "replay":
        return None
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    return MeetingStreamSession(api_key)