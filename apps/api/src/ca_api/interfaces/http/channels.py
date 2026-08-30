"""Kênh tin (Telegram/Zalo/replay) + Page quán (Facebook replay)."""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, cast

from ca_agents.ag_fbpage import (
    FBMessageInput,
    FBMessageOutput,
    process_fb_message,
)
from ca_agents.ag_msg import classify
from ca_agents.facebook_page import (
    fetch_conversations,
    is_within_24h_window,
    page_health,
    publish_page_post,
    send_messenger_text,
    upsert_thread_from_messaging,
    verify_fb_webhook_signature,
)
from ca_agents.llm import agent_mode
from ca_agents.messaging import (
    InboundMessage,
    get_port,
    is_xem_lich,
    parse_telegram_update,
    parse_zalo_webhook,
    should_enqueue_constraint,
)
from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ca_api.interfaces.http.sprint3 import (
    _nv_from_token,
    _phan_cong,
    _require_manager,
)
from ca_api.persist import (
    audit_add,
    kenh_bind_code_consume,
    kenh_bind_code_issue,
    kenh_bind_get,
    kenh_bind_list,
    kenh_bind_set,
    kv_get,
    kv_mutate,
    kv_set,
)
from ca_api.persist import session as auth_session
from ca_api.services.store_public_context import (
    get_active_promotions,
    get_public_menu,
    get_store_profile,
    set_active_promotions,
    set_store_profile,
)

UTC = UTC
router = APIRouter()
ROOT = Path(__file__).resolve().parents[6]
SEED = ROOT / "data" / "seed" / "sample.json"
PAGE_FIXTURE = ROOT / "data" / "golden" / "page" / "threads_01.json"


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _audit(ai: str, hanh: str, payload: dict[str, Any]) -> None:
    audit_add(_now(), ai, hanh, payload)


# ── Bind ──────────────────────────────────────────────────────────────────


class BindIssueOut(BaseModel):
    code: str
    huong_dan: str


@router.post("/api/v1/channels/bind/issue")
def bind_issue(authorization: Annotated[str | None, Header()] = None) -> dict[str, str]:
    nv = _nv_from_token(authorization)
    code = kenh_bind_code_issue(nv)
    return {
        "code": code,
        "huong_dan": (
            f"Ưu tiên Zalo OA — nhắn đúng một dòng: /bind {code}. "
            f"Telegram (nếu có bot): cùng lệnh /bind {code}."
        ),
        "nv_id": nv,
    }


class BindManualBody(BaseModel):
    channel: str = "telegram"
    external_user_id: str
    nv_id: str


@router.post("/api/v1/channels/bind")
def bind_manual(
    body: BindManualBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    kenh_bind_set(body.channel, body.external_user_id, body.nv_id)
    _audit(role, "kenh_bind", body.model_dump())
    return {"ok": True, **body.model_dump()}


@router.get("/api/v1/channels/bind")
def bind_list(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    if s["role"] in {"quan_ly", "chu_quan"}:
        return {"items": kenh_bind_list()}
    return {"items": kenh_bind_list(s["nv_id"])}


# ── Inbound process ───────────────────────────────────────────────────────


def _format_lich(nv_id: str) -> str:
    phan = _phan_cong()
    seed = json.loads(SEED.read_text(encoding="utf-8")) if SEED.exists() else {}
    meta = {c["id"]: c for c in seed.get("ca_mau_21", [])}
    thu = {1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"}
    mine = [cid for cid, nvs in phan.items() if nv_id in nvs]
    if not mine:
        return f"Lịch của bạn ({nv_id}): chưa có ca nào trong tuần này."
    lines = [f"Lịch ca của bạn ({nv_id}):"]
    for cid in mine[:12]:
        m = meta.get(cid, {})
        lines.append(
            f"- {thu.get(int(m.get('ngay_offset', 1)), 'T2')} "
            f"{m.get('bat_dau', '?')}–{m.get('ket_thuc', '?')} "
            f"{m.get('vi_tri', '')} ({cid})"
        )
    return "\n".join(lines)


def _enqueue_inbox(
    *,
    text: str,
    intent: str,
    do_tin_cay: float,
    channel: str,
    nv_id: str,
    external_user_id: str,
    rang_buoc: dict[str, str],
) -> dict[str, Any]:
    item = {
        "id": f"in_ch_{uuid.uuid4().hex[:8]}",
        "agent": "ag_msg",
        "tom_tat": text.strip()[:200],
        "trang_thai": "cho_duyet",
        "nguon": channel,
        "y_dinh": intent,
        "do_tin_cay": do_tin_cay,
        "noi_dung_goc": text,
        "nv_id": nv_id,
        "channel_user_id": external_user_id,
        "rang_buoc": rang_buoc,
        "created_at": _now(),
    }

    def mut(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items.insert(0, item)
        return items

    # Không gọi _seed_inbox trước — tránh ghi đè fixture nếu kv trống trong test
    # khi đã có mục kênh. Seed chỉ khi list rỗng ở GET.
    existing = kv_get("inbox_rang_buoc", None)
    if existing is None:
        kv_set("inbox_rang_buoc", [item])
    else:
        kv_mutate("inbox_rang_buoc", mut, [])
    return item


def process_inbound(msg: InboundMessage, *, reply_backend: str | None = None) -> dict[str, Any]:
    """Xử lý một tin: bind → xem lịch | classify → inbox."""
    port = get_port(reply_backend or msg.channel)
    text = msg.text.strip()
    bind_m = re.match(r"^/bind\s+([a-z0-9]{6,16})$", text, re.I)
    if bind_m:
        nv = kenh_bind_code_consume(bind_m.group(1), msg.channel, msg.external_user_id)
        if not nv:
            sent = port.send(
                msg.external_user_id,
                "Mã bind không đúng hoặc đã dùng. Lấy mã mới trên /toi.",
            )
            return {"ok": False, "ly_do": "bind_code", "message": sent.__dict__}
        sent = port.send(
            msg.external_user_id,
            f"Đã nối kênh với {nv}. Bạn có thể hỏi lịch hoặc gửi ý định ca.",
        )
        return {"ok": True, "hanh": "bind", "nv_id": nv, "message": sent.__dict__}

    nv_id = kenh_bind_get(msg.channel, msg.external_user_id)
    if not nv_id:
        sent = port.send(
            msg.external_user_id,
            "Chưa nối tài khoản quán. Vào web NHỊP QUÁN → Ca của tôi → lấy mã bind, "
            "rồi nhắn: /bind <mã>",
        )
        return {"ok": False, "ly_do": "chua_bind", "message": sent.__dict__}

    if is_xem_lich(text):
        body = _format_lich(nv_id)
        sent = port.send(msg.external_user_id, body)
        return {"ok": True, "hanh": "xem_lich", "nv_id": nv_id, "message": sent.__dict__}

    r = classify(text, mode=agent_mode())
    if not should_enqueue_constraint(text, r.intent, r.do_tin_cay):
        sent = port.send(
            msg.external_user_id,
            "Đã nhận tin. Đây không phải ràng buộc ca — nhắn xin nghỉ / đổi ca / cập nhật TKB "
            "hoặc «xem lịch» nếu cần.",
        )
        return {
            "ok": True,
            "hanh": "bo_qua",
            "intent": r.intent,
            "nv_id": nv_id,
            "message": sent.__dict__,
        }
    item = _enqueue_inbox(
        text=text,
        intent=r.intent,
        do_tin_cay=r.do_tin_cay,
        channel=msg.channel,
        nv_id=nv_id,
        external_user_id=msg.external_user_id,
        rang_buoc=dict(r.rang_buoc),
    )
    sent = port.send(
        msg.external_user_id,
        f"Đã ghi nhận ý định «{r.intent}» — quản lý sẽ duyệt trên hộp thư ràng buộc.",
    )
    return {"ok": True, "hanh": "enqueue", "item": item, "message": sent.__dict__}


class ReplayBody(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    backend: str = "replay"


@router.get("/api/v1/channels/status")
def channels_status(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    """Trạng thái nối kênh thật — UI dùng để hiện 'Chưa nối', không giả lập."""
    caller = auth_session(authorization)
    if not caller:
        raise HTTPException(status_code=401, detail="thieu_token")
    zalo_on = os.environ.get("NHIPQUAN_ZALO_ENABLED", "").strip() in {"1", "true", "yes"}
    zalo_token = bool(os.environ.get("NHIPQUAN_ZALO_OA_ACCESS_TOKEN", "").strip())
    tg_token = bool(os.environ.get("NHIPQUAN_TELEGRAM_BOT_TOKEN", "").strip())
    fb_token = bool(os.environ.get("NHIPQUAN_FB_PAGE_TOKEN", "").strip())
    binds = (
        kenh_bind_list()
        if caller["role"] in {"quan_ly", "chu_quan"}
        else kenh_bind_list(caller["nv_id"])
    )
    return {
        "uu_tien": ["zalo", "telegram", "facebook"],
        "agent_mode": agent_mode(),
        "zalo": {
            "enabled_flag": zalo_on,
            "connected": zalo_on and zalo_token,
            "huong_dan": "docs/runbooks/zalo-oa-connect.md",
        },
        "telegram": {
            "connected": tg_token,
            "huong_dan": "docs/runbooks/telegram-bot-connect.md",
        },
        "facebook": {
            "connected": fb_token,
            "huong_dan": "docs/runbooks/facebook-page-connect.md",
        },
        "binds": binds,
    }


@router.post("/api/v1/channels/replay")
def channels_replay(
    body: ReplayBody | None = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Chỉ cho CI/test — không dùng làm dữ liệu quán thật."""
    _require_manager(authorization)
    if os.environ.get("NHIPQUAN_ALLOW_MSG_REPLAY", "").strip() not in {"1", "true", "yes"}:
        raise HTTPException(
            status_code=403,
            detail="replay_tat — bật NHIPQUAN_ALLOW_MSG_REPLAY=1 chỉ khi chạy test",
        )
    b = body or ReplayBody()
    port = get_port("replay")
    results = []
    for i, msg in enumerate(port.receive_iter()):
        if i >= b.limit:
            break
        results.append(process_inbound(msg, reply_backend=b.backend))
    return {"ok": True, "n": len(results), "results": results}


@router.post("/api/v1/channels/telegram/webhook")
async def telegram_webhook(request: Request) -> dict[str, Any]:
    secret = os.environ.get("NHIPQUAN_TELEGRAM_WEBHOOK_SECRET", "").strip()
    if secret:
        got = request.headers.get("x-telegram-bot-api-secret-token", "")
        if got != secret:
            raise HTTPException(status_code=403, detail="webhook_secret")
    payload = await request.json()
    msg = parse_telegram_update(payload if isinstance(payload, dict) else {})
    if not msg:
        return {"ok": True, "ignored": True}
    return process_inbound(msg, reply_backend="telegram")


@router.post("/api/v1/channels/zalo/webhook")
async def zalo_webhook(request: Request) -> dict[str, Any]:
    """Webhook OA Zalo — kênh ưu tiên tại VN. Cần NHIPQUAN_ZALO_ENABLED=1 + token."""
    if os.environ.get("NHIPQUAN_ZALO_ENABLED", "").strip() not in {"1", "true", "yes"}:
        return {"ok": False, "detail": "chua_bat_zalo — xem docs/runbooks/zalo-oa-connect.md"}
    if not os.environ.get("NHIPQUAN_ZALO_OA_ACCESS_TOKEN", "").strip():
        return {"ok": False, "detail": "thieu_zalo_token"}
    payload = await request.json()
    msg = parse_zalo_webhook(payload if isinstance(payload, dict) else {})
    if not msg:
        return {"ok": True, "ignored": True}
    return process_inbound(msg, reply_backend="zalo")


# ── Page quán (Facebook replay) ────────────────────────────────────────────


def _page_store() -> dict[str, Any]:
    """Store trống theo mặc định — không nhồi fixture làm dữ liệu quán.

    Chỉ seed file golden khi `NHIPQUAN_PAGE_SEED_FIXTURE=1` (CI).
    """
    stored = kv_get("page_quan", None)
    if stored:
        return cast(dict[str, Any], stored)
    seed = os.environ.get("NHIPQUAN_PAGE_SEED_FIXTURE", "").strip() in {"1", "true", "yes"}
    if seed and PAGE_FIXTURE.exists():
        data = json.loads(PAGE_FIXTURE.read_text(encoding="utf-8"))
    else:
        data = {"threads": [], "drafts": [], "mode": "disconnected"}
    data.setdefault("mode", "disconnected")
    data.setdefault("threads", [])
    data.setdefault("drafts", [])
    kv_set("page_quan", data)
    return data


def _page_mode() -> str:
    env = os.environ.get("NHIPQUAN_PAGE_MODE", "").strip().lower()
    if env in {"live", "disconnected"}:
        return env
    token = bool(os.environ.get("NHIPQUAN_FB_PAGE_TOKEN", "").strip())
    if token and env == "live":
        return "live"
    if token:
        return "live"
    return "disconnected"


@router.get("/api/v1/page/status")
def page_status(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_manager(authorization)
    mode = _page_mode()
    token = bool(os.environ.get("NHIPQUAN_FB_PAGE_TOKEN", "").strip())
    page_id = os.environ.get("NHIPQUAN_FB_PAGE_ID", "").strip()
    health: dict[str, Any] = {"ok": False, "detail": "chua_goi"}
    if mode == "live" and token and page_id:
        health = page_health()
    connected = mode == "live" and token and bool(health.get("ok"))
    return {
        "mode": mode,
        "connected": connected,
        "has_token": token,
        "page_id": page_id or None,
        "page_name": health.get("page_name") if health.get("ok") else None,
        "graph_ok": bool(health.get("ok")),
        "graph_detail": None if health.get("ok") else health.get("detail"),
        "huong_dan": (
            "Tạo Page Facebook rồi làm theo docs/runbooks/facebook-page-connect.md "
            "— không dùng dữ liệu giả."
        ),
    }


@router.post("/api/v1/page/sync")
def page_sync(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    """Kéo hội thoại Messenger thật từ Graph vào store Page quán."""
    _require_manager(authorization)
    if _page_mode() != "live" or not os.environ.get("NHIPQUAN_FB_PAGE_TOKEN", "").strip():
        raise HTTPException(status_code=400, detail="page_chua_live")
    try:
        threads = fetch_conversations(limit=20)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)[:180]) from e

    def mut(doc: dict[str, Any]) -> dict[str, Any]:
        by_id = {t.get("id"): t for t in doc.get("threads", []) if t.get("id")}
        for th in threads:
            by_id[th["id"]] = th
        doc["threads"] = list(by_id.values())
        doc["mode"] = "live"
        return doc

    kv_mutate("page_quan", mut, _page_store())
    return {"ok": True, "n": len(threads), "mode": "live"}


@router.api_route("/api/v1/channels/facebook/webhook", methods=["GET", "POST"])
async def facebook_webhook(request: Request) -> Any:
    """Meta webhook: GET verify challenge; POST Messenger events → AG-FBPAGE processing."""
    if request.method == "GET":
        mode = request.query_params.get("hub.mode", "")
        token = request.query_params.get("hub.verify_token", "")
        challenge = request.query_params.get("hub.challenge", "")
        expected = os.environ.get("NHIPQUAN_FB_WEBHOOK_VERIFY", "").strip()
        if mode == "subscribe" and expected and token == expected and challenge:
            return Response(content=challenge, media_type="text/plain")
        raise HTTPException(status_code=403, detail="verify_fail")

    body_bytes = await request.body()
    sig_header = request.headers.get("x-hub-signature-256", "")
    if not verify_fb_webhook_signature(body_bytes, sig_header):
        raise HTTPException(status_code=403, detail="invalid_signature")

    if _page_mode() != "live" or not os.environ.get("NHIPQUAN_FB_PAGE_TOKEN", "").strip():
        return {"ok": False, "detail": "page_chua_live"}

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        return {"ok": True, "ignored": True}

    if not isinstance(payload, dict):
        return {"ok": True, "ignored": True}

    public_ctx = {
        "profile": get_store_profile(),
        "menu": get_public_menu(),
        "promotions": get_active_promotions(),
    }

    n = 0
    for entry in payload.get("entry") or []:
        for ev in entry.get("messaging") or []:
            sender = ((ev.get("sender") or {}).get("id")) or ""
            msg = ev.get("message") or {}
            text = (msg.get("text") or "").strip()
            if not sender or not text:
                continue

            mid = str(msg.get("mid") or "")
            ts = float(ev.get("timestamp") or 0)
            input_msg = FBMessageInput(psid=sender, text=text, message_id=mid, timestamp=ts)

            # Xử lý tin nhắn qua AG-FBPAGE với Guardrails và Ngưỡng tin cậy
            out: FBMessageOutput = await process_fb_message(
                input_msg,
                auto_respond_enabled=True,
                public_context=public_ctx,
            )

            th = upsert_thread_from_messaging(sender, text, mid)
            th["intent"] = out.intent
            th["confidence"] = out.confidence
            th["suggested_reply"] = out.suggested_reply
            th["pending_approval"] = out.action == "queue_to_inbox"
            th["last_message_ts"] = ts
            th["is_within_24h"] = is_within_24h_window(ts)

            if out.action == "auto_respond" and out.response:
                bot_reply = {
                    "id": f"bot_{uuid.uuid4().hex[:6]}",
                    "text": out.response,
                    "by": "Chatbot (Tự động)",
                    "at": _now(),
                    "mock": False,
                }
                th.setdefault("replies", []).append(bot_reply)
                if _page_mode() == "live":
                    try:
                        send_messenger_text(sender, out.response)
                    except Exception:
                        pass

            def mut(doc: dict[str, Any], thread: dict[str, Any] = th) -> dict[str, Any]:
                threads = doc.setdefault("threads", [])
                existing = next((t for t in threads if t.get("id") == thread["id"]), None)
                if existing:
                    existing["tom_tat"] = thread["tom_tat"]
                    existing.setdefault("replies", []).extend(thread.get("replies") or [])
                    existing["psid"] = thread.get("psid")
                    existing["intent"] = thread.get("intent")
                    existing["confidence"] = thread.get("confidence")
                    existing["suggested_reply"] = thread.get("suggested_reply")
                    existing["pending_approval"] = thread.get("pending_approval")
                    existing["last_message_ts"] = thread.get("last_message_ts")
                    existing["is_within_24h"] = thread.get("is_within_24h")
                else:
                    threads.insert(0, thread)
                doc["mode"] = "live"
                return doc

            kv_mutate("page_quan", mut, _page_store())
            n += 1
    return {"ok": True, "n": n}


@router.get("/api/v1/page/threads")
def page_threads(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_manager(authorization)
    doc = _page_store()
    threads = doc.get("threads", [])
    # Update is_within_24h dynamic flag
    for t in threads:
        t["is_within_24h"] = is_within_24h_window(t.get("last_message_ts"))
    return {"items": threads, "mode": _page_mode(), "nguon": "quan"}


class PageReplyBody(BaseModel):
    text: str
    tag: str | None = None


@router.post("/api/v1/page/threads/{thread_id}/reply")
def page_reply(
    thread_id: str,
    body: PageReplyBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    _require_manager(authorization)
    found: dict[str, Any] | None = None

    def mut(doc: dict[str, Any]) -> dict[str, Any]:
        nonlocal found
        for th in doc.get("threads", []):
            if th.get("id") == thread_id:
                th["pending_approval"] = False
                replies = th.setdefault("replies", [])
                replies.append(
                    {
                        "id": f"pr_{uuid.uuid4().hex[:6]}",
                        "text": body.text.strip(),
                        "by": s.get("display_name", s["nv_id"]),
                        "at": _now(),
                        "mock": _page_mode() != "live",
                    }
                )
                found = th
                break
        return doc

    kv_mutate("page_quan", mut, _page_store())
    if not found:
        raise HTTPException(status_code=404, detail="thread")
    graph_sent = False
    if _page_mode() == "live":
        psid = str(found.get("psid") or "")
        if psid:
            try:
                tag = body.tag
                if not tag and not is_within_24h_window(found.get("last_message_ts")):
                    tag = "CONFIRMED_EVENT_UPDATE"
                send_messenger_text(psid, body.text.strip(), tag=tag)
                graph_sent = True
            except RuntimeError as e:
                raise HTTPException(status_code=502, detail=str(e)[:180]) from e

    _audit(
        s["nv_id"],
        "page_reply",
        {"thread_id": thread_id, "text": body.text.strip(), "graph_sent": graph_sent},
    )
    return {"ok": True, "thread": found, "mode": _page_mode(), "graph_sent": graph_sent}


class PageThreadApproveBody(BaseModel):
    final_reply: str
    tag: str | None = None


@router.post("/api/v1/page/threads/{thread_id}/approve")
def page_thread_approve(
    thread_id: str,
    body: PageThreadApproveBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Quản lý duyệt câu trả lời gợi ý của bot hoặc sửa câu trả lời trước khi gửi."""
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    _require_manager(authorization)
    found: dict[str, Any] | None = None
    suggested_orig: str = ""

    def mut(doc: dict[str, Any]) -> dict[str, Any]:
        nonlocal found, suggested_orig
        for th in doc.get("threads", []):
            if th.get("id") == thread_id:
                suggested_orig = str(th.get("suggested_reply") or "")
                th["pending_approval"] = False
                replies = th.setdefault("replies", [])
                replies.append(
                    {
                        "id": f"pr_{uuid.uuid4().hex[:6]}",
                        "text": body.final_reply.strip(),
                        "by": f"Quản lý {s.get('display_name', s['nv_id'])} (Đã duyệt)",
                        "at": _now(),
                        "mock": _page_mode() != "live",
                    }
                )
                found = th
                break
        return doc

    kv_mutate("page_quan", mut, _page_store())
    if not found:
        raise HTTPException(status_code=404, detail="thread")

    graph_sent = False
    if _page_mode() == "live":
        psid = str(found.get("psid") or "")
        if psid:
            try:
                tag = body.tag
                if not tag and not is_within_24h_window(found.get("last_message_ts")):
                    tag = "CONFIRMED_EVENT_UPDATE"
                send_messenger_text(psid, body.final_reply.strip(), tag=tag)
                graph_sent = True
            except RuntimeError as e:
                raise HTTPException(status_code=502, detail=str(e)[:180]) from e

    # Audit log with diff tracking
    _audit(
        s["nv_id"],
        "page_thread_approve",
        {
            "thread_id": thread_id,
            "suggested": suggested_orig,
            "final": body.final_reply.strip(),
            "diff_detected": suggested_orig.strip() != body.final_reply.strip(),
            "graph_sent": graph_sent,
        },
    )
    return {"ok": True, "thread": found, "graph_sent": graph_sent}


@router.get("/api/v1/store/profile")
def get_profile() -> dict[str, Any]:
    return get_store_profile()


@router.put("/api/v1/store/profile")
def update_profile(
    data: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    set_store_profile(data)
    _audit(role, "store_profile_update", data)
    return {"ok": True, "profile": get_store_profile()}


@router.get("/api/v1/store/promotions")
def get_promos() -> list[dict[str, Any]]:
    return get_active_promotions()


@router.put("/api/v1/store/promotions")
def update_promos(
    promotions: list[dict[str, Any]],
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    set_active_promotions(promotions)
    _audit(role, "store_promotions_update", {"count": len(promotions)})
    return {"ok": True, "promotions": get_active_promotions()}


class PageDraftBody(BaseModel):
    noi_dung: str


@router.get("/api/v1/page/drafts")
def page_drafts(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_manager(authorization)
    return {"items": _page_store().get("drafts", []), "mode": _page_mode()}


@router.post("/api/v1/page/drafts")
def page_draft_create(
    body: PageDraftBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    item = {
        "id": f"pd_{uuid.uuid4().hex[:8]}",
        "noi_dung": body.noi_dung.strip(),
        "trang_thai": "nhap",
        "by": role,
        "at": _now(),
    }

    def mut(doc: dict[str, Any]) -> dict[str, Any]:
        doc.setdefault("drafts", []).insert(0, item)
        return doc

    kv_mutate("page_quan", mut, _page_store())
    return item


class PageDraftDecideBody(BaseModel):
    quyet_dinh: str  # cho_duyet | duyet | tu_choi


@router.post("/api/v1/page/drafts/{draft_id}")
def page_draft_decide(
    draft_id: str,
    body: PageDraftDecideBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    if body.quyet_dinh not in {"cho_duyet", "duyet", "tu_choi"}:
        raise HTTPException(status_code=400, detail="quyet_dinh")
    found: dict[str, Any] | None = None

    def mut(doc: dict[str, Any]) -> dict[str, Any]:
        nonlocal found
        for d in doc.get("drafts", []):
            if d.get("id") == draft_id:
                d["trang_thai"] = (
                    ("da_dang" if _page_mode() == "live" else "da_dang_mock")
                    if body.quyet_dinh == "duyet"
                    else body.quyet_dinh
                )
                d["quyet_boi"] = role
                d["quyet_luc"] = _now()
                found = d
                break
        return doc

    kv_mutate("page_quan", mut, _page_store())
    if not found:
        raise HTTPException(status_code=404, detail="draft")
    graph_post_id = None
    if body.quyet_dinh == "duyet" and _page_mode() == "live":
        try:
            pub = publish_page_post(str(found.get("noi_dung") or ""))
            graph_post_id = pub.get("id")

            def mark(doc: dict[str, Any]) -> dict[str, Any]:
                for d in doc.get("drafts", []):
                    if d.get("id") == draft_id:
                        d["trang_thai"] = "da_dang"
                        d["graph_post_id"] = graph_post_id
                        break
                return doc

            kv_mutate("page_quan", mark, _page_store())
            found = {**found, "trang_thai": "da_dang", "graph_post_id": graph_post_id}
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e)[:180]) from e
    _audit(
        role,
        "page_draft",
        {
            "id": draft_id,
            "q": body.quyet_dinh,
            "graph_post_id": graph_post_id,
        },
    )
    return found


class TreoFromThreadBody(BaseModel):
    thread_id: str
    ghi_chu: str = ""


@router.post("/api/v1/page/treo")
def page_treo(
    body: TreoFromThreadBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Cầu nối ops: thread page → việc treo (không CRM)."""
    _require_manager(authorization)
    doc = _page_store()
    th = next((t for t in doc.get("threads", []) if t.get("id") == body.thread_id), None)
    if not th:
        raise HTTPException(status_code=404, detail="thread")
    item = {
        "id": f"tr_pg_{uuid.uuid4().hex[:8]}",
        "mo_ta": body.ghi_chu or f"Từ page: {th.get('tom_tat', th.get('id'))}",
        "trang_thai": "dang_cho",
        "nguon": "page_quan",
        "thread_id": body.thread_id,
        "created_at": _now(),
    }

    def mut(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items.insert(0, item)
        return items

    kv_mutate("treo", mut, [])
    return item
