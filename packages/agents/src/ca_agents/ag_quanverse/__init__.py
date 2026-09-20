"""AG-QUANVERSE — Living Cafe OS (Phase 06).

Server-side role projection (LivingCafeSnapshot strip fields truoc khi tra).
Flavor recommendation: catalog filter/scorer deterministic — khong infer dung
not. Mode activation: proposal + xac nhan manager. AR-lite sau 2D/WebGL.
"""

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
]