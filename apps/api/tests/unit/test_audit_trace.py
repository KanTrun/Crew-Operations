# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit test cho truy vết tác nhân trong sổ vết hệ thống.

Kiểm tra:
  - resolve_actor_type suy đúng loại từ `ai` (human/agent/system/guest)
  - audit_add ghi đủ actor_type/agent_name/controller_user_id
  - audit_list trả về các trường truy vết mới
  - copilot_audit_add / copilot_audit_list truyền agent_name + controller
"""

from __future__ import annotations

import pytest
from ca_api.audit_trace import ActorType, agent_label, resolve_actor_type
from ca_api.persist import (
    audit_add,
    audit_list,
    copilot_audit_add,
    copilot_audit_list,
    init_db,
)

# ── resolve_actor_type ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("ai", "expected"),
    [
        ("nv_001", ActorType.HUMAN),
        ("quan_ly", ActorType.HUMAN),
        ("ag_copilot", ActorType.AGENT),
        ("ag_scheduler", ActorType.AGENT),
        ("system", ActorType.SYSTEM),
        ("unknown", ActorType.SYSTEM),
        ("fb_policy_engine", ActorType.SYSTEM),
        ("fb_moderation_block", ActorType.SYSTEM),
        ("guest", ActorType.GUEST),
        ("nv_guest", ActorType.GUEST),
        (None, ActorType.HUMAN),
        ("", ActorType.HUMAN),
    ],
)
def test_resolve_actor_type(ai: str | None, expected: ActorType) -> None:
    assert resolve_actor_type(ai) == expected


def test_agent_label_known_and_unknown() -> None:
    assert agent_label("ag_copilot") == "AG-COPILOT"
    assert agent_label("ag_scheduler") == "AG-SCHEDULER"
    # Agent chưa đăng ký → trả về chính tên
    assert agent_label("ag_chua_biet") == "ag_chua_biet"
    assert agent_label(None) is None
    assert agent_label("") is None


# ── audit_add / audit_list ───────────────────────────────────────────────────

def test_audit_add_with_agent_trace() -> None:
    init_db()
    audit_add(
        "2026-09-17T10:00:00Z",
        "ag_copilot",
        "copilot.propose",
        {"intent": "SCHEDULE_SOLVE"},
        actor_type=ActorType.AGENT,
        agent_name="ag_copilot",
        controller_user_id="nv_quanly",
    )
    items = audit_list()
    assert items, "audit_list phải trả về ít nhất 1 vết"
    latest = items[0]
    assert latest["ai"] == "ag_copilot"
    assert latest["actor_type"] == "agent"
    assert latest["agent_name"] == "ag_copilot"
    assert latest["controller_user_id"] == "nv_quanly"


def test_audit_add_infers_actor_type_from_ai() -> None:
    init_db()
    # Không truyền actor_type → suy từ ai
    audit_add("2026-09-17T10:00:00Z", "system", "worker.run", {"job": "x"})
    audit_add("2026-09-17T10:00:00Z", "nv_001", "user.login", {})
    items = audit_list()
    by_ai = {it["ai"]: it for it in items}
    assert by_ai["system"]["actor_type"] == "system"
    assert by_ai["nv_001"]["actor_type"] == "human"


def test_audit_add_human_default() -> None:
    init_db()
    audit_add("2026-09-17T10:00:00Z", "nv_002", "user.logout", {})
    items = audit_list()
    latest = items[0]
    assert latest["actor_type"] == "human"
    assert latest["agent_name"] is None
    assert latest["controller_user_id"] is None


# ── copilot_audit_add / copilot_audit_list ───────────────────────────────────

def test_copilot_audit_with_agent_trace() -> None:
    init_db()
    copilot_audit_add(
        action_id="act_001",
        actor_user_id="nv_quanly",
        store_id="quan_01",
        intent="SCHEDULE_SOLVE",
        decision="approve",
        payload_diff={"ok": True},
        channel="web",
        latency_ms=120,
        agent_name="ag_copilot",
        controller_user_id="nv_quanly",
    )
    items = copilot_audit_list(store_id="quan_01")
    assert items, "copilot_audit_list phải trả về ít nhất 1 vết"
    latest = items[0]
    assert latest["action_id"] == "act_001"
    assert latest["agent_name"] == "ag_copilot"
    assert latest["controller_user_id"] == "nv_quanly"


def test_copilot_audit_without_agent_trace() -> None:
    init_db()
    copilot_audit_add(
        action_id="act_002",
        actor_user_id="nv_001",
        store_id="quan_01",
        intent="SEND_MAIL",
        decision="propose",
    )
    items = copilot_audit_list(store_id="quan_01")
    latest = items[0]
    assert latest["agent_name"] is None
    assert latest["controller_user_id"] is None