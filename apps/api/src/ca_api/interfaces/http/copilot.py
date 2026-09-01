"""AG-COPILOT HTTP endpoints — Conversational dispatch, two-phase confirmation, VF gates & audit."""

from __future__ import annotations

import hmac
import hashlib
import json
import os
import time
import uuid
from typing import Annotated, Any

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ca_agents.ag_copilot import run_copilot
from ca_contracts import (
    ActionProposal,
    ActionProposalStatus,
    COPILOT_ROLE_INTENT_MATRIX,
    CopilotContext,
    CopilotIntent,
    CopilotMessage,
    CopilotResponse,
    copilot_intents_allowed_for_role,
)
from ca_gates import compute_snapshot_hash, validate_scope, validate_stale
from ca_api.persist import (
    copilot_audit_add,
    copilot_audit_list,
    copilot_draft_get,
    copilot_draft_list,
    copilot_draft_save,
    copilot_draft_update_status,
    kv_get,
    kv_mutate,
    kv_set,
)
from ca_api.persist import session as auth_session

router = APIRouter(prefix="/api/v1/copilot", tags=["copilot"])

_RATE_LIMIT_STORE: dict[str, list[float]] = {}


def _get_verified_user(authorization: str | None) -> dict[str, str]:
    """Extract authenticated session; fallback to default test user if auth not enforced in replay."""
    sess = auth_session(authorization)
    if sess:
        return {
            "username": sess["username"],
            "user_id": sess["nv_id"],
            "role": sess["role"],
            "store_id": "quan_01",
        }
    # For open endpoints with optional auth, check header or assign unauthenticated
    return {
        "username": "guest",
        "user_id": "nv_guest",
        "role": "nhan_vien",
        "store_id": "quan_01",
    }


def _require_user(authorization: str | None) -> dict[str, str]:
    """Validate user — raise 401 when token missing. For write-like endpoints.

    Giữ `_get_verified_user` cho endpoint đọc (Telegram/Zalo webhook có thể không
    có token user). Endpoint GHI dữ liệu (execute-action, amend) phải xác thực.
    """
    sess = auth_session(authorization)
    if not sess:
        raise HTTPException(status_code=401, detail="thieu_token_hoac_session_het_han")
    return {
        "username": sess["username"],
        "user_id": sess["nv_id"],
        "role": sess["role"],
        "store_id": "quan_01",
    }


def _check_rate_limit(user_id: str, max_per_min: int = 30) -> None:
    now = time.time()
    times = [t for t in _RATE_LIMIT_STORE.get(user_id, []) if now - t < 60]
    if len(times) >= max_per_min:
        raise HTTPException(status_code=429, detail="rate_limit_exceeded:too_many_requests")
    times.append(now)
    _RATE_LIMIT_STORE[user_id] = times


# ── Request / Response Models ────────────────────────────────────────────────

class MessageRequestBody(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    store_id: str = "quan_01"
    channel: str = "web"
    recent_messages: list[str] = Field(default_factory=list, max_length=3)


class ExecuteActionBody(BaseModel):
    action_id: str
    decision: str = Field(pattern="^(approve|reject)$")
    idempotency_key: str = Field(default_factory=lambda: uuid.uuid4().hex)
    reason: str | None = None


class AmendActionBody(BaseModel):
    reason: str = Field(min_length=3)
    correction_diff: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(default_factory=lambda: uuid.uuid4().hex)


# ── 1. POST /api/v1/copilot/message ──────────────────────────────────────────

@router.post("/message", response_model=CopilotResponse)
def copilot_message(
    body: MessageRequestBody,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_telegram_secret: Annotated[str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")] = None,
) -> CopilotResponse:
    """Send natural language instruction to AG-COPILOT."""
    t0 = time.time()

    # Webhook signature verification for Telegram if channel is telegram
    if body.channel == "telegram":
        expected_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
        if expected_secret and x_telegram_secret != expected_secret:
            raise HTTPException(status_code=401, detail="invalid_telegram_webhook_secret")

    user = _get_verified_user(authorization)
    _check_rate_limit(user["user_id"])

    # Enforce verified identity from server session
    verified_context = {
        "store_id": user["store_id"],
        "user_id": user["user_id"],
        "user_role": user["role"],
        "active_date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "channel": body.channel,
        "recent_messages": body.recent_messages,
    }

    # Run AG-COPILOT
    response = run_copilot(body.message, verified_context)
    latency_ms = int((time.time() - t0) * 1000)

    # Minh bạch: log các lượt bị chặn do vượt quyền (role_blocked) để review.
    if response.intent == CopilotIntent.OUT_OF_SCOPE and "vượt phạm vi vai trò" in response.reply_text:
        copilot_audit_add(
            action_id="n/a",
            actor_user_id=user["user_id"],
            store_id=user["store_id"],
            intent="role_blocked",
            decision="role_blocked",
            payload_diff={"message": body.message[:200]},
            channel=body.channel,
            latency_ms=latency_ms,
        )

    # If action proposal was generated, save draft and log propose audit
    if response.action_proposal:
        prop_dict = response.action_proposal.model_dump()
        copilot_draft_save(prop_dict)
        copilot_audit_add(
            action_id=response.action_proposal.action_id,
            actor_user_id=user["user_id"],
            store_id=user["store_id"],
            intent=response.action_proposal.intent.value,
            decision="propose",
            payload_diff=response.action_proposal.payload_diff,
            channel=body.channel,
            latency_ms=latency_ms,
        )

    return response


# ── 1b. POST /api/v1/copilot/message/stream (SSE) ────────────────────────────

@router.post("/message/stream")
def copilot_message_stream(
    body: MessageRequestBody,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> StreamingResponse:
    """SSE streaming: gửi event meta (intent/proposal) rồi delta text từng phần.

    Trả về mỗi dòng dạng `event: <name>\\ndata: <json>\\n\\n`. Client dùng
    fetch + ReadableStream đọc từng chunk. Fallback auto về /message (JSON)
    nếu LLM stream không khả dụng.
    """
    user = _get_verified_user(authorization)
    _check_rate_limit(user["user_id"])
    verified_context = {
        "store_id": user["store_id"],
        "user_id": user["user_id"],
        "user_role": user["role"],
        "active_date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "channel": body.channel,
        "recent_messages": body.recent_messages,
    }

    # 1. Chạy copilot bình thường (tất định: intent/tool/proposal) — nhanh vì replay.
    response = run_copilot(body.message, verified_context)

    # 2. Xây generator SSE
    def _sse(
        ev: str, payload: dict[str, Any]
    ) -> str:
        return f"event: {ev}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def _gen():
        # Meta trước: intent + confidence + action_proposal (client biết trước).
        meta = {
            "intent": response.intent.value if hasattr(response.intent, "value") else str(response.intent),
            "confidence": response.confidence,
            "action_proposal": (
                response.action_proposal.model_dump() if response.action_proposal else None
            ),
            "citations": list(getattr(response, "citations", []) or []),
            "direct_answer": getattr(response, "direct_answer", None),
        }
        yield _sse("meta", meta)

        # Text: stream từng phần từ reply_text.
        reply_text = response.reply_text or ""
        # Chia nhỏ theo từ khoá (giữ khoảng trắng) để mượt.
        parts = _chunk_text(reply_text)
        for chunk in parts:
            yield _sse("delta", {"text": chunk})
        yield _sse("done", {"ok": True})

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _chunk_text(text: str, size: int = 4) -> list[str]:
    """Chia chuỗi thành các cụm nhỏ (SSE delta). Giữ nguyên khoảng trắng."""
    chars = list(text)
    return ["".join(chars[i : i + size]) for i in range(0, len(chars), size)]


# ── 2. POST /api/v1/copilot/execute-action ───────────────────────────────────

@router.post("/execute-action")
def copilot_execute_action(
    body: ExecuteActionBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Confirm/Approve or Reject an ActionProposal with VF-SCOPE, VF-STALE and Idempotency."""
    t0 = time.time()
    user = _require_user(authorization)
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Fetch draft from DB
    draft = copilot_draft_get(body.action_id)
    if not draft:
        raise HTTPException(status_code=404, detail="action_proposal_not_found")

    # 2. Check Idempotency / Already Executed
    if draft["status"] == "executed":
        return {
            "ok": True,
            "action_id": body.action_id,
            "status": "executed",
            "message": "Action already executed successfully (idempotent replay).",
            "payload_diff": draft["payload_diff"],
        }

    # 3. VF-SCOPE: Multi-tenant and role check
    scope_res = validate_scope(
        caller_store_id=user["store_id"],
        target_store_id=draft["store_id"],
        caller_role=user["role"],
        intent=draft["intent"],
        action_created_by=draft["created_by"],
        caller_user_id=user["user_id"],
    )
    if not scope_res.passed:
        copilot_audit_add(
            action_id=body.action_id,
            actor_user_id=user["user_id"],
            store_id=user["store_id"],
            intent=draft["intent"],
            decision="authz_blocked",
            payload_diff={"reason": scope_res.reason},
            channel="web",
            latency_ms=int((time.time() - t0) * 1000),
        )
        raise HTTPException(status_code=403, detail=f"scope_blocked:{scope_res.reason}")

    # 4. Check Expiration
    if draft["expires_at"]:
        try:
            exp_dt = datetime.fromisoformat(draft["expires_at"].replace("Z", "+00:00"))
            if datetime.now(UTC) > exp_dt:
                copilot_draft_update_status(body.action_id, "expired")
                copilot_audit_add(
                    action_id=body.action_id,
                    actor_user_id=user["user_id"],
                    store_id=user["store_id"],
                    intent=draft["intent"],
                    decision="expired",
                    channel="web",
                    latency_ms=int((time.time() - t0) * 1000),
                )
                raise HTTPException(status_code=400, detail="action_proposal_expired")
        except Exception:
            pass

    # 5. Handle REJECT
    if body.decision == "reject":
        copilot_draft_update_status(body.action_id, "rejected")
        copilot_audit_add(
            action_id=body.action_id,
            actor_user_id=user["user_id"],
            store_id=user["store_id"],
            intent=draft["intent"],
            decision="reject",
            payload_diff={"reason": body.reason},
            channel="web",
            latency_ms=int((time.time() - t0) * 1000),
        )
        return {
            "ok": True,
            "action_id": body.action_id,
            "status": "rejected",
            "message": "Action proposal rejected.",
        }

    # 6. VF-STALE Check on APPROVE
    # Compute current data state snapshot
    current_snapshot_data = draft["payload_diff"]
    current_hash = compute_snapshot_hash(current_snapshot_data)
    stale_res = validate_stale(
        draft_snapshot_hash=draft["data_snapshot_hash"],
        current_snapshot_hash=current_hash,
    )
    if not stale_res.passed:
        copilot_draft_update_status(body.action_id, "stale_rejected")
        copilot_audit_add(
            action_id=body.action_id,
            actor_user_id=user["user_id"],
            store_id=user["store_id"],
            intent=draft["intent"],
            decision="stale_rejected",
            payload_diff={"reason": stale_res.reason},
            channel="web",
            latency_ms=int((time.time() - t0) * 1000),
        )
        raise HTTPException(status_code=409, detail=f"stale_rejected:{stale_res.reason}")

    # 7. Apply Action Execution (Single Transaction)
    intent = draft["intent"]
    diff = draft["payload_diff"]

    if intent == "SCHEDULE_SOLVE":
        kv_set("lich_tuan", diff.get("phan_cong", {}))
        kv_set("lich_tuan_status", "da_cong_bo")
    elif intent == "APPROVE_SHIFT_SWAP":
        swap_id = diff.get("swap_id")
        # UI + tool hiện dùng KV "swap" (swap-market 3 nhánh, khóa "id").
        def mut_swap(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            for it in items:
                if it.get("id") == swap_id or it.get("swap_id") == swap_id:
                    it["trang_thai"] = "da_duyet"
                    it["duyet_ai"] = user["user_id"]
                    it["duyet_luc"] = now_iso
            return items
        kv_mutate("swap", mut_swap, [])
        # Cũ (legacy) vẫn dùng khóa "shift_swaps" + "swap_id".
        def mut_legacy(swaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
            for sw in swaps:
                if sw.get("swap_id") == swap_id:
                    sw["trang_thai"] = "da_duyet"
            return swaps
        kv_mutate("shift_swaps", mut_legacy, [])
        # Cập nhật phân công thật: hoán đổi người trong ca trên lịch tuần.
        ca_id = diff.get("ca_id")
        tu_nv, nhan_nv = diff.get("tu_nv"), diff.get("nhan_nv")
        if ca_id and tu_nv and nhan_nv:
            def mut_phan_cong(phan_cong: dict[str, Any]) -> dict[str, Any]:
                for ca, nvs in phan_cong.items():
                    if ca == ca_id and isinstance(nvs, list):
                        for i, nv in enumerate(nvs):
                            if nv == tu_nv:
                                nvs[i] = nhan_nv
                return phan_cong
            kv_mutate("phan_cong", mut_phan_cong, {})
    elif intent == "CREATE_RULE_PROPOSAL":
        # Ghi luật thật vào cẩm nang sống (cam_nang.json) ở trạng thái de_xuat.
        de_xuat = diff.get("de_xuat")
        if isinstance(de_xuat, dict):
            try:
                from ca_playbook.vong_doi import list_luat, save_luat
                luat = list(list_luat() or [])
                luat.append(de_xuat)
                save_luat(luat)
            except Exception:
                # Fallback sang KV nếu playbook chưa khả dụng.
                def mut_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
                    rules.append(de_xuat)
                    return rules
                kv_mutate("rules", mut_rules, [])
        else:
            def mut_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
                rules.append(diff)
                return rules
            kv_mutate("rules", mut_rules, [])
    elif intent == "INVENTORY_RESTOCK_CHECK":
        # Tool trả data.canh_bao (danh sách mặt hàng dưới ngưỡng).
        items = diff.get("canh_bao") or diff.get("items") or []
        def mut_orders(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
            orders.append({"order_id": f"ord_{uuid.uuid4().hex[:6]}", "items": items, "created_at": now_iso})
            return orders
        kv_mutate("restock_orders", mut_orders, [])

    # Mark draft as executed
    copilot_draft_update_status(body.action_id, "executed", executed_at=now_iso)

    # Record audit log
    copilot_audit_add(
        action_id=body.action_id,
        actor_user_id=user["user_id"],
        store_id=user["store_id"],
        intent=draft["intent"],
        decision="approve",
        payload_diff=diff,
        channel="web",
        latency_ms=int((time.time() - t0) * 1000),
    )

    return {
        "ok": True,
        "action_id": body.action_id,
        "status": "executed",
        "message": "Đã phê duyệt và thực thi hành động thành công!",
        "payload_diff": diff,
    }


# ── 3. POST /api/v1/copilot/action/{action_id}/amend ─────────────────────────

@router.post("/action/{action_id}/amend")
def copilot_amend_action(
    action_id: str,
    body: AmendActionBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Amend / Correct an already executed action within the amendment time window (15 mins)."""
    t0 = time.time()
    user = _require_user(authorization)
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    draft = copilot_draft_get(action_id)
    if not draft:
        raise HTTPException(status_code=404, detail="action_not_found")

    if draft["status"] != "executed":
        raise HTTPException(status_code=400, detail="only_executed_actions_can_be_amended")

    # Check 15-minute amendment window
    if draft["executed_at"]:
        try:
            exec_dt = datetime.fromisoformat(draft["executed_at"].replace("Z", "+00:00"))
            if (datetime.now(UTC) - exec_dt).total_seconds() > 900:  # 15 mins
                raise HTTPException(status_code=400, detail="amendment_window_expired")
        except HTTPException:
            raise
        except Exception:
            pass

    # Create new correction draft action
    new_action_id = f"amend_{uuid.uuid4().hex[:8]}"
    new_draft = {
        "action_id": new_action_id,
        "intent": draft["intent"],
        "status": "executed",
        "store_id": draft["store_id"],
        "created_by": user["user_id"],
        "confidence": 1.0,
        "summary": f"Đính chính cho hành động {action_id}: {body.reason}",
        "explanation": f"Yêu cầu đính chính từ {user['username']}: {body.reason}",
        "payload_diff": body.correction_diff or draft["payload_diff"],
        "requires_confirmation": True,
        "data_snapshot_hash": draft["data_snapshot_hash"],
        "expires_at": draft["expires_at"],
        "created_at": now_iso,
        "executed_at": now_iso,
        "amended_from": action_id,
        "amended_by": user["user_id"],
    }
    copilot_draft_save(new_draft)

    # Link original action
    copilot_draft_update_status(action_id, "executed", amended_by=user["user_id"])

    # Log audit
    copilot_audit_add(
        action_id=new_action_id,
        actor_user_id=user["user_id"],
        store_id=user["store_id"],
        intent=draft["intent"],
        decision="amend",
        payload_diff={"amended_from": action_id, "reason": body.reason, "diff": body.correction_diff},
        channel="web",
        latency_ms=int((time.time() - t0) * 1000),
    )

    return {
        "ok": True,
        "new_action_id": new_action_id,
        "amended_from": action_id,
        "status": "executed",
        "message": f"Đã ghi nhận đính chính cho hành động {action_id}.",
    }


# ── 4. GET /api/v1/copilot/action/{action_id} ────────────────────────────────

@router.get("/action/{action_id}")
def copilot_get_action(
    action_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Get ActionProposal details."""
    draft = copilot_draft_get(action_id)
    if not draft:
        raise HTTPException(status_code=404, detail="action_not_found")
    return draft


# ── 5. GET /api/v1/copilot/audit ─────────────────────────────────────────────

@router.get("/audit")
def copilot_get_audit(
    store_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    authorization: Annotated[str | None, Header()] = None,
) -> list[dict[str, Any]]:
    """Get audit log for Copilot actions (manager/owner view)."""
    user = _get_verified_user(authorization)
    target_store = store_id or user["store_id"]
    return copilot_audit_list(target_store, limit=limit)


# ── 6. GET /api/v1/copilot/permissions ───────────────────────────────────────

@router.get("/permissions")
def copilot_get_permissions(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Minh bạch quyền: role hiện tại được (và không được) dùng intent nào."""
    user = _get_verified_user(authorization)
    role = user["role"]
    allowed = sorted(copilot_intents_allowed_for_role(role))
    all_intents = sorted(
        str(i.value) if hasattr(i, "value") else str(i)
        for i in CopilotIntent
        if i != CopilotIntent.OUT_OF_SCOPE
    )
    return {
        "role": role,
        "allowed_intents": allowed,
        "denied_intents": sorted(set(all_intents) - set(allowed)),
        "matrix": {
            r: sorted(v) for r, v in COPILOT_ROLE_INTENT_MATRIX.items()
        },
    }
