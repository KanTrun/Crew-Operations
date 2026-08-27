"""Kênh tin (Telegram/Zalo/replay) + Page quán (Facebook replay)."""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, cast

from ca_agents.ag_msg import classify
from ca_agents.llm import agent_mode
from ca_agents.messaging import (
    InboundMessage,
    get_port,
    is_xem_lich,
    parse_telegram_update,
    parse_zalo_webhook,
)
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from ca_api.interfaces.http.sprint3 import _nv_from_token, _phan_cong, _require_manager, _require_role
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
            sent = port.send(msg.external_user_id, "Mã bind không đúng hoặc đã dùng. Lấy mã mới trên /toi.")
            return {"ok": False, "ly_do": "bind_code", "message": sent.__dict__}
        sent = port.send(msg.external_user_id, f"Đã nối kênh với {nv}. Bạn có thể hỏi lịch hoặc gửi ý định ca.")
        return {"ok": True, "hanh": "bind", "nv_id": nv, "message": sent.__dict__}

    nv_id = kenh_bind_get(msg.channel, msg.external_user_id)
    if not nv_id:
        sent = port.send(
            msg.external_user_id,
            "Chưa nối tài khoản quán. Vào web NHỊP QUÁN → Ca của tôi → lấy mã bind, rồi nhắn: /bind <mã>",
        )
        return {"ok": False, "ly_do": "chua_bind", "message": sent.__dict__}

    if is_xem_lich(text):
        body = _format_lich(nv_id)
        sent = port.send(msg.external_user_id, body)
        return {"ok": True, "hanh": "xem_lich", "nv_id": nv_id, "message": sent.__dict__}

    r = classify(text, mode=agent_mode())
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
    _require_role(authorization)
    zalo_on = os.environ.get("NHIPQUAN_ZALO_ENABLED", "").strip() in {"1", "true", "yes"}
    zalo_token = bool(os.environ.get("NHIPQUAN_ZALO_OA_ACCESS_TOKEN", "").strip())
    tg_token = bool(os.environ.get("NHIPQUAN_TELEGRAM_BOT_TOKEN", "").strip())
    fb_token = bool(os.environ.get("NHIPQUAN_FB_PAGE_TOKEN", "").strip())
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
        "binds": kenh_bind_list(),
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
    _require_role(authorization)
    mode = _page_mode()
    token = bool(os.environ.get("NHIPQUAN_FB_PAGE_TOKEN", "").strip())
    return {
        "mode": mode,
        "connected": mode == "live" and token,
        "has_token": token,
        "huong_dan": "Tạo Page Facebook rồi làm theo docs/runbooks/facebook-page-connect.md — không dùng dữ liệu giả.",
    }


@router.get("/api/v1/page/threads")
def page_threads(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    doc = _page_store()
    return {"items": doc.get("threads", []), "mode": _page_mode(), "nguon": "quan"}


class PageReplyBody(BaseModel):
    text: str


@router.post("/api/v1/page/threads/{thread_id}/reply")
def page_reply(
    thread_id: str,
    body: PageReplyBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    _require_role(authorization)
    found: dict[str, Any] | None = None

    def mut(doc: dict[str, Any]) -> dict[str, Any]:
        nonlocal found
        for th in doc.get("threads", []):
            if th.get("id") == thread_id:
                replies = th.setdefault("replies", [])
                replies.append(
                    {
                        "id": f"pr_{uuid.uuid4().hex[:6]}",
                        "text": body.text.strip(),
                        "by": s["nv_id"],
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
    return {"ok": True, "thread": found, "mode": _page_mode()}


class PageDraftBody(BaseModel):
    noi_dung: str


@router.get("/api/v1/page/drafts")
def page_drafts(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
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
                    "da_dang_mock" if body.quyet_dinh == "duyet" else body.quyet_dinh
                )
                d["quyet_boi"] = role
                d["quyet_luc"] = _now()
                found = d
                break
        return doc

    kv_mutate("page_quan", mut, _page_store())
    if not found:
        raise HTTPException(status_code=404, detail="draft")
    _audit(role, "page_draft", {"id": draft_id, "q": body.quyet_dinh})
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
    _require_role(authorization)
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
