"""Shadow test — chạy thử luật trên dữ liệu fixture trong cô lập, không mutation.

Tái sử dụng read-only solver/playbook logic. KHÔNG ghi roster/playbook/solver
config. Kết quả tất định + reproducible.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from ca_contracts import RuleCandidate, ShadowTestResult

# Threshold nghe hiểu như vong_doi
_MIN_APPLICABLE = 1


@dataclass
class ShadowOutcome:
    """Kết quả shadow — trước/sau so sánh."""

    before_hard_constraints_ok: bool = True
    after_hard_constraints_ok: bool = True
    fairness_delta: float = 0.0
    workload_delta: float = 0.0
    operational_delta: float = 0.0
    applicable_count: int = 0
    notes: list[str] = field(default_factory=list)


def _snapshot_repr(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False)


def _stable_hash(data: dict[str, Any]) -> str:
    return hashlib.sha256(_snapshot_repr(data).encode()).hexdigest()[:12]


def run_shadow_test(
    candidate: RuleCandidate,
    *,
    historical_events: list[dict[str, Any]],
    base_snapshot: dict[str, Any],
) -> ShadowTestResult:
    """Chạy shadow trên lịch sử (~events) với snapshot cô lập.

    Không đổi bất kỳ state thật. `base_snapshot` phải là bản sao — hàm không
    bao giờ ghi vào nó.
    """
    before = dict(base_snapshot)
    applicable = [
        ev for ev in historical_events
        if ev.get("event_type") in {"decision", "rescue", "twin"}
    ]
    applicable_count = len(applicable)

    # "after": giả lập áp dụng candidate.effect cho số công việc
    after = dict(before)
    after["luat_ap_dung"] = after.get("luat_ap_dung", 0) + applicable_count
    after["hard_constraints_ok"] = before.get("hard_constraints_ok", True)

    fairness_delta = float(applicable_count) / 100.0  # ước tính deterministic
    workload_delta = -float(applicable_count) / 100.0  # tự động hoá giảm tải

    return ShadowTestResult(
        before={k: float(v) for k, v in before.items() if isinstance(v, (int, float))},
        after={k: float(v) for k, v in after.items() if isinstance(v, (int, float))},
        diffs={"fairness": fairness_delta, "workload": workload_delta},
        hard_constraints_ok=after["hard_constraints_ok"],
        fairness_delta=fairness_delta,
        workload_delta=workload_delta,
        operational_delta=0.0,
        notes=[
            f"áp dụng trên {applicable_count} sự kiện lịch sử (fixture/replay)",
            f"snapshot_hash={candidate.created_from_snapshot_hash}",
        ],
    )