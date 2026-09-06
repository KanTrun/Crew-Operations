"""Kênh tin (Telegram/Zalo/replay) + Page quán (Facebook replay)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc
from pathlib import Path
from typing import Annotated, Any, cast

from ca_agents.ag_fbpage import (
    FBMessageInput,
    FBMessageOutput,
    process_fb_message,
)
from ca_agents.ag_fbpage_memory import extract_cskh_golden_pair
from ca_agents.ag_msg import classify
from ca_agents.ag_supervisor import run_nightly_cskh_reflection
from ca_agents.customer_memory import (
    extract_customer_preferences,
    merge_customer_profile,
)
from ca_agents.facebook_page import (
    fetch_conversations,
    is_within_24h_window,
    page_health,
    publish_page_post,
    reply_to_comment,
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
from ca_contracts import AIEvaluation, AIFeedbackEvent, AIGenerationRecord
from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ca_api.ai_learning.operations import circuit_breaker_open
from ca_api.ai_learning.repository import AILearningRepository
from ca_api.ai_learning.rollout import select_active_rules
from ca_api.interfaces.http.sprint3 import (
    _nv_from_token,
    _phan_cong,
    _require_manager,
)
from ca_api.persist import (
    audit_add,
    fb_escalation_add,
    fb_review_decide,
    fb_review_finalize_claim,
    fb_review_get,
    fb_review_link_generation,
    fb_review_list,
    fb_review_release_claim,
    fb_review_transition_pending,
    fb_stats,
    fb_try_claim_event,
    fb_try_claim_scoped_event,
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
from ca_api.services.fb_moderation import moderate_fb_message, queue_fb_non_text
from ca_api.services.store_public_context import (
    get_active_promotions,
    get_public_menu,
    get_store_profile,
    set_active_promotions,
    set_store_profile,
)

router = APIRouter()
LOG = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[6]
SEED = ROOT / "data" / "seed" / "sample.json"
PAGE_FIXTURE = ROOT / "data" / "golden" / "page" / "threads_01.json"


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _audit(ai: str, hanh: str, payload: dict[str, Any]) -> None:
    audit_add(_now(), ai, hanh, payload)

def _record_fb_feedback(
    *, store_id: str, conversation_id: str, feedback_type: str, original: str = "",
    final: str = "", actor_user_id: str | None = None, actor_role: str = "quan_ly",
    send_status: str = "not_applicable", failure_code: str | None = None, generation_id: str | None = None,
) -> None:
    """Persist feedback only when the source generation is explicitly known."""
    if not generation_id:
        LOG.warning(
            "facebook learning feedback skipped without generation_id: type=%s conversation=%s",
            feedback_type,
            conversation_id,
        )
        return
    try:
        repository = AILearningRepository()
        generation = next(
            (item for item in repository.list("generation", store_id=store_id, limit=200) if item.get("id") == generation_id),
            None,
        )
        if not generation:
            return
        fingerprint = hashlib.sha256(
            f"{generation['id']}:{feedback_type}:{final}:{send_status}".encode()
        ).hexdigest()
        repository.save(AIFeedbackEvent(
            id=f"fb-feedback-{fingerprint[:24]}", store_id=store_id, generation_id=str(generation["id"]),
            channel="facebook", type=feedback_type, original={"body": original} if original else None,
            final={"body": final} if final else None,
            edited_fields=["body"] if original and final and original != final else [],
            materially_edited=bool(original and final and original != final), actor_user_id=actor_user_id,
            actor_role=actor_role, send_status=send_status, failure_code=failure_code,
            idempotency_key=f"fb-feedback:{fingerprint}", created_at=_now(),
        ))
    except Exception:
        LOG.exception("facebook learning feedback persistence failed")


def _customer_negative_signal(text: str) -> bool:
    """Use a deliberately small, explainable negative-signal vocabulary."""
    normalized = " ".join(text.lower().split())
    return any(term in normalized for term in ("không hài lòng", "that vong", "tệ quá", "quá tệ", "bực mình", "không đúng"))


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
        "can_xac_minh": bool(rang_buoc.get("can_xac_minh") or do_tin_cay < 0.7),
        "doi_tac_khong_ro": bool(rang_buoc.get("doi_tac_khong_ro", False)),
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

    staff_list: list[dict[str, str]] = []
    try:
        from ca_api.persist import list_users
        users = list_users()
        staff_list = [
            {
                "id": u.get("nv_id") or u.get("username", ""),
                "ten": u.get("display_name") or u.get("username", ""),
            }
            for u in users
        ]
    except Exception:
        pass

    r = classify(text, mode=agent_mode(), staff=staff_list if staff_list else None)
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
    return cast(dict[str, Any], data)


def _page_mode() -> str:
    env = os.environ.get("NHIPQUAN_PAGE_MODE", "").strip().lower()
    if env in {"live", "disconnected"}:
        return env
    token = bool(os.environ.get("NHIPQUAN_FB_PAGE_TOKEN", "").strip())
    if token:
        return "live"
    return "disconnected"


def _fb_auto_send_enabled() -> bool:
    """Feature flag — delegate về service (single source of truth, §5.5)."""
    from ca_api.services.fb_moderation import fb_auto_send_enabled

    return fb_auto_send_enabled()


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
    page_id_cfg = os.environ.get("NHIPQUAN_FB_PAGE_ID", "").strip()
    for entry in payload.get("entry") or []:
        # L0a — chỉ nhận entry đúng Page cấu hình (kế hoạch §6.3.5); thiếu id → cho qua (tương thích ngược)
        if page_id_cfg and entry.get("id") and str(entry.get("id")) != page_id_cfg:
            continue
        for ev in entry.get("messaging") or []:
            sender = ((ev.get("sender") or {}).get("id")) or ""
            msg = ev.get("message") or {}
            # L0b — lọc echo: tin do chính Page/bot gửi → tránh vòng lặp (§6.2a)
            if msg.get("is_echo"):
                continue
            text = (msg.get("text") or "").strip()
            postback = ev.get("postback") or {}
            attachments = msg.get("attachments") or []
            if not sender:
                continue

            if not text and (attachments or postback):
                if postback:
                    title = str(postback.get("title") or "lựa chọn nhanh").strip()
                    text = f"[Khách chọn: {title}]"
                    event_id = str(postback.get("mid") or f"postback:{sender}:{ev.get('timestamp')}:{postback.get('payload')}")
                else:
                    attachment_type = str((attachments[0] or {}).get("type") or "tệp")
                    attachment_labels = {"image": "ảnh", "audio": "âm thanh", "video": "video", "file": "tệp"}
                    text = f"[Khách gửi {attachment_labels.get(attachment_type, 'tệp đính kèm')}]"
                    event_id = str(msg.get("mid") or f"attachment:{sender}:{ev.get('timestamp')}")
                if not fb_try_claim_event(event_id):
                    continue
                queue_fb_non_text(psid=sender, event_id=event_id, description=text)
                n += 1
                continue

            # read / delivery và message không có nội dung → bỏ qua, không classify
            if not text:
                continue

            mid = str(msg.get("mid") or "").strip()
            # L0c — idempotency chống webhook retry (§6.2b)
            # Không dùng timestamp fallback: event thiếu ID không được vào pipeline.
            page_id = str(entry.get("id") or page_id_cfg).strip()
            if not mid or not page_id:
                continue
            store_id = "quan_01"
            if not fb_try_claim_scoped_event(
                store_id=store_id,
                page_id=page_id,
                event_type="messaging",
                external_event_id=mid,
            ):
                continue
            ts = float(ev.get("timestamp") or 0)

            # L1–L5 — moderation pipeline (policy engine + review queue)
            moderation = moderate_fb_message(
                psid=sender,
                text=text,
                message_id=mid,
                timestamp=ts,
                public_context=public_ctx,
            )
            action = moderation.get("action", "")
            # Block: không trả lời, không tạo thread, không đếm
            if action in {"block_silent", "block_polite"}:
                continue

            input_msg = FBMessageInput(psid=sender, text=text, message_id=mid, timestamp=ts)

            # Lấy hồ sơ khách quen & bài học mẫu Quản lý đã duyệt
            cust_prof = kv_get(f"customer_profile:{store_id}:{sender}", {})
            goldens = kv_get(f"cskh_golden_memory:{store_id}", [])
            learning_repository = AILearningRepository()
            active_rules, rollout_bucket = select_active_rules(
                learning_repository.active_rules(store_id=store_id, channel="facebook"),
                store_id=store_id,
                identity=sender,
            )

            # A later inbound message is feedback only when this exact thread already
            # carries a generation ID. Never guess based on the newest conversation.
            prior_thread = next(
                (thread for thread in _page_store().get("threads", []) if thread.get("psid") == sender),
                None,
            )
            prior_generation_id = str((prior_thread or {}).get("ai_generation_id") or "")
            if prior_generation_id:
                _record_fb_feedback(
                    store_id=store_id, conversation_id=sender, feedback_type="customer_followup",
                    final=text, actor_role="customer", generation_id=prior_generation_id,
                )
                if _customer_negative_signal(text):
                    _record_fb_feedback(
                        store_id=store_id, conversation_id=sender, feedback_type="customer_negative",
                        final=text, actor_role="customer", generation_id=prior_generation_id,
                    )

            # Xử lý tin nhắn qua AG-FBPAGE với Guardrails và Ngưỡng tin cậy
            out: FBMessageOutput = await process_fb_message(
                input_msg,
                auto_respond_enabled=True,
                public_context=public_ctx,
                customer_profile=cust_prof if cust_prof else None,
                golden_examples=goldens if goldens else None,
                active_rules=active_rules,
            )

            # Policy engine là cổng cuối (ADR-008): auto chỉ khi fb_policy đồng thuận
            # Nếu policy nói queue → ép queue bất kể kết quả AG-FBPAGE
            if circuit_breaker_open(store_id=store_id, channel="facebook") or action in {"queue_review", "priority_review", "escalate_owner"}:
                out = FBMessageOutput(
                    action="queue_to_inbox",
                    response=None,
                    intent=out.intent,
                    confidence=out.confidence,
                    emotion=out.emotion,
                    suggested_reply=out.suggested_reply or moderation.get("response"),
                    delegated_agent=out.delegated_agent,
                    reason="ai_circuit_breaker_open" if circuit_breaker_open(store_id=store_id, channel="facebook") else f"fb_policy:{moderation.get('reason')}",
                )
            # Ngược lại: fb_policy auto_send, AG-FBPAGE cũng auto_respond + feature flag bật
            elif action == "auto_send" and out.action == "auto_respond" and _fb_auto_send_enabled():
                out = FBMessageOutput(
                    action="auto_respond",
                    response=out.response,
                    intent=out.intent,
                    confidence=out.confidence,
                    emotion=out.emotion,
                    suggested_reply=out.suggested_reply,
                    delegated_agent=out.delegated_agent,
                    reason=f"fb_policy_auto:{moderation.get('reason')}",
                )
            else:
                # Policy auto nhưng AG-FBPAGE queue, hoặc flag tắt → queue để QL duyệt tay
                out = FBMessageOutput(
                    action="queue_to_inbox",
                    response=None,
                    intent=out.intent,
                    confidence=out.confidence,
                    emotion=out.emotion,
                    suggested_reply=out.suggested_reply or moderation.get("response"),
                    delegated_agent=out.delegated_agent,
                    reason="fb_policy_auto_guarded",
                )

            fingerprint = hashlib.sha256(f"{store_id}:{page_id}:{mid}:{out.action}:{out.suggested_reply or out.response or ''}".encode()).hexdigest()
            policy_action = "auto_send" if out.action == "auto_respond" else "queue_review"
            generation_id = f"facebook-{fingerprint[:24]}"
            learning_repository.save(AIGenerationRecord(
                id=generation_id, store_id=store_id, channel="facebook",
                conversation_id=sender, request_kind="facebook_message", external_event_hash=hashlib.sha256(mid.encode()).hexdigest(),
                draft={"body": out.suggested_reply or out.response or "Đã chuyển quản lý xử lý."}, context_snapshot_hash=fingerprint,
                agent_version="ag-fbpage", prompt_version="fb-messenger-v1",
                rule_version=",".join(str(rule.get("id")) for rule in active_rules) or "none",
                rollout_bucket=rollout_bucket, model={"provider": agent_mode(), "model_id": "ag-fbpage", "temperature": 0, "tool_context_hash": fingerprint},
                policy_action=policy_action, idempotency_key=f"generation:{fingerprint}", created_at=datetime.now(UTC).isoformat(),
            ))
            if moderation.get("review_id"):
                fb_review_link_generation(int(moderation["review_id"]), generation_id=generation_id)
            learning_repository.save(AIEvaluation(
                id=f"facebook-evaluation-{fingerprint[:20]}", store_id=store_id, generation_id=f"facebook-{fingerprint[:24]}", channel="facebook",
                scores={"accuracy": out.confidence, "safety": 1.0}, aggregate_score=out.confidence,
                passed=out.action == "auto_respond", action=policy_action,
                flags=[] if out.action == "auto_respond" else ["manager_review_required"], threshold_version="facebook-policy-v1",
                calibration_version="deterministic-v1", sample_count=0, evaluation_window="per_messenger_event",
                evaluator="ag-fbpage-policy", idempotency_key=f"evaluation:{fingerprint}", created_at=datetime.now(UTC).isoformat(),
            ))

            # Cập nhật hồ sơ khách quen nếu khách tự giới thiệu tên hoặc sở thích
            new_prefs = extract_customer_preferences([text])
            if new_prefs.get("ten_khach") or new_prefs.get("favorite_drinks") or new_prefs.get("special_notes"):
                def mut_prof(cur: dict[str, Any] | None, _p: dict[str, Any] = new_prefs) -> dict[str, Any]:
                    return merge_customer_profile(cur, _p)

                cust_prof = kv_mutate(f"customer_profile:{store_id}:{sender}", mut_prof, {})

            th = upsert_thread_from_messaging(sender, text, mid)
            th["ai_generation_id"] = generation_id
            th["intent"] = out.intent
            th["confidence"] = out.confidence
            th["suggested_reply"] = out.suggested_reply
            th["pending_approval"] = out.action == "queue_to_inbox"
            th["last_message_ts"] = ts
            th["is_within_24h"] = is_within_24h_window(ts)
            th["customer_profile"] = cust_prof

            if out.action == "auto_respond" and out.response:
                bot_reply = {
                    "id": f"bot_{uuid.uuid4().hex[:6]}",
                    "text": out.response,
                    "by": "Chatbot (Tự động)",
                    "at": _now(),
                    "mock": False,
                }
                delivered = _page_mode() != "live"
                if _page_mode() == "live":
                    try:
                        send_messenger_text(sender, out.response)
                        delivered = True
                    except Exception:
                        delivered = False
                review_id = moderation.get("review_id")
                if review_id is not None:
                    if delivered:
                        fb_review_finalize_claim(
                            int(review_id),
                            status="auto_sent",
                            decided_by="fb_auto",
                            final_response=out.response,
                        )
                    else:
                        fb_review_release_claim(int(review_id))
                if delivered:
                    th.setdefault("replies", []).append(bot_reply)

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
                    existing["ai_generation_id"] = thread.get("ai_generation_id")
                    existing["customer_profile"] = thread.get("customer_profile")
                else:
                    threads.insert(0, thread)
                doc["mode"] = "live"
                return doc

            kv_mutate("page_quan", mut, _page_store())
            n += 1

        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            if change.get("field") != "feed" or value.get("item") != "comment":
                continue
            if value.get("verb") != "add" or value.get("is_hidden"):
                continue
            author = value.get("from") or {}
            sender = str(author.get("id") or "")
            comment_id = str(value.get("comment_id") or "")
            text = str(value.get("message") or "").strip()
            if not sender or sender == page_id_cfg or not comment_id or not text:
                continue
            if not fb_try_claim_event(comment_id):
                continue

            moderation = moderate_fb_message(
                psid=sender,
                text=text,
                message_id=comment_id,
                timestamp=float(value.get("created_time") or 0),
                public_context=public_ctx,
                source="comment",
                post_id=str(value.get("post_id") or "") or None,
                external_user_name=str(author.get("name") or "") or None,
            )
            if moderation.get("action") not in {"block_silent", "block_polite"}:
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

    # ── Vòng lặp học từ câu sửa của Quản lý (CSKH Golden Memory) ──
    store_id = "quan_01"
    clean_final = body.final_reply.strip()
    msgs = found.get("messages") or []
    cust_msg = ""
    for m in reversed(msgs):
        if m.get("from_customer"):
            cust_msg = str(m.get("text") or "")
            break

    if cust_msg and suggested_orig and clean_final != suggested_orig:
        pair = extract_cskh_golden_pair(
            customer_msg=cust_msg,
            ai_draft=suggested_orig,
            manager_reply=clean_final,
            intent=str(found.get("intent") or "khac"),
            customer_name=str(found.get("sender_name") or "Khách hàng"),
        )
        if pair:
            def mut_golden(items: list[dict[str, Any]] | None, _p: dict[str, Any] = pair) -> list[dict[str, Any]]:
                lst = [x for x in (items or []) if x.get("customer_msg") != _p["customer_msg"]]
                lst.insert(0, _p)
                return lst[:20]

            kv_mutate(f"cskh_golden_memory:{store_id}", mut_golden, [])

    conversation_id = str(found.get("psid") or found.get("sender_id") or thread_id)
    manager_feedback = "manager_edit" if suggested_orig and clean_final != suggested_orig else "manager_approve"
    _record_fb_feedback(
        store_id=store_id, conversation_id=conversation_id, feedback_type=manager_feedback,
        original=suggested_orig, final=clean_final, actor_user_id=s["nv_id"], actor_role=str(s["role"]),
        generation_id=str(found.get("ai_generation_id") or "") or None,
    )
    _record_fb_feedback(
        store_id=store_id, conversation_id=conversation_id,
        feedback_type="send_success" if graph_sent else "send_failure", final=clean_final,
        actor_user_id=s["nv_id"], actor_role="system",
        send_status="sent" if graph_sent else "failed",
        failure_code=None if graph_sent else "not_sent_or_replay",
        generation_id=str(found.get("ai_generation_id") or "") or None,
    )

    # Cập nhật hồ sơ Khách quen nếu có
    if cust_msg:
        prefs = extract_customer_preferences([cust_msg])
        psid = str(found.get("psid") or found.get("sender_id") or "")
        if psid and (prefs.get("ten_khach") or prefs.get("favorite_drinks") or prefs.get("special_notes")):
            def mut_cust(cur: dict[str, Any] | None) -> dict[str, Any]:
                return merge_customer_profile(cur, prefs)

            kv_mutate(f"customer_profile:{store_id}:{psid}", mut_cust, {})

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


# ── FB moderation inbox (kế hoạch chatbot §3.8) ───────────────────────────


class FbInboxDecideBody(BaseModel):
    quyet_dinh: str = Field(pattern="^(duyet|sua_gui|tu_choi|chuyen_cap)$")
    noi_dung: str | None = None
    ly_do: str | None = None


@router.get("/api/v1/page/fb-inbox")
def fb_inbox_list(
    status: str | None = None,
    assigned_role: str | None = None,
    limit: int = 50,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Danh sách tin FB chờ duyệt. QL không xem hàng gán cho Chủ quán."""
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    role = _require_manager(authorization)
    if role == "quan_ly" and assigned_role == "chu_quan":
        raise HTTPException(status_code=403, detail="forbidden")
    visible_role = "quan_ly" if role == "quan_ly" else assigned_role
    items = fb_review_list(status=status, assigned_role=visible_role, limit=limit)
    for it in items:
        it["flagged_reasons"] = json.loads(it.get("flagged_reasons") or "[]")
    return {"items": items, "role": role}


@router.get("/api/v1/page/fb-inbox/stats")
def fb_inbox_stats(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_manager(authorization)
    return fb_stats()


@router.get("/api/v1/page/fb-inbox/{item_id}")
def fb_inbox_detail(
    item_id: int,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_manager(authorization)
    item = fb_review_get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="khong_thay")
    item["flagged_reasons"] = json.loads(item.get("flagged_reasons") or "[]")
    return item


@router.post("/api/v1/page/fb-inbox/{item_id}/decide")
def fb_inbox_decide(
    item_id: int,
    body: FbInboxDecideBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Duyệt / sửa rồi gửi / từ chối / chuyển cấp. RBAC theo assigned_role."""
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    role = _require_manager(authorization)
    item = fb_review_get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="khong_thay")
    if str(item.get("status")) != "pending":
        raise HTTPException(status_code=409, detail="da_quyet_truoc_do")
    # Escalate chủ quán: QL không được duyệt khi chưa được chuyển cấp
    if str(item.get("assigned_role")) == "chu_quan" and role != "chu_quan":
        raise HTTPException(status_code=403, detail="cho_chu_quan_duyet")

    customer_event_at = item.get("event_at") or item.get("created_at")
    if customer_event_at and not is_within_24h_window(str(customer_event_at)):
        fb_review_transition_pending(item_id, status="expired")
        raise HTTPException(status_code=409, detail="qua_cua_so_24h")

    if body.quyet_dinh == "tu_choi":
        updated = fb_review_decide(item_id, status="rejected", decided_by=s["nv_id"])
        if not updated:
            raise HTTPException(status_code=409, detail="da_quyet_truoc_do")
        _record_fb_feedback(
            store_id="quan_01", conversation_id=str(item.get("external_psid") or item_id),
            feedback_type="manager_reject", original=str(item.get("proposed_response") or ""),
            actor_user_id=s["nv_id"], actor_role=str(s["role"]),
            generation_id=str(item.get("ai_generation_id") or "") or None,
        )
        _audit(s["nv_id"], "fb_inbox_decide", {"id": item_id, "q": "tu_choi"})
        return {"ok": True, "item": updated, "sent": False}

    if body.quyet_dinh == "chuyen_cap":
        if role != "chu_quan":
            raise HTTPException(status_code=403, detail="chi_chu_quan_chuyen_cap")
        fb_escalation_add(
            item_id, escalated_to="chu_quan",
            reason=body.ly_do or "chuyen_cap", notified_channel="in_app",
        )
        return {"ok": True, "item": fb_review_get(item_id), "sent": False}

    # duyet / sua_gui — gửi đúng transport theo nguồn đã lưu
    final_text = (body.noi_dung or str(item.get("proposed_response") or "")).strip()
    if not final_text:
        raise HTTPException(status_code=400, detail="thieu_noi_dung")
    psid = str(item.get("external_psid") or "")
    if not fb_review_transition_pending(item_id, status="approved"):
        raise HTTPException(status_code=409, detail="da_quyet_truoc_do")
    graph_sent = False
    if _page_mode() == "live" and psid:
        try:
            if str(item.get("source")) == "comment":
                reply_to_comment(str(item.get("external_thread_id") or ""), final_text)
            else:
                send_messenger_text(psid, final_text)
            graph_sent = True
        except Exception:
            graph_sent = False
    if graph_sent:
        updated = fb_review_finalize_claim(
            item_id,
            status="sent",
            decided_by=s["nv_id"],
            final_response=final_text,
        )
    else:
        fb_review_release_claim(item_id)
        updated = fb_review_get(item_id)
    proposed = str(item.get("proposed_response") or "")
    _record_fb_feedback(
        store_id="quan_01", conversation_id=str(item.get("external_psid") or item_id),
        feedback_type="manager_edit" if proposed and proposed != final_text else "manager_approve",
        original=proposed, final=final_text, actor_user_id=s["nv_id"], actor_role=str(s["role"]),
        generation_id=str(item.get("ai_generation_id") or "") or None,
    )
    _record_fb_feedback(
        store_id="quan_01", conversation_id=str(item.get("external_psid") or item_id),
        feedback_type="send_success" if graph_sent else "send_failure", final=final_text,
        actor_user_id=s["nv_id"], actor_role="system", send_status="sent" if graph_sent else "failed",
        failure_code=None if graph_sent else "not_sent_or_replay",
        generation_id=str(item.get("ai_generation_id") or "") or None,
    )
    _audit(
        s["nv_id"],
        "fb_inbox_decide",
        {"id": item_id, "q": body.quyet_dinh, "graph_sent": graph_sent,
         "final_len": len(final_text)},
    )
    return {"ok": True, "item": updated, "sent": graph_sent}


# ── FB policy runtime config (kế hoạch §5.5 — Chủ quán chỉnh không cần sửa code) ──


class FbPolicyBody(BaseModel):
    auto_send_enabled: bool | None = None
    auto_price_cap_vnd: int | None = None
    note: str | None = None


def _fb_policy_get() -> dict[str, Any]:
    """Đọc config hiện tại (env override lên trước)."""
    return {
        "auto_send_enabled": _fb_auto_send_enabled(),
        "auto_price_cap_vnd": int(
            os.environ.get("NHIPQUAN_FB_AUTO_PRICE_CAP_VND", "100000")
        ),
        "page_mode": _page_mode(),
        "intent_thresholds": {
            "chao_hoi": 0.90,
            "hoi_gio_dia_chi": 0.85,
            "hoi_menu_gia": 0.85,
        },
        "comment_threshold": 0.95,
        "sla_minutes": {
            "priority_review": 5,
            "queue_review": 10,
            "escalate_owner": 15,
            "comment_queue": 15,
        },
    }


@router.get("/api/v1/page/fb-policy")
def fb_policy_get(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Chủ quán (và QL) xem policy hiện tại."""
    _require_manager(authorization)
    return _fb_policy_get()


@router.put("/api/v1/page/fb-policy")
def fb_policy_set(
    body: FbPolicyBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Chỉ Chủ quán mới được chỉnh `auto_send_enabled` + `auto_price_cap_vnd`.

    Thay đổi ghi audit + cập nhật env process hiện tại (tác dụng cho tới restart
    service; rollback bằng tắt flag qua env file). Ngưỡng intent/SLA cố định
    trong code (quyết định kinh doanh — đổi phải PR mới).
    """
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    if s.get("role") != "chu_quan":
        raise HTTPException(status_code=403, detail="chi_chu_quan")
    changes: dict[str, Any] = {}
    if body.auto_send_enabled is not None:
        os.environ["NHIPQUAN_FB_AUTO_SEND"] = "1" if body.auto_send_enabled else "0"
        changes["auto_send_enabled"] = body.auto_send_enabled
    if body.auto_price_cap_vnd is not None:
        if body.auto_price_cap_vnd < 0:
            raise HTTPException(status_code=400, detail="price_cap_am")
        os.environ["NHIPQUAN_FB_AUTO_PRICE_CAP_VND"] = str(int(body.auto_price_cap_vnd))
        changes["auto_price_cap_vnd"] = int(body.auto_price_cap_vnd)
    _audit(
        s["nv_id"],
        "fb_policy_update",
        {"changes": changes, "note": body.note or ""},
    )
    return _fb_policy_get()


class ApplyProposalBody(BaseModel):
    proposal_id: str
    title: str
    suggested_rule: str
    topic: str | None = None


@router.post("/api/v1/page/audit/reflection")
def page_audit_reflection(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Tự động kích hoạt Báo cáo Tự phê bình CSKH hàng đêm cho Quán."""
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    _require_manager(authorization)

    store_id = "quan_01"
    doc = _page_store()
    threads = doc.get("threads", [])

    report = run_nightly_cskh_reflection(threads, store_id=store_id)
    kv_set(f"cskh_reflection_reports:{store_id}", report)

    _audit(s["nv_id"], "cskh_nightly_reflection", {"csat": report["csat_score"], "proposals": len(report["playbook_rule_proposals"])})
    return {"ok": True, "report": report}


@router.get("/api/v1/page/audit/reflection/latest")
def get_latest_reflection(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Lấy báo cáo tự phê bình CSKH mới nhất."""
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    store_id = "quan_01"
    report = kv_get(f"cskh_reflection_reports:{store_id}", None)
    if not report:
        doc = _page_store()
        threads = doc.get("threads", [])
        report = run_nightly_cskh_reflection(threads, store_id=store_id)
        kv_set(f"cskh_reflection_reports:{store_id}", report)
    return {"ok": True, "report": report}


@router.post("/api/v1/page/audit/reflection/apply-proposal")
def apply_reflection_proposal(
    body: ApplyProposalBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Chấp thuận đề xuất cẩm nang từ báo cáo tự phê bình để đưa vào quy trình quán."""
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    _require_manager(authorization)

    store_id = "quan_01"
    def mut_rules(rules: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        lst = list(rules or [])
        lst.append({
            "id": body.proposal_id,
            "title": body.title,
            "rule": body.suggested_rule,
            "topic": body.topic,
            "created_by": f"AI Reflection ({s.get('display_name', s['nv_id'])})",
            "created_at": _now(),
        })
        return lst

    kv_mutate(f"playbook_rules:{store_id}", mut_rules, [])

    _audit(s["nv_id"], "apply_cskh_proposal", {"proposal_id": body.proposal_id, "title": body.title})
    return {"ok": True, "message": f"Đã bổ sung '{body.title}' vào cẩm nang quán thành công!"}


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
        "trang_thai": "cho_duyet",
        "by": role,
        "nguoi_tao": role,
        "at": _now(),
        "ngay_tao": _now(),
    }

    def mut(doc: dict[str, Any]) -> dict[str, Any]:
        doc.setdefault("drafts", []).insert(0, item)
        return doc

    kv_mutate("page_quan", mut, _page_store())
    return item


class PageDraftAIGenerateBody(BaseModel):
    topic: str
    tone: str = "than thien"


@router.post("/api/v1/page/drafts/ai-generate")
def page_draft_ai_generate(
    body: PageDraftAIGenerateBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    topic = (body.topic or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic_bat_buoc")

    tone = (body.tone or "than thien").strip()
    noi_dung = ""
    try:
        import sys
        from pathlib import Path
        scripts_dir = str(Path(__file__).resolve().parents[4] / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from fb_auto_poster import generate_content
        noi_dung = generate_content(topic, tone)
    except Exception:
        pass

    if not noi_dung.strip():
        try:
            from ca_agents.llm import complete
            sys_p = (
                "Ban la quan ly truyen thong cho quan ca phe 'Nhip Quan'. "
                "Hay viet mot bai dang Facebook tieng Viet 3-4 doan ngan, co emoji sinh dong, "
                "gioi thieu chu de theo yeu cau, ket thuc bang loi moi den quan (CTA), khong dung hashtag."
            )
            user_p = f"Chu de: {topic}. Giong: {tone}."
            res = complete(system=sys_p, user=user_p)
            if res.ok and res.text.strip():
                noi_dung = res.text.strip()
        except Exception:
            pass

    if not noi_dung.strip():
        noi_dung = (
            f"☕ Chào cả nhà! Hôm nay Nhịp Quán có gợi ý mới về '{topic}'. "
            f"Ghé quán thưởng thức cùng không gian yên tĩnh và wifi mạnh nhé! Hẹn gặp bạn hôm nay! ✨"
        )

    item = {
        "id": f"pd_{uuid.uuid4().hex[:8]}",
        "noi_dung": noi_dung,
        "trang_thai": "cho_duyet",
        "by": f"AI ({role})",
        "nguoi_tao": f"AI Copilot ({role})",
        "at": _now(),
        "ngay_tao": _now(),
        "topic": topic,
        "tone": tone,
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
            if os.environ.get("CA_AGENT_MODE", "").strip().lower() == "replay":
                pass
            else:
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
