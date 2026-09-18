"""Authenticated server-to-server WebSocket proxy for AG-COPILOT voice."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime

from ca_agents.ag_copilot.voice_session import (
    GeminiLiveSession,
    VerifiedVoiceContext,
    VoiceSessionUnavailable,
)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ca_api.persist import audit_add
from ca_api.persist import session as auth_session

router = APIRouter(tags=["copilot-voice"])

AUTH_TIMEOUT_SECONDS = 5.0
VOICE_IDLE_TIMEOUT_SECONDS = float(os.environ.get("VOICE_IDLE_TIMEOUT_SECONDS", "60.0"))
VOICE_SESSION_MAX_SECONDS = float(os.environ.get("VOICE_SESSION_MAX_SECONDS", "300.0"))
MAX_TEXT_LENGTH = 2000
MAX_AUDIO_CHUNK_BYTES = 65536  # 64 KB per PCM chunk
MAX_MESSAGES_PER_SECOND = 25.0

@dataclass
class _ActiveVoiceSession:
    websocket: WebSocket
    stop_event: asyncio.Event
    loop: asyncio.AbstractEventLoop

_ACTIVE_VOICE_SESSIONS: dict[str, _ActiveVoiceSession] = {}
_ACTIVE_SESSIONS_LOCK = threading.Lock()



class TokenBucket:
    """Token-bucket rate limiter per WebSocket connection."""

    def __init__(self, rate: float = 25.0, capacity: float = 40.0) -> None:
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last = time.monotonic()

    def allow(self, cost: float = 1.0) -> bool:
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


class ActivityTracker:
    """Track last user audio/text activity for idle timeout watchdog."""

    def __init__(self) -> None:
        self.last_activity = time.monotonic()

    def touch(self) -> None:
        self.last_activity = time.monotonic()

    def idle_seconds(self) -> float:
        return time.monotonic() - self.last_activity


def _verified_context(token: str) -> VerifiedVoiceContext | None:
    session = auth_session(f"Bearer {token}") or auth_session(token)
    if not session:
        return None
    user_id = str(session.get("nv_id") or "").strip()
    role = str(session.get("role") or "")
    if not user_id or role not in {"chu_quan", "quan_ly", "nhan_vien"}:
        return None
    return VerifiedVoiceContext(
        user_id=user_id,
        user_role=role,
        store_id=str(session.get("store_id") or "quan_01"),
    )


async def _authenticate(websocket: WebSocket) -> VerifiedVoiceContext | None:
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS)
        message = json.loads(raw)
    except (TimeoutError, WebSocketDisconnect, json.JSONDecodeError, RuntimeError, Exception):
        return None
    if not isinstance(message, dict):
        return None
    if message.get("event") != "auth" or not message.get("token"):
        return None
    return _verified_context(str(message["token"]).strip())


async def _receive_client(
    websocket: WebSocket,
    live: GeminiLiveSession,
    tracker: ActivityTracker,
    limiter: TokenBucket,
) -> None:
    consecutive_oversize = 0
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return

        if not limiter.allow():
            continue

        audio = message.get("bytes")
        if audio is not None:
            if audio:
                if len(audio) > MAX_AUDIO_CHUNK_BYTES:
                    consecutive_oversize += 1
                    if consecutive_oversize >= 3:
                        await websocket.close(code=4003, reason="rate_limited")
                        return
                    continue
                consecutive_oversize = 0
                tracker.touch()
                await live.send_audio(audio)
            continue

        raw = message.get("text")
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        event = payload.get("event")
        if event == "stop":
            return
        if event == "text":
            text = str(payload.get("text") or "").strip()
            if text:
                tracker.touch()
                await live.send_text(text[:MAX_TEXT_LENGTH])
        elif event == "interrupt":
            tracker.touch()
            await websocket.send_json({"event": "voice:interrupted"})
        elif event == "activity_start":
            tracker.touch()
            await live.send_activity_start()
        elif event == "activity_end":
            tracker.touch()
            await live.send_activity_end()


async def _receive_upstream(websocket: WebSocket, live: GeminiLiveSession) -> None:
    while True:
        event = await live.receive()
        await websocket.send_json({"event": "voice:upstream", "data": event})


async def _idle_watchdog(websocket: WebSocket, tracker: ActivityTracker) -> None:
    while True:
        await asyncio.sleep(5.0)
        if tracker.idle_seconds() >= VOICE_IDLE_TIMEOUT_SECONDS:
            await websocket.close(code=4005, reason="idle_timeout")
            return


@router.websocket("/api/v1/copilot/voice")
async def copilot_voice_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    context = await _authenticate(websocket)
    if context is None:
        await websocket.close(code=4001, reason="auth_invalid")
        return

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    current_session = _ActiveVoiceSession(
        websocket=websocket, stop_event=stop_event, loop=loop
    )

    # Concurrency limit: close previous active session for this user
    with _ACTIVE_SESSIONS_LOCK:
        old_session = _ACTIVE_VOICE_SESSIONS.get(context.user_id)
        if old_session is not None and old_session.websocket is not websocket:
            def _signal_superseded(s: _ActiveVoiceSession) -> None:
                s.stop_event.set()
                asyncio.create_task(
                    s.websocket.close(code=4002, reason="session_superseded")
                )

            with suppress(Exception):
                old_session.loop.call_soon_threadsafe(_signal_superseded, old_session)
        _ACTIVE_VOICE_SESSIONS[context.user_id] = current_session

    if stop_event.is_set():
        with suppress(Exception):
            await websocket.close(code=4002, reason="session_superseded")
        return

    live = GeminiLiveSession(context)
    start_time = loop.time()
    try:
        audit_add(
            datetime.now(UTC).isoformat(),
            context.user_id,
            "copilot.voice.start",
            {"store_id": context.store_id, "role": context.user_role},
            agent_name="ag_copilot",
            controller_user_id=context.user_id,
        )
    except Exception:
        pass

    close_reason = "normal"
    tracker = ActivityTracker()
    limiter = TokenBucket(rate=MAX_MESSAGES_PER_SECOND, capacity=40.0)

    try:
        await live.open()
        if stop_event.is_set():
            close_reason = "session_superseded"
            return

        await websocket.send_json(
            {
                "event": "voice:ready",
                "data": {
                    "input_format": "pcm_s16le_16000_mono",
                    "output_format": "pcm_s16le_24000_mono",
                    "session_timeout_seconds": int(VOICE_SESSION_MAX_SECONDS),
                    "idle_timeout_seconds": int(VOICE_IDLE_TIMEOUT_SECONDS),
                },
            }
        )
        async with asyncio.timeout(VOICE_SESSION_MAX_SECONDS):
            client_task = asyncio.create_task(
                _receive_client(websocket, live, tracker, limiter)
            )
            upstream_task = asyncio.create_task(_receive_upstream(websocket, live))
            watchdog_task = asyncio.create_task(_idle_watchdog(websocket, tracker))
            stop_task = asyncio.create_task(stop_event.wait())
            tasks = {client_task, upstream_task, watchdog_task, stop_task}
            try:
                done, _ = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    if not task.cancelled():
                        task.result()
                if stop_event.is_set():
                    close_reason = "session_superseded"
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
    except VoiceSessionUnavailable as exc:
        close_reason = str(exc)
        await websocket.send_json(
            {
                "event": "voice:error",
                "data": {"code": str(exc), "fallback": "text_chat"},
            }
        )
    except TimeoutError:
        close_reason = "max_duration_reached"
        with suppress(Exception):
            await websocket.send_json(
                {
                    "event": "voice:ended",
                    "data": {"code": "max_duration_reached", "fallback": "text_chat"},
                }
            )
    except (WebSocketDisconnect, json.JSONDecodeError):
        close_reason = "client_disconnected"
    except (asyncio.CancelledError, GeneratorExit):
        close_reason = "session_superseded" if stop_event.is_set() else "cancelled"
    except Exception as exc:
        close_reason = f"upstream_error: {type(exc).__name__}"
        with suppress(Exception):
            await websocket.send_json(
                {
                    "event": "voice:error",
                    "data": {"code": "upstream_unavailable", "fallback": "text_chat"},
                }
            )
    finally:
        duration = loop.time() - start_time
        try:
            audit_add(
                datetime.now(UTC).isoformat(),
                context.user_id,
                "copilot.voice.end",
                {
                    "store_id": context.store_id,
                    "role": context.user_role,
                    "duration_seconds": round(duration, 2),
                    "reason": close_reason,
                },
                agent_name="ag_copilot",
                controller_user_id=context.user_id,
            )
        except Exception:
            pass

        with _ACTIVE_SESSIONS_LOCK:
            if _ACTIVE_VOICE_SESSIONS.get(context.user_id) is current_session:
                _ACTIVE_VOICE_SESSIONS.pop(context.user_id, None)

        await live.close()
        if close_reason == "session_superseded":
            with suppress(Exception):
                await websocket.close(code=4002, reason="session_superseded")
        else:
            with suppress(Exception):
                await websocket.close(code=1000)

