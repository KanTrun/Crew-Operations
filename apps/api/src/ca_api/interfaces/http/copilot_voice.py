"""Authenticated server-to-server WebSocket proxy for AG-COPILOT voice."""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress

from ca_agents.ag_copilot.voice_session import (
    GeminiLiveSession,
    VerifiedVoiceContext,
    VoiceSessionUnavailable,
)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ca_api.persist import session as auth_session

router = APIRouter(tags=["copilot-voice"])

AUTH_TIMEOUT_SECONDS = 5.0
SESSION_TIMEOUT_SECONDS = 600.0
MAX_TEXT_LENGTH = 2000


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
    except (TimeoutError, WebSocketDisconnect, json.JSONDecodeError):
        return None
    if not isinstance(message, dict):
        return None
    if message.get("event") != "auth" or not message.get("token"):
        return None
    return _verified_context(str(message["token"]).strip())


async def _receive_client(websocket: WebSocket, live: GeminiLiveSession) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return
        audio = message.get("bytes")
        if audio is not None:
            if audio:
                await live.send_audio(audio)
            continue

        raw = message.get("text")
        if not raw:
            continue
        payload = json.loads(raw)
        event = payload.get("event")
        if event == "stop":
            return
        if event == "text":
            text = str(payload.get("text") or "").strip()
            if text:
                await live.send_text(text[:MAX_TEXT_LENGTH])
        elif event == "interrupt":
            await websocket.send_json({"event": "voice:interrupted"})


async def _receive_upstream(websocket: WebSocket, live: GeminiLiveSession) -> None:
    while True:
        event = await live.receive()
        await websocket.send_json({"event": "voice:upstream", "data": event})


@router.websocket("/api/v1/copilot/voice")
async def copilot_voice_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    context = await _authenticate(websocket)
    if context is None:
        await websocket.close(code=4001, reason="auth_invalid")
        return

    live = GeminiLiveSession(context)
    try:
        await live.open()
        await websocket.send_json(
            {
                "event": "voice:ready",
                "data": {
                    "input_format": "pcm_s16le_16000_mono",
                    "output_format": "pcm_s16le_24000_mono",
                    "session_timeout_seconds": int(SESSION_TIMEOUT_SECONDS),
                },
            }
        )
        async with asyncio.timeout(SESSION_TIMEOUT_SECONDS):
            client_task = asyncio.create_task(_receive_client(websocket, live))
            upstream_task = asyncio.create_task(_receive_upstream(websocket, live))
            tasks = {client_task, upstream_task}
            try:
                done, _ = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    task.result()
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
    except VoiceSessionUnavailable as exc:
        await websocket.send_json(
            {
                "event": "voice:error",
                "data": {"code": str(exc), "fallback": "text_chat"},
            }
        )
    except TimeoutError:
        await websocket.send_json(
            {
                "event": "voice:error",
                "data": {"code": "session_timeout", "fallback": "text_chat"},
            }
        )
    except (WebSocketDisconnect, json.JSONDecodeError):
        pass
    except Exception:
        with suppress(Exception):
            await websocket.send_json(
                {
                    "event": "voice:error",
                    "data": {"code": "upstream_unavailable", "fallback": "text_chat"},
                }
            )
    finally:
        await live.close()
        with suppress(Exception):
            await websocket.close(code=1000)
