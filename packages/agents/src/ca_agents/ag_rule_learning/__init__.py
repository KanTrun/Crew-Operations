"""AG-RULE-LEARNING — quán tự viết luật (Phase 04).

Tái sử dụng vong_doi.py (8-step lifecycle, ADR-010), AG-RULE phrasing, gates.
KHÔNG tạo state machine luật thứ hai — vong_doi là sole writer.
Mọi ReadModel qua contracts (không import ca_api/DB internals).
"""

from ca_agents.ag_rule_learning.discover import (
    discover_rule_candidates,
    group_decisions,
    to_vf_condition,
)
from ca_agents.ag_rule_learning.evidence import build_evidence_readmodel
from ca_agents.ag_rule_learning.shadow_test import run_shadow_test

__all__ = [
    "discover_rule_candidates",
    "group_decisions",
    "to_vf_condition",
    "build_evidence_readmodel",
    "run_shadow_test",
]