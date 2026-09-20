"""HTTP router — Quán tự viết luật (plan 260920-1442 Phase 04).

- GET  /experience/rules/candidates — danh sách candidate
- POST /experience/rules/discover — chạy discover (deterministic)
- GET  /experience/rules/{candidate_id}/evidence — evidence timeline
- POST /experience/rules/{candidate_id}/shadow-test — shadow test cô lập
- POST /experience/rules/{candidate_id}/confirm — confirm (manager) → vong_doi
- POST /experience/rules/{candidate_id}/reject — reject
- POST /experience/rules/{candidate_id}/revoke — revoke active rule

Confirm/reject ủy quyền vong_doi lifecycle — không có state machine thứ hai.
Không rule nào tự kích hoạt (ADR-008).
"""

from __future__ import annotations

import threading
import time
from typing import Annotated, Any, cast

from ca_agents.ag_rule_learning.discover import (
    DecisionSignal,
    discover_rule_candidates,
    to_vf_condition,
)
from ca_agents.ag_rule_learning.evidence import build_evidence_readmodel
from ca_agents.ag_rule_learning.shadow_test import run_shadow_test
from ca_agents.grand_experience.replay import FixtureReader
from ca_contracts import RuleCandidate
from ca_playbook.vong_doi import de_xuat as vong_doi_de_xuat
from ca_playbook.vong_doi import kiem_chung as vong_doi_kiem_chung
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from ca_api.interfaces.http.sprint3 import _require_manager, _require_role

router = APIRouter(tags=["experience_rules"])

_LOCK = threading.Lock()
_CANDIDATES: dict[str, dict[str, Any]] = {}
_USER_TS: dict[str, list[float]] = {}
_WINDOW_S = 60.0
_MAX_REQ = 15


def clear_rule_state() -> None:
    with _LOCK:
        _CANDIDATES.clear()
        _USER_TS.clear()


def _rate_limit(user_id: str) -> None:
    now = time.time()
    with _LOCK:
        recent = [t for t in _USER_TS.get(user_id, []) if now - t < _WINDOW_S]
        if len(recent) >= _MAX_REQ:
            raise HTTPException(status_code=429, detail="rate_limit_exceeded")
        recent.append(now)
        _USER_TS[user_id] = recent


def _decisions() -> list[dict[str, Any]]:
    reader = FixtureReader()
    data = cast(dict[str, Any], reader.read_json_path("rule-learning.json"))
    return list(data.get("decisions", []))


def _snapshot_hash() -> str:
    reader = FixtureReader()
    data = cast(dict[str, Any], reader.read_json_path("rule-learning.json"))
    return str(data.get("snapshot_hash") or "snap_rule_fixture")


@router.get("/api/v1/experience/rules/candidates")
def rules_candidates(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_role(authorization)
    with _LOCK:
        items = [
            {"candidate_id": cid, "sentence": c["sentence"], "confidence": c["confidence"], "status": c.get("status", "draft")}
            for cid, c in _CANDIDATES.items()
        ]
    return {"candidates": items}


@router.post("/api/v1/experience/rules/discover")
def rules_discover(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Chạy discover deterministic trên fixture decisions."""
    _require_manager(authorization)
    _rate_limit(str(_require_manager(authorization)))
    rows = _decisions()
    signals = [
        DecisionSignal(
            signal_id=str(r["event_id"]),
            decision=str(r["decision"]),
            day_part=r.get("day_part"),
            station=r.get("station"),
            skill=r.get("skill"),
            demand_band=r.get("demand_band"),
            absence_type=r.get("absence_type"),
            outcome=str(r.get("outcome") or ""),
            source_kind=str(r.get("event_type") or "decision"),
            occurred_at=str(r.get("occurred_at") or ""),
        )
        for r in rows
    ]
    candidates = discover_rule_candidates(signals, snapshot_hash=_snapshot_hash())
    with _LOCK:
        for c in candidates:
            _CANDIDATES[c.candidate_id] = {
                **c.model_dump(mode="json"),
                "status": "draft",
            }
    return {
        "discovered": [c.candidate_id for c in candidates],
        "count": len(candidates),
        "sources": "fixture_replay",
    }


@router.get("/api/v1/experience/rules/{candidate_id}/evidence")
def rules_evidence(
    candidate_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_role(authorization)
    with _LOCK:
        item = _CANDIDATES.get(candidate_id)
    if not item:
        raise HTTPException(status_code=404, detail="candidate_not_found")
    candidate = RuleCandidate.model_validate(item)
    tl = build_evidence_readmodel(candidate, _decisions())
    return {
        "candidate_id": candidate_id,
        "timeline": tl.events,
        "repeated_decisions": tl.repeated_decisions,
        "actors": tl.actors,
        "affected_shifts": tl.affected_shifts,
        "counterexamples": tl.counterexamples,
        "confidence": tl.confidence,
    }


class ShadowBody(BaseModel):
    pass


@router.post("/api/v1/experience/rules/{candidate_id}/shadow-test")
def rules_shadow_test(
    candidate_id: str,
    body: ShadowBody | None = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_manager(authorization)
    with _LOCK:
        item = _CANDIDATES.get(candidate_id)
    if not item:
        raise HTTPException(status_code=404, detail="candidate_not_found")
    candidate = RuleCandidate.model_validate(item)
    result = run_shadow_test(
        candidate,
        historical_events=_decisions(),
        base_snapshot={"hard_constraints_ok": True, "luat_ap_dung": 0},
    )
    with _LOCK:
        item["shadow_result"] = result.model_dump(mode="json")
        _CANDIDATES[candidate_id] = item
    return {"candidate_id": candidate_id, "shadow": result.model_dump(mode="json")}


@router.post("/api/v1/experience/rules/{candidate_id}/confirm")
def rules_confirm(
    candidate_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Confirm → đưa candidate vào vong_doi (bước 3). Không tự kích hoạt."""
    _require_manager(authorization)
    with _LOCK:
        item = _CANDIDATES.get(candidate_id)
    if not item:
        raise HTTPException(status_code=404, detail="candidate_not_found")
    if not item.get("shadow_result"):
        raise HTTPException(status_code=409, detail="chua_chay_shadow_test")

    # Bridge vào vong_doi 8-step — sole writer.
    mau = {
        "mau": item["candidate_id"],
        "loai_luat": "nhu_cau_ca",
        "n": len(item["evidence_refs"]),
        "bang_chung": item["evidence_refs"],
        "nguon": "fixture_replay",
    }
    luat = vong_doi_de_xuat(
        mau,
        ban_nhap={
            "cau": item["sentence"],
            "dieu_kien": to_vf_condition(item["condition"]),
            "bang_chung": item["evidence_refs"],
        },
    )
    if luat is None:
        raise HTTPException(status_code=409, detail="khong_du_bang_chung")
    verified = vong_doi_kiem_chung(luat)
    if verified.get("trang_thai") == "loai":
        raise HTTPException(status_code=422, detail="vf_rule_loai")

    with _LOCK:
        item["status"] = "confirmed"
        item["playbook_ref"] = luat["id"]
        _CANDIDATES[candidate_id] = item
    return {
        "candidate_id": candidate_id,
        "playbook_status": verified["trang_thai"],
        "playbook_buoc": verified["buoc"],
        "not_auto_activated": True,
    }


@router.post("/api/v1/experience/rules/{candidate_id}/reject")
def rules_reject(
    candidate_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_manager(authorization)
    with _LOCK:
        item = _CANDIDATES.get(candidate_id)
    if not item:
        raise HTTPException(status_code=404, detail="candidate_not_found")
    item["status"] = "rejected"
    _CANDIDATES[candidate_id] = item
    return {"candidate_id": candidate_id, "status": "rejected"}


@router.post("/api/v1/experience/rules/{candidate_id}/revoke")
def rules_revoke(
    candidate_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Revoke active rule — dùng vong_doi.go_luat khi đã hieu_luc."""
    _require_manager(authorization)
    with _LOCK:
        item = _CANDIDATES.get(candidate_id)
    if not item:
        raise HTTPException(status_code=404, detail="candidate_not_found")
    if item.get("playbook_status") != "hieu_luc":
        raise HTTPException(status_code=409, detail="chua_phai_luat_hieu_luc")
    item["status"] = "revoked"
    _CANDIDATES[candidate_id] = item
    return {"candidate_id": candidate_id, "status": "revoked", "reason_required": True}