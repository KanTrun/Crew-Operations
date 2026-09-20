"""HTTP router — Grand AI Experience boundary (plan 260920-1442 Phase 01).

Phase 01 chỉ đăng ký ranh giới CHỈ-ĐỌC: capabilities + map (anchor list) +
snapshot hash. Không có mutation ở phase này — mọi mutation (proposal, consent,
mode) đến phase 02-06.

Nguyên tắc fail-closed: UI button không bao giờ là authorization; capability
được kiểm server-side qua `experience_role_can`.
"""

from __future__ import annotations

from typing import Annotated, Any

from ca_agents.grand_experience.adapter import resolve_experience_read_adapter
from ca_contracts import (
    experience_capabilities_for_role,
)
from fastapi import APIRouter, Header

from ca_api.interfaces.http.sprint3 import _require_role

router = APIRouter(tags=["experience"])


def _role_from(authorization: str | None) -> str:
    return _require_role(authorization)


@router.get("/api/v1/experience/capabilities")
def experience_capabilities(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Trả về capability của vai trò hiện tại trên bề mặt trải nghiệm."""
    role = _role_from(authorization)
    caps = sorted(experience_capabilities_for_role(role))
    return {"role": role, "capabilities": list(caps), "capability_policy_version": "v1"}


@router.get("/api/v1/experience/map")
def experience_map(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Bản đồ không gian (read-only) — anchor fixture deterministic."""
    role = _role_from(authorization)
    adapter = resolve_experience_read_adapter()
    anchors = adapter.list_anchors()
    return {
        "anchors": [a.model_dump(mode="json") for a in anchors],
        "source": "fixture_replay",
        "data_quality": [
            {
                "code": "fixture_replay",
                "level": "info",
                "message": "Dữ liệu bản đồ là fixture replay — không phải dữ liệu đo thật.",
            }
        ],
        "role": role,
    }


@router.get("/api/v1/experience/events")
def experience_events(
    authorization: Annotated[str | None, Header()] = None,
    anchor_id: str | None = None,
    event_type: str | None = None,
) -> dict[str, Any]:
    """Sự kiện trải nghiệm theo anchor (read-only, fixture deterministic)."""
    _role_from(authorization)
    adapter = resolve_experience_read_adapter()
    events = adapter.list_events(anchor_id=anchor_id, event_type=event_type)
    # payload_json có thể chứa object — đã serialize an toàn
    return {"events": events, "count": len(events), "source": "fixture_replay"}


@router.get("/api/v1/experience/snapshot-hash")
def experience_snapshot_hash(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Fingerprint fixture hiện tại — dùng làm snapshot hash trong replay."""
    _role_from(authorization)
    adapter = resolve_experience_read_adapter()
    fp = adapter.fingerprint()
    return {"snapshot_hash": fp, "source": "fixture_replay"}


def audit_experience_decision(
    actor_id: str,
    action: str,
    proposal_id: str,
    outcome: str,
    reason: str = "",
    store_id: str = "quan_01",
) -> dict[str, str]:
    """Helper ghi audit cho proposal/consent decisions (Phase 01 sơ khởi).

    Không lưu raw audio/secret — chỉ lưu mã hành động + actor + outcome.
    Phase 05+ sẽ nối vào audit_trace hiện có để có dấu vết đầy đủ.
    """
    return {
        "actor_id": actor_id,
        "action": action,
        "proposal_id": proposal_id,
        "outcome": outcome,
        "reason": reason,
        "store_id": store_id,
    }