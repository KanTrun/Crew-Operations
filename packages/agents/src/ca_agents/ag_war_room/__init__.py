"""AG-WAR-ROOM — điều phối War Room (Phase 02, plan 260920-1442).

Bao bọc AG-TWIN math + CP-SAT feasibility + fairness thành so sánh đa phương
án tất định. LLM KHÔNG cung cấp số — tầng này chạy 100% deterministic.

Nguyên tắc (plan mục "Safety"):
- LLM chỉ parse intent. Không LLM cung cấp numeric output.
- Math layer (AG-TWIN / math_layer) sở hữu mọi con số.
- CP-SAT/gates sở hữu hard constraints. Phương án có lợi nhuận nhưng vi phạm
  hard constraint VẪN bị loại.
- Simulation Idempotent theo fingerprint — cùng input → cùng output.
"""

from ca_agents.ag_war_room.command import (
    WarRoomCommand,
    normalize_command,
)
from ca_agents.ag_war_room.orchestrator import (
    run_war_room_comparison,
    validate_baseline_snapshot,
)

__all__ = [
    "WarRoomCommand",
    "normalize_command",
    "run_war_room_comparison",
    "validate_baseline_snapshot",
]