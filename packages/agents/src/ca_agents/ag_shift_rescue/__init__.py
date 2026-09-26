"""AG-SHIFT-RESCUE — cứu hộ ca khi nhân viên vắng đột xuất (Phase 03).

KHÔNG phải scheduler mới: dùng solver hard constraints (c01-c06), fairness
debt, và lifecycle hiện có. Ranking tất định theo policy version, không LLM.
Không bao giờ đề xuất người vi phạm hard constraint là "an toàn".
"""

from ca_agents.ag_shift_rescue.eligibility import (
    eligibility_reasons,
    filter_eligible,
)
from ca_agents.ag_shift_rescue.intake import (
    normalize_absence,
    resolve_shift_identity,
)
from ca_agents.ag_shift_rescue.ranking import (
    RANKING_POLICY_VERSION,
    rank_candidates,
)

__all__ = [
    "filter_eligible",
    "eligibility_reasons",
    "normalize_absence",
    "resolve_shift_identity",
    "rank_candidates",
    "RANKING_POLICY_VERSION",
]