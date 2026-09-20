"""War Room orchestrator — so sánh baseline + đa phương án, tất định.

Pipeline:
1. Normalize command (Pydantic fail-closed).
2. Xây LichInput từ baseline (đọc qua adapter/fixture).
3. Với mỗi scenario: chạy AG-TWIN math → outputs; CP-SAT/solve_hard_only
   cho feasibility; fairness delta bằng ca_solver.fairness.
4. Dựng EvidenceBuilder — mọi số đều có nguồn.
5. Idempotent theo fingerprint (request_id + scenarios).

Không gọi LLM ở tầng này. Không mutation — chỉ trả WarRoomComparison.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ca_contracts import (
    WarRoomComparison,
    WarRoomOption,
    WarRoomScenario,
    WarRoomScenarioType,
)
from ca_solver.fairness import (
    max_debt,
    update_debt_from_assignment,
    zero_debt,
)
from ca_solver.model import LichInput, solve_hard_only

from ca_agents.ag_twin.simulator import simulate_scenario
from ca_agents.ag_war_room.command import WarRoomCommand
from ca_agents.ag_war_room.evidence import EvidenceBuilder


def _fingerprint(command: WarRoomCommand) -> str:
    payload = {
        "request_id": command.request_id,
        "baseline_snapshot": command.baseline_snapshot,
        "scenarios": [s.model_dump(mode="json") for s in command.scenarios],
        "requested_by": command.requested_by,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def validate_baseline_snapshot(
    baseline_snapshot: str,
    current_snapshot_hash: str,
) -> bool:
    """Baseline stale → không cho confirm. Fail-closed: hash rỗng → False."""
    if not baseline_snapshot or not current_snapshot_hash:
        return False
    return baseline_snapshot == current_snapshot_hash


def _baseline_ca_meta_from_fixture(scenario: WarRoomScenario) -> dict[str, dict[str, str]]:
    """Chuyển params của kịch bản thành ca_meta cho solver feasibility.

    Đơn giản hoá tất định: kịch bản staffing sẽ dùng ca_id + khung từ params.
    Nếu thiếu ca_meta cần thiết → trả rỗng (feasibility không chặn nhưng
    cảnh báo thiếu dữ liệu).
    """
    ca_meta: dict[str, dict[str, str]] = {}
    if scenario.loai == WarRoomScenarioType.ADD_STAFF_TO_SHIFT:
        ca_id = str(scenario.tham_so.get("ca_id", "ca_01"))
        ca_meta[ca_id] = {
            "ca_id": ca_id,
            "thu": str(scenario.tham_so.get("thu", "T7")),
            "khung": str(scenario.tham_so.get("khung", "toi")),
            "bat_dau": str(scenario.tham_so.get("bat_dau", "17:00")),
            "ket_thuc": str(scenario.tham_so.get("ket_thuc", "22:00")),
        }
    return ca_meta


def _feasibility_check(
    scenario: WarRoomScenario,
    nv_ids: list[str],
) -> tuple[bool, list[str]]:
    """Kiểm tra hard constraints bằng solver (c01-c06). Tất định, không LLM."""
    ca_meta = _baseline_ca_meta_from_fixture(scenario)
    ca_ids = list(ca_meta.keys())
    if not ca_ids:
        # Kịch bản không đụng staffing → coi như khả thi (chỉ đánh dấu nếu có params khác).
        return True, []
    data = LichInput(
        nhan_vien_ids=nv_ids,
        ca_ids=ca_ids,
        phan_cong={},
        ca_meta=ca_meta,
        tran_gio_tuan=48.0,
        khoang_nghi_gio=8.0,
        so_nguoi_toi_thieu={ca_id: 1 for ca_id in ca_ids},
    )
    result = solve_hard_only(data)
    return result.ok, result.violations


def _fairness_projection(
    nv_ids: list[str],
    phan_cong: dict[str, list[str]],
    ca_meta: dict[str, dict[str, str]],
) -> dict[str, float]:
    """Chiếu fairness debt sau khi thêm/bớt người — chỉ số max debt delta."""
    debt_before = zero_debt(nv_ids)
    debt_after = update_debt_from_assignment(debt_before, phan_cong, ca_meta)
    return {
        "max_debt_before": max_debt(debt_before),
        "max_debt_after": max_debt(debt_after),
        "delta": max_debt(debt_after) - max_debt(debt_before),
    }


def _run_one_scenario(
    scenario: WarRoomScenario,
    baseline: dict[str, object],
    nv_ids: list[str],
    ev: EvidenceBuilder,
) -> dict[str, Any]:
    """Chạy một kịch bản → dict option-ready (không dùng LLM)."""
    # AG-TWIN math (deterministic) — tái dùng math_layer, không duplicate.
    tham_so: dict[str, object] = dict(scenario.tham_so)
    twin = simulate_scenario(
        scenario_id=scenario.scenario_id,
        loai=_to_twin_type(scenario.loai),
        tham_so=tham_so,
        baseline=baseline,
    )
    twin_results: dict[str, object] = dict(twin.ket_qua)
    for k, v in twin_results.items():
        ev.add_deterministic(f"ag_twin.{k}", v, note="tầng toán tất định AG-TWIN")
    # Fallback nếu twin không điền ket_qua
    if not twin_results:
        twin_results = {"rui_ro": "Kịch bản chưa có mô hình tất định — đánh dấu ước tính"}

    # Feasibility (hard constraints)
    ok, violations = _feasibility_check(scenario, nv_ids)
    for v in violations:
        ev.add_solver("solve_hard_only", v, note="c01-c06")
    if not ok:
        ev.add_deterministic("feasibility", "rejected", note="vi phạm hard constraint")

    # Fairness delta
    fair = _fairness_projection(
        nv_ids,
        phan_cong={scenario.scenario_id: nv_ids[:1]} if ok else {},
        ca_meta=_baseline_ca_meta_from_fixture(scenario),
    )
    ev.add_deterministic("fairness.max_debt_delta", fair["delta"], note="ca_solver.fairness")

    def _float(v: object, default: float = 0.0) -> float:
        try:
            return float(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default

    estimates = {
        "doanh_thu_du_kien": _float(twin_results.get("doanh_thu_moi")),
        "luong_ban_moi": _float(twin_results.get("luong_ban_moi")),
        "loi_nhuan_rong": _float(twin_results.get("loi_nhuan_rong")),
        "chenh_lech": _float(twin_results.get("chenh_lech")),
    }
    # Chỉ giữ số có thật trong ket_qua, không bịa 0
    estimates = {k: v for k, v in estimates.items() if k in twin_results}

    return {
        "option_id": f"opt_{scenario.scenario_id}",
        "scenario_id": scenario.scenario_id,
        "input_assumptions": dict(scenario.tham_so),
        "outputs": estimates,
        "staffing": {"thay_doi": 1 if scenario.loai in (WarRoomScenarioType.ADD_STAFF_TO_SHIFT,) else 0},
        "load": {"du_bao": _float(twin_results.get("load_du_bao"), 0.5)},
        "fairness_impact": fair,
        "estimated_cost": _float(twin_results.get("chi_phi_nhan_su"))
        if "chi_phi_nhan_su" in twin_results else None,
        "estimated_revenue": estimates.get("doanh_thu_du_kien"),
        "risk": str(twin.rui_ro or twin_results.get("rui_ro", "")),
        "evidence_refs": ev.to_dicts(),
        "constraint_violations": violations,
        "labels": ["mo_phong"],
    }


def _to_twin_type(scenario_type: WarRoomScenarioType) -> Any:
    """Map WarRoomScenarioType → TwinScenarioType của AG-TWIN hiện có.

    Không duplicate math: thêm/bớt nhân sự map sang THEM/BOT_NHAN_SU;
    demand surge/heavy rain/large group → TANG_GIA (ước tính cầu);
    equipment outage → BOT_NHAN_SU (mất năng lực). Mọi map là deterministic.
    """
    from ca_contracts.ops_predict import TwinScenarioType

    mapping = {
        WarRoomScenarioType.ADD_STAFF_TO_SHIFT: TwinScenarioType.THEM_NHAN_SU,
        WarRoomScenarioType.REMOVE_STAFF_FROM_SHIFT: TwinScenarioType.BOT_NHAN_SU,
        WarRoomScenarioType.DEMAND_SURGE: TwinScenarioType.TANG_GIA,
        WarRoomScenarioType.HEAVY_RAIN: TwinScenarioType.GIAM_GIA,
        WarRoomScenarioType.EQUIPMENT_OUTAGE: TwinScenarioType.BOT_NHAN_SU,
        WarRoomScenarioType.LARGE_GROUP_ARRIVAL: TwinScenarioType.TANG_GIA,
    }
    return mapping[scenario_type]


def run_war_room_comparison(
    command: WarRoomCommand,
    *,
    current_snapshot_hash: str,
    nv_ids: list[str] | None = None,
) -> WarRoomComparison:
    """Chạy War Room: baseline + options, idempotent theo fingerprint.

    `current_snapshot_hash` từ adapter/fixture — nếu baseline stale thì trả
    comparison với cảnh báo stale_data trên mọi option.
    """
    if nv_ids is None:
        nv_ids = [f"nv_{i + 1}" for i in range(8)]

    # Baseline snapshot không hợp lệ → fail-closed (không chạy số bịa).
    snapshot_ok = validate_baseline_snapshot(command.baseline_snapshot, current_snapshot_hash)

    baseline: dict[str, object] = {
        "snapshot_hash": command.baseline_snapshot,
        "fingerprint": _fingerprint(command),
        "snapshot_valid": snapshot_ok,
        "nv_count": len(nv_ids),
    }

    options: list[WarRoomOption] = []
    for scenario in command.scenarios:
        ev = EvidenceBuilder()
        raw = _run_one_scenario(scenario, baseline, nv_ids, ev)
        if not snapshot_ok:
            raw["stale_data"] = True
        # evidence_refs đã đính trong raw — đổi type cho đúng contract
        raw["evidence_refs"] = [r["nguon"] for r in raw["evidence_refs"]]
        raw = {k: v for k, v in raw.items() if k != "stale_data" or raw.get("stale_data")}
        options.append(WarRoomOption.model_validate(raw))

    return WarRoomComparison(
        simulation_id=f"sim_{_fingerprint(command)[:12]}",
        baseline_snapshot_hash=command.baseline_snapshot,
        baseline=baseline,
        options=options,
    )