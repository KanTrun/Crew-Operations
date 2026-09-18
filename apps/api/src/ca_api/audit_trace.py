"""Truy vết actor cho sổ vết hệ thống.

Mỗi vết (audit) cần trả lời được 3 câu:
  1. Ai làm?            -> actor (nv_id / "system" / "guest" / tên agent)
  2. Là người hay agent? -> actor_type (human / agent / system / guest)
  3. Ai điều khiển?      -> controller_user_id (người duyệt / kích hoạt agent)

Module này là nơi duy nhất định nghĩa ActorType và registry tên agent, để
backend (persist, copilot, worker) và frontend dùng chung một nguồn sự thật.
"""

from __future__ import annotations

from enum import Enum


class ActorType(str, Enum):
    """Phân loại tác nhân thực hiện một vết."""

    HUMAN = "human"      # người dùng thật (nv_id)
    AGENT = "agent"      # agent tự chạy (ag_copilot, ag_scheduler, ...)
    SYSTEM = "system"    # hệ thống (worker, cron, middleware)
    GUEST = "guest"      # chưa đăng nhập (nv_guest)


# Registry tên agent — một nơi duy nhất. Key là tên module agent, value là
# nhãn hiển thị thân thiện.
AGENT_NAMES: dict[str, str] = {
    "ag_copilot": "AG-COPILOT",
    "ag_scheduler": "AG-SCHEDULER",
    "ag_mailwriter": "AG-MAILWRITER",
    "ag_pricing": "AG-PRICING",
    "ag_sop": "AG-SOP",
    "ag_tkb": "AG-TKB",
    "ag_waste": "AG-WASTE",
    "ag_barista": "AG-BARISTA",
    "ag_concierge": "AG-CONCIERGE",
    "ag_supervisor": "AG-SUPERVISOR",
    "ag_meeting": "AG-MEETING",
    "ag_msg": "AG-MSG",
    "ag_brief": "AG-BRIEF",
    "ag_explain": "AG-EXPLAIN",
    "ag_handover": "AG-HANDOVER",
    "ag_fbpage": "AG-FBPAGE",
    "ag_trend": "AG-TREND",
    "ag_mail": "AG-MAIL",
    "ag_rule": "AG-RULE",
    "ag_voc": "AG-VOC",
}

# Các giá trị ai đặc biệt không phải nv_id người thật.
_SYSTEM_AI = {"system", "unknown", "fb_policy_engine", "fb_moderation_block"}
_GUEST_AI = {"guest", "nv_guest"}


def resolve_actor_type(ai: str | None) -> ActorType:
    """Suy ra actor_type từ giá trị `ai` khi không được truyền tường minh.

    Dùng làm fallback cho dữ liệu cũ / các điểm ghi vết chưa truyền actor_type.
    """
    raw = (ai or "").strip().lower()
    if raw in _SYSTEM_AI:
        return ActorType.SYSTEM
    if raw in _GUEST_AI:
        return ActorType.GUEST
    if raw in AGENT_NAMES:
        return ActorType.AGENT
    return ActorType.HUMAN


def agent_label(agent_name: str | None) -> str | None:
    """Nhãn hiển thị thân thiện cho tên agent; None nếu không biết."""
    if not agent_name:
        return None
    return AGENT_NAMES.get(agent_name, agent_name)