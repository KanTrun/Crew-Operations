"""Discover — nhóm quyết định lặp lại thành RuleCandidate tất định.

Chỉ tạo candidate khi đủ bằng chứng tối thiểu (mặc định 3) và không có
counterexample mạnh. Condition/effect keys từ closed registry (RuleConditionKey),
không nhận biểu thức thực thi tuỳ ý.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from ca_contracts import RuleCandidate
from ca_contracts.grand_experience import (
    RuleConditionKey,
    RuleConditionMap,
)

MIN_EVIDENCE = 3


@dataclass
class DecisionSignal:
    """Một tín hiệu quyết định lặp lại (từ sự kiện/rescue/twin)."""

    signal_id: str
    decision: str
    day_part: str | None = None
    station: str | None = None
    skill: str | None = None
    demand_band: str | None = None
    absence_type: str | None = None
    outcome: str = ""
    source_kind: str = "decision"
    occurred_at: str = ""


def _hash(id_parts: list[str]) -> str:
    raw = json.dumps(id_parts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _condition_from(signal: DecisionSignal) -> RuleConditionMap:
    """Map signal → condition với field registry của experience (RuleConditionKey).

    Trước khi vào vong_doi, bridge sẽ map về fields VF-RULE (khung/vi_tri/
    so_nguoi) — xem `test_experience_rule_bridge` và `_to_vf_condition`.
    """
    cond: RuleConditionMap = {}
    if signal.day_part:
        cond[RuleConditionKey.DAY_PART.value] = signal.day_part
    if signal.station:
        cond[RuleConditionKey.STATION.value] = signal.station
    if signal.skill:
        cond[RuleConditionKey.SKILL.value] = signal.skill
    if signal.demand_band:
        cond[RuleConditionKey.DEMAND_BAND.value] = signal.demand_band
    if signal.absence_type:
        cond[RuleConditionKey.ABSENCE_TYPE.value] = signal.absence_type
    return cond


def to_vf_condition(condition: RuleConditionMap) -> RuleConditionMap:
    """Map condition experience → fields VF-RULE (để validate_rule pass).

    Chỉ giữ fields VF-RULE hợp lệ (thu/khung/vi_tri/so_nguoi). Deterministic,
    không bịa giá trị:
    - day_part -> khung
    - station  -> vi_tri
    - demand_band -> so_nguoi (xấp xỉ: cao=2, thấp=1)
    - thu (nếu có)
    - skill / absence_type -> bỏ qua (không có field VF-RULE tương đương)
    """
    out: RuleConditionMap = {}
    mapping = {
        "day_part": "khung",
        "station": "vi_tri",
        "thu": "thu",
    }
    for k, v in condition.items():
        if k == "demand_band":
            out["so_nguoi"] = 2 if str(v) == "cao" else 1
            continue
        target = mapping.get(k)
        if target:
            out[target] = v
    return out


def group_decisions(signals: list[DecisionSignal]) -> list[dict[str, Any]]:
    """Nhóm tín hiệu theo (decision, condition tuple) — deterministic."""
    groups: dict[str, list[DecisionSignal]] = {}
    for sig in signals:
        key = json.dumps(
            {
                "decision": sig.decision,
                "condition": sorted(_condition_from(sig).items()),
            },
            sort_keys=True,
        )
        groups.setdefault(key, []).append(sig)
    result = []
    for key, items in groups.items():
        meta = json.loads(key)
        result.append(
            {
                "key": key,
                "decision": meta["decision"],
                "condition": dict(meta["condition"]),
                "signals": items,
                "count": len(items),
            }
        )
    return result


def discover_rule_candidates(
    signals: list[DecisionSignal],
    *,
    min_evidence: int = MIN_EVIDENCE,
    snapshot_hash: str,
) -> list[RuleCandidate]:
    """Tạo candidate khi đủ bằng chứng — không bịa khi thiếu."""

    def _sentence(group: dict[str, Any]) -> str:
        decision = str(group["decision"])
        cond = group["condition"]
        if cond:
            parts = ", ".join(f"{k} = {v}" for k, v in sorted(cond.items()))
            return f"Nếu {parts} thì {decision}"
        return f"Nếu có quyết định lặp lại thì {decision}"

    candidates: list[RuleCandidate] = []
    for group in group_decisions(signals):
        items = group["signals"]
        if len(items) < min_evidence:
            continue
        # counterexample: cùng decision nhưng outcome trái (fail)
        counterexamples = [
            s.signal_id for s in items if s.outcome and s.outcome.lower() in {"fail", "no", "reject"}
        ]
        evidence_refs = [s.signal_id for s in items[:min_evidence]]
        # confidence = tỷ lệ outcome thành công / tổng
        ok = sum(1 for s in items if s.outcome and s.outcome.lower() in {"ok", "yes", "approve"})
        confidence = round(ok / len(items), 2) if items else 0.0

        candidates.append(
            RuleCandidate(
                candidate_id=f"rc_{_hash([group['key']])}",
                condition=RuleConditionMap(group["condition"]),
                effect={"decision": str(group["decision"])},
                sentence=_sentence(group),
                evidence_refs=evidence_refs,
                counterexample_refs=counterexamples,
                confidence=confidence,
                source_kind=items[0].source_kind,
                created_from_snapshot_hash=snapshot_hash,
            )
        )
    return candidates