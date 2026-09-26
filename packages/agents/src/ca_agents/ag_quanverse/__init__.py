"""AG-QUANVERSE — Living Cafe OS (Phase 06).

Server-side role projection (LivingCafeSnapshot strip fields truoc khi tra).
Flavor recommendation: catalog filter/scorer deterministic — khong infer dung
not. Mode activation: proposal + xac nhan manager. AR-lite sau 2D/WebGL.

Them 2026-09-26: `brief` (tong hop TAT DINH theo trang) va `assistant` (dien dat
cau tra loi tren brief). `assistant` KHONG tinh toan nghiep vu — moi con so den
tu `brief`, LLM chi duoc dien dat lai va phai qua cong grounding.
"""

from ca_agents.ag_quanverse.assistant import (
    answer_question,
    audit_answer,
)
from ca_agents.ag_quanverse.brief import (
    PageFacts,
    brief_living_map,
    brief_rules,
    brief_shift_rescue,
    brief_spatial_memory,
    brief_war_room,
    build_brief,
)
from ca_agents.ag_quanverse.flavor import (
    FlavorPreference,
    recommend_from_taste,
    scorer,
)
from ca_agents.ag_quanverse.modes import (
    allowed_mode_activation_roles,
    can_activate_mode,
)

__all__ = [
    "FlavorPreference",
    "recommend_from_taste",
    "scorer",
    "allowed_mode_activation_roles",
    "can_activate_mode",
    "PageFacts",
    "brief_living_map",
    "brief_war_room",
    "brief_shift_rescue",
    "brief_rules",
    "brief_spatial_memory",
    "build_brief",
    "answer_question",
    "audit_answer",
]