"""HTTP router — Predictive Playbook & Digital Twin (plan 260918 mục 5).

Endpoints:
- GET  /api/v1/ops/predict/suggestions — danh sách đề xuất luật tích cực
- POST /api/v1/ops/predict/run — trigger phát hiện mẫu thành công
- POST /api/v1/ops/twin/simulate — chạy mô phỏng "nếu... thì..."
- GET  /api/v1/ops/twin/scenarios — danh sách kịch bản đã chạy
- POST /api/v1/ops/predict/{rule_id}/approve — duyệt luật tích cực (fail-closed)
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Annotated, Any, cast

from ca_agents.ag_predict import (
    de_xuat_luat_tich_cuc,
    detect_success_patterns,
)
from ca_agents.ag_twin import simulate_scenario, simulate_virtual_staff
from ca_contracts.ops_predict import (
    TwinScenarioType,
)
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ca_api.interfaces.http.sprint3 import _require_manager, _require_role
from ca_api.persist import kv_get, kv_mutate

router = APIRouter(tags=["ops_predict"])

# ── Rate limiting + idempotency (plan mục 5.2) ───────────────────────────────
_RATE_LIMIT_LOCK = threading.Lock()
_USER_REQUEST_TIMESTAMPS: dict[str, list[float]] = {}
_IDEMPOTENCY_INDEX: dict[str, str] = {}
_WINDOW_S = 60.0
_MAX_REQ_PER_MIN = 30


def _check_rate_limit(user_id: str) -> None:
    """Cửa sổ trượt 60s cho request của user (plan mục 5.2: 30 req/60s)."""
    with _RATE_LIMIT_LOCK:
        now = time.time()
        stale = [
            k for k, ts in _USER_REQUEST_TIMESTAMPS.items()
            if not ts or (now - ts[-1]) >= _WINDOW_S
        ]
        for k in stale:
            _USER_REQUEST_TIMESTAMPS.pop(k, None)
        recent = [t for t in _USER_REQUEST_TIMESTAMPS.get(user_id, []) if (now - t) < _WINDOW_S]
        if len(recent) >= _MAX_REQ_PER_MIN:
            _USER_REQUEST_TIMESTAMPS[user_id] = recent
            raise HTTPException(status_code=429, detail="rate_limit_exceeded:too_many_requests")
        recent.append(now)
        _USER_REQUEST_TIMESTAMPS[user_id] = recent


def _check_idempotency(key: str) -> str | None:
    """Trả về kết quả đã lưu nếu key trùng (idempotent POST)."""
    with _RATE_LIMIT_LOCK:
        return _IDEMPOTENCY_INDEX.get(key)


def _store_idempotency(key: str, result: str) -> None:
    with _RATE_LIMIT_LOCK:
        _IDEMPOTENCY_INDEX[key] = result


def _fingerprint(payload: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def clear_rate_limits() -> None:
    """Xóa bộ đếm rate limit + idempotency (dùng khi test)."""
    with _RATE_LIMIT_LOCK:
        _USER_REQUEST_TIMESTAMPS.clear()
        _IDEMPOTENCY_INDEX.clear()


class PredictRunBody(BaseModel):
    doanh_thu_by_ca: dict[str, float] = Field(default_factory=dict)
    doanh_thu_by_mon: dict[str, float] = Field(default_factory=dict)
    ton_kho_by_time: dict[str, float] = Field(default_factory=dict)


class TwinSimulateBody(BaseModel):
    scenario_id: str
    loai: TwinScenarioType
    tham_so: dict[str, object] = Field(default_factory=dict)
    baseline: dict[str, object] = Field(default_factory=dict)


@router.get("/api/v1/ops/predict/suggestions")
def get_predict_suggestions(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Lấy danh sách đề xuất luật tích cực + mẫu thành công."""
    _require_role(authorization)
    rules = kv_get("ops_predict_rules", [])
    patterns = kv_get("ops_predict_patterns", [])
    scenarios = kv_get("ops_twin_scenarios", [])
    return {
        "suggestions": rules,
        "patterns": patterns,
        "twin_scenarios": scenarios,
    }


@router.post("/api/v1/ops/predict/run")
def run_predict(
    body: PredictRunBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Trigger phát hiện mẫu thành công → đề xuất luật tích cực."""
    user = _require_manager(authorization)
    _check_rate_limit(str(user))

    # Idempotency: cùng payload → cùng kết quả
    fp = _fingerprint(body.model_dump())
    idem_key = f"predict_run:{fp}"
    cached = _check_idempotency(idem_key)
    if cached:
        return cast(dict[str, Any], json.loads(cached))

    patterns = detect_success_patterns(
        doanh_thu_by_ca=body.doanh_thu_by_ca,
        doanh_thu_by_mon=body.doanh_thu_by_mon,
        ton_kho_by_time=body.ton_kho_by_time,
    )
    rules = de_xuat_luat_tich_cuc(patterns)

    # Lưu vào KV store
    pattern_dicts = [p.model_dump() for p in patterns]
    rule_dicts = [r.model_dump() for r in rules]

    def mut_patterns(cur: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return pattern_dicts + cur

    def mut_rules(cur: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return rule_dicts + cur

    kv_mutate("ops_predict_patterns", mut_patterns, [])
    kv_mutate("ops_predict_rules", mut_rules, [])

    result = {
        "ok": True,
        "patterns": pattern_dicts,
        "suggestions": rule_dicts,
    }
    _store_idempotency(idem_key, json.dumps(result, ensure_ascii=False))
    return result


@router.post("/api/v1/ops/twin/simulate")
def twin_simulate(
    body: TwinSimulateBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Chạy mô phỏng "nếu... thì..." (tất định)."""
    user = _require_manager(authorization)
    _check_rate_limit(str(user))

    # Idempotency: cùng scenario_id + tham_so → cùng kết quả
    fp = _fingerprint(body.model_dump())
    idem_key = f"twin_simulate:{fp}"
    cached = _check_idempotency(idem_key)
    if cached:
        return cast(dict[str, Any], json.loads(cached))

    scenario = simulate_scenario(
        scenario_id=body.scenario_id,
        loai=body.loai,
        tham_so=body.tham_so,
        baseline=body.baseline,
    )
    scenario_dict = scenario.model_dump()

    def mut_scenarios(cur: list[dict[str, Any]]) -> list[dict[str, Any]]:
        res = [s for s in cur if s.get("scenario_id") != body.scenario_id]
        res.insert(0, scenario_dict)
        return res

    kv_mutate("ops_twin_scenarios", mut_scenarios, [])
    result = {"ok": True, "scenario": scenario_dict}
    _store_idempotency(idem_key, json.dumps(result, ensure_ascii=False))
    return result


@router.get("/api/v1/ops/twin/scenarios")
def list_twin_scenarios(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Lấy danh sách kịch bản đã chạy."""
    _require_role(authorization)
    scenarios = kv_get("ops_twin_scenarios", [])
    return {"items": scenarios}


@router.post("/api/v1/ops/predict/{rule_id}/approve")
def approve_positive_rule(
    rule_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Duyệt luật tích cực (fail-closed, chỉ Quản lý/Chủ quán)."""
    _require_manager(authorization)

    rules = kv_get("ops_predict_rules", [])
    target = next((r for r in rules if r.get("id") == rule_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Rule not found")

    def mut_rules(cur: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {**r, "trang_thai": "hieu_luc"} if r.get("id") == rule_id else r
            for r in cur
        ]

    kv_mutate("ops_predict_rules", mut_rules, [])
    return {"ok": True, "rule_id": rule_id, "trang_thai": "hieu_luc"}


class VirtualStaffBody(BaseModel):
    simulation_id: str
    kich_ban: str
    staff_rows: list[dict[str, object]] = Field(default_factory=list)
    so_lan: int = 1


@router.post("/api/v1/ops/twin/virtual-staff")
def twin_virtual_staff(
    body: VirtualStaffBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Mô phỏng hành vi nhân viên ảo (tất định, không LLM)."""
    _require_manager(authorization)

    simulation = simulate_virtual_staff(
        simulation_id=body.simulation_id,
        kich_ban=body.kich_ban,
        staff_rows=body.staff_rows,
        so_lan=body.so_lan,
    )
    return {"ok": True, "simulation": simulation.model_dump(mode="json")}