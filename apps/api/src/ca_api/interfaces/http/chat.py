"""Chat REST & WebSocket routes with enterprise-grade security."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc

from ca_api.persist import (
    chat_conversation_create,
    chat_conversation_get,
    chat_conversation_list_for_user,
    chat_conversation_mute,
    chat_get_or_create_direct,
    chat_message_create,
    chat_message_delete,
    chat_message_edit,
    chat_message_pin,
    chat_message_react,
    chat_messages_list,
    chat_messages_search,
    chat_read_receipts_update,
    user_is_active,
)
from ca_api.persist import (
    session as auth_session,
)
from ca_api.services.chat_ws import (
    auth_ip_limiter,
    chat_ws_manager,
    msg_rate_limiter,
    sanitize_text,
)

router = APIRouter(tags=["chat"])

ROOT = Path(__file__).resolve().parents[6]
UPLOAD_DIR = ROOT / "data" / "uploads" / "chat"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


CHAT_ENABLED = os.environ.get("CHAT_ENABLED", "true").lower() in ("true", "1", "yes")


def _check_chat_enabled() -> None:
    if not CHAT_ENABLED:
        raise HTTPException(status_code=503, detail="he_thong_chat_tam_khoa_bao_tri")


def _require_user(authorization: str | None) -> dict[str, str]:
    _check_chat_enabled()
    sess = auth_session(authorization)
    if not sess:
        raise HTTPException(status_code=401, detail="chua_dang_nhap")
    if not user_is_active(sess["nv_id"]):
        raise HTTPException(status_code=403, detail="tai_khoan_da_vo_hieu_hoa")
    return sess


class CreateConvBody(BaseModel):
    conv_type: str = Field(..., description="'direct' hoặc 'group'")
    display_name: str = ""
    participant_nv_ids: list[str] = []
    target_nv_id: str | None = None
    avatar_url: str = ""


class SendMsgBody(BaseModel):
    content: str = ""
    msg_type: str = "text"
    metadata: dict[str, Any] = {}
    reply_to_id: str | None = None


class EditMsgBody(BaseModel):
    content: str


class ReactBody(BaseModel):
    emoji: str


class MuteBody(BaseModel):
    muted: bool = True


class PinMsgBody(BaseModel):
    pinned: bool = True


# ── WebSocket Endpoint với First-Message Authentication ──────────────────────

@router.websocket("/ws/chat")
async def chat_websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    client_ip = websocket.client.host if websocket.client else "unknown"

    # 1. Kiểm tra rate limit brute-force theo IP
    if await auth_ip_limiter.is_blocked(client_ip):
        await websocket.close(code=4001, reason="ip_blocked")
        return

    # 2. Chờ tin nhắn đầu tiên phải là auth trong vòng 5 giây
    try:
        raw_first = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
        first_msg = json.loads(raw_first)
    except TimeoutError:
        await auth_ip_limiter.record_failure(client_ip)
        await websocket.close(code=4001, reason="auth_timeout")
        return
    except Exception:
        await auth_ip_limiter.record_failure(client_ip)
        await websocket.close(code=4001, reason="auth_invalid")
        return

    if first_msg.get("event") != "auth" or not first_msg.get("token"):
        await auth_ip_limiter.record_failure(client_ip)
        await websocket.close(code=4001, reason="auth_invalid")
        return

    token = str(first_msg.get("token")).strip()
    sess = auth_session(f"Bearer {token}") or auth_session(token)
    if not sess or not user_is_active(sess["nv_id"]):
        await auth_ip_limiter.record_failure(client_ip)
        await websocket.close(code=4001, reason="auth_invalid")
        return

    # Auth thành công
    await auth_ip_limiter.clear(client_ip)
    nv_id = sess["nv_id"]
    display_name = sess.get("display_name", nv_id)

    # Gửi ACK xác thực cho client
    await websocket.send_text(
        json.dumps({
            "event": "auth:ack",
            "data": {"nv_id": nv_id, "display_name": display_name, "role": sess.get("role")},
        })
    )

    # Chỉ add connection vào broadcast group SAU KHI auth thành công
    await chat_ws_manager.connect(nv_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await chat_ws_manager.handle_client_message(nv_id, websocket, data)
    except WebSocketDisconnect:
        await chat_ws_manager.disconnect(nv_id, websocket)
    except Exception:
        await chat_ws_manager.disconnect(nv_id, websocket)


# ── REST Endpoints ───────────────────────────────────────────────────────────

@router.get("/api/v1/chat/conversations")
def list_conversations(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    sess = _require_user(authorization)
    nv_id = sess["nv_id"]
    store_id = sess.get("store_id", "quan_01")
    items = chat_conversation_list_for_user(nv_id, store_id)
    return {"items": items, "unread_total": sum(c.get("unread_count", 0) for c in items)}


@router.post("/api/v1/chat/conversations")
async def create_conversation(
    body: CreateConvBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    sess = _require_user(authorization)
    nv_id = sess["nv_id"]
    store_id = sess.get("store_id", "quan_01")

    if body.conv_type == "direct":
        if not body.target_nv_id:
            raise HTTPException(status_code=422, detail="thieu_target_nv_id")
        conv = chat_get_or_create_direct(store_id, nv_id, body.target_nv_id)
        return conv

    if body.conv_type == "group":
        display_name = sanitize_text(body.display_name) or "Nhóm mới"
        conv = chat_conversation_create(
            store_id=store_id,
            conv_type="group",
            display_name=display_name,
            created_by=nv_id,
            participant_nv_ids=body.participant_nv_ids,
            is_locked=False,
            avatar_url=body.avatar_url,
        )
        await chat_ws_manager.broadcast_to_conversation(
            conv["id"],
            {"event": "conversation:created", "data": conv},
        )
        return conv

    raise HTTPException(status_code=422, detail="loai_hoi_thoai_khong_hop_le")


@router.get("/api/v1/chat/conversations/{conv_id}")
def get_conversation(
    conv_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    sess = _require_user(authorization)
    conv = chat_conversation_get(conv_id, sess["nv_id"])
    if not conv:
        raise HTTPException(status_code=404, detail="khong_tim_thay_hoi_thoai")
    return conv


@router.get("/api/v1/chat/conversations/{conv_id}/messages")
def get_messages(
    conv_id: str,
    limit: int = Query(50, ge=1, le=100),
    before_id: str | None = Query(None),
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_user(authorization)
    messages = chat_messages_list(conv_id, limit=limit, before_id=before_id)
    return {"items": messages, "limit": limit, "before_id": before_id}


async def _reply_copilot_bg(conv_id: str, prompt: str, sess: dict[str, Any]) -> None:
    try:
        from ca_agents.ag_copilot import run_copilot
        verified_context = {
            "store_id": sess.get("store_id", "quan_01"),
            "user_id": sess.get("nv_id", "system"),
            "user_role": sess.get("role", "nhan_vien"),
            "active_date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "channel": "chat",
            "recent_messages": [],
        }
        res = run_copilot(prompt, verified_context)
        reply_content = res.reply_text if res else "Tôi đã nhận được yêu cầu."
        meta: dict[str, Any] = {}
        msg_type = "text"
        if res and getattr(res, "action_proposal", None):
            msg_type = "ops_card"
            meta["proposal"] = res.action_proposal.model_dump()

        copilot_msg = chat_message_create(
            conv_id=conv_id,
            sender_id="copilot",
            content=reply_content,
            msg_type=msg_type,
            metadata=meta,
        )
        await chat_ws_manager.broadcast_to_conversation(
            conv_id,
            {"event": "message:new", "data": copilot_msg},
        )
    except Exception:
        pass


@router.post("/api/v1/chat/conversations/{conv_id}/messages")
async def send_message(
    conv_id: str,
    body: SendMsgBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    sess = _require_user(authorization)
    nv_id = sess["nv_id"]

    if not await msg_rate_limiter.check_and_record(nv_id):
        raise HTTPException(status_code=429, detail="gui_tin_qua_nhanh_toi_da_30_tin_phut")

    content = sanitize_text(body.content)
    if not content and not body.metadata.get("url"):
        raise HTTPException(status_code=422, detail="tin_nhan_rong")

    try:
        msg = chat_message_create(
            conv_id=conv_id,
            sender_id=nv_id,
            content=content,
            msg_type=body.msg_type,
            metadata=body.metadata,
            reply_to_id=body.reply_to_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    await chat_ws_manager.broadcast_to_conversation(
        conv_id,
        {"event": "message:new", "data": msg},
    )

    c_low = content.lower()
    if "@agent_lich" in c_low or "@lich" in c_low or "@xep_lich" in c_low or ("xếp lịch" in c_low and ("ai" in c_low or "bot" in c_low or "agent" in c_low or "@" in c_low)):
        from ca_api.services.chat_scheduler_agent import handle_scheduling_request
        asyncio.create_task(handle_scheduling_request(conv_id, content, sess))
    elif "@copilot" in c_low:
        prompt = content
        for prefix in ("@copilot", "@Copilot"):
            prompt = prompt.replace(prefix, "")
        asyncio.create_task(_reply_copilot_bg(conv_id, prompt.strip() or "Xin chào", sess))
    elif any(w in c_low for w in ["rảnh", "đăng ký", "em rảnh"]) and any(d in c_low for d in ["t2", "t3", "t4", "t5", "t6", "t7", "cn", "thứ"]):
        try:
            from ca_api.persist import chat_message_react
            chat_message_react(msg["id"], "ai_scheduler", "👍")
            asyncio.create_task(chat_ws_manager.broadcast_to_conversation(
                conv_id,
                {"event": "message:react", "data": {"message_id": msg["id"], "conversation_id": conv_id, "emoji": "👍", "nv_id": "ai_scheduler"}},
            ))
        except Exception:
            pass

    return msg


@router.post("/api/v1/chat/messages/{message_id}/pin")
async def pin_message(
    message_id: str,
    body: PinMsgBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    sess = _require_user(authorization)
    msg = chat_message_pin(message_id, sess["nv_id"], pinned=body.pinned)
    if not msg:
        raise HTTPException(status_code=403, detail="khong_the_ghim_tin_nhan")
    await chat_ws_manager.broadcast_to_conversation(
        msg["conversation_id"],
        {"event": "message:updated", "data": msg},
    )
    return msg


@router.patch("/api/v1/chat/messages/{message_id}")
async def edit_message(
    message_id: str,
    body: EditMsgBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    sess = _require_user(authorization)
    nv_id = sess["nv_id"]
    new_content = sanitize_text(body.content)
    if not new_content:
        raise HTTPException(status_code=422, detail="noi_dung_rong")

    msg = chat_message_edit(message_id, nv_id, new_content)
    if not msg:
        raise HTTPException(status_code=403, detail="khong_the_chinh_sua_tin_nhan")

    await chat_ws_manager.broadcast_to_conversation(
        msg["conversation_id"],
        {"event": "message:updated", "data": msg},
    )
    return msg


@router.delete("/api/v1/chat/messages/{message_id}")
async def delete_message(
    message_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    sess = _require_user(authorization)
    nv_id = sess["nv_id"]
    msg = chat_message_delete(message_id, nv_id)
    if not msg:
        raise HTTPException(status_code=403, detail="khong_co_quyen_thu_hoi")

    await chat_ws_manager.broadcast_to_conversation(
        msg["conversation_id"],
        {"event": "message:updated", "data": msg},
    )
    return msg


@router.post("/api/v1/chat/messages/{message_id}/reactions")
async def react_message(
    message_id: str,
    body: ReactBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    sess = _require_user(authorization)
    nv_id = sess["nv_id"]
    msg = chat_message_react(message_id, nv_id, body.emoji)
    if "conversation_id" in msg:
        await chat_ws_manager.broadcast_to_conversation(
            msg["conversation_id"],
            {"event": "message:updated", "data": msg},
        )
    return msg


@router.post("/api/v1/chat/conversations/{conv_id}/read")
async def mark_read(
    conv_id: str,
    message_id: str = Query(...),
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    sess = _require_user(authorization)
    nv_id = sess["nv_id"]
    receipts = chat_read_receipts_update(conv_id, nv_id, message_id)
    await chat_ws_manager.broadcast_to_conversation(
        conv_id,
        {
            "event": "message:read",
            "data": {"conversation_id": conv_id, "nv_id": nv_id, "message_id": message_id, "receipts": receipts},
        },
    )
    return {"ok": True, "receipts": receipts}


@router.post("/api/v1/chat/conversations/{conv_id}/mute")
def mute_conversation(
    conv_id: str,
    body: MuteBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    sess = _require_user(authorization)
    chat_conversation_mute(conv_id, sess["nv_id"], body.muted)
    return {"ok": True, "muted": body.muted}


@router.get("/api/v1/chat/search")
def search_messages(
    q: str = Query(..., min_length=1),
    conv_id: str | None = Query(None),
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    sess = _require_user(authorization)
    items = chat_messages_search(q, sess["nv_id"], conv_id=conv_id, store_id=sess.get("store_id", "quan_01"))
    return {"items": items, "query": q}


@router.get("/api/v1/chat/online")
def get_online_users(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_user(authorization)
    return {"online_users": chat_ws_manager.get_online_users()}


# ── File Upload với Magic Bytes Validation ───────────────────────────────────

# Magic bytes signature cho các định dạng an toàn
MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),       # Sẽ check thêm WEBP ở offset 8
    (b"%PDF-", "application/pdf"),
    (b"\x1a\x45\xdf\xa3", "video/webm"),  # WebM / Matroska (Audio/Voice)
    (b"OggS", "audio/ogg"),
    (b"ID3", "audio/mpeg"),
]

def validate_magic_bytes(header: bytes) -> bool:
    """Xác thực định dạng thực tế của file thông qua header bytes."""
    for sig, _mime in MAGIC_SIGNATURES:
        if header.startswith(sig):
            if sig == b"RIFF":
                # Check WEBP hoặc WAVE
                return b"WEBP" in header[:16] or b"WAVE" in header[:16]
            return True
    return False


@router.post("/api/v1/chat/upload")
async def upload_chat_media(
    file: UploadFile = File(...),
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_user(authorization)

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="tep_qua_lon_toi_da_15mb")

    # Kiểm tra magic bytes
    if not validate_magic_bytes(content[:32]):
        raise HTTPException(status_code=415, detail="dinh_dang_tep_khong_hop_le_hoac_nguy_hiem")

    original_filename = file.filename or "media"
    ext = os.path.splitext(original_filename)[1].lower()
    if not ext:
        if file.content_type and "audio" in file.content_type:
            ext = ".webm"
        elif file.content_type and "image" in file.content_type:
            ext = ".jpg"
        else:
            ext = ".bin"

    safe_filename = f"{uuid.uuid4().hex}{ext}"
    dest_path = UPLOAD_DIR / safe_filename
    with open(dest_path, "wb") as f:
        f.write(content)

    return {
        "url": f"/api/v1/chat/uploads/{safe_filename}",
        "filename": sanitize_text(original_filename),
        "size": len(content),
        "mime_type": file.content_type or "application/octet-stream",
    }


@router.get("/api/v1/chat/uploads/{filename}")
def serve_chat_media(filename: str) -> FileResponse:
    safe_name = os.path.basename(filename)
    path = UPLOAD_DIR / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="khong_tim_thay_tep")
    return FileResponse(path)
