"""Shift Rescue policy — state machine cho case cứu hộ (opsengine, Phase 03).

States: reported -> resolving -> candidates_ready -> proposed -> invited ->
responded -> confirmed/expired/cancelled.

Mọi transition đều idempotent-safe (cùng input → cùng output) và không tự
mutation roster — confirm phải qua lifecycle hiện có.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RescueState(StrEnum):
    REPORTED = "reported"
    RESOLVING = "resolving"
    CANDIDATES_READY = "candidates_ready"
    PROPOSED = "proposed"
    INVITED = "invited"
    RESPONDED = "responded"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


VALID_TRANSITIONS: dict[RescueState, frozenset[RescueState]] = {
    RescueState.REPORTED: frozenset({RescueState.RESOLVING}),
    RescueState.RESOLVING: frozenset({RescueState.CANDIDATES_READY, RescueState.EXPIRED, RescueState.CANCELLED}),
    RescueState.CANDIDATES_READY: frozenset({RescueState.PROPOSED, RescueState.EXPIRED, RescueState.CANCELLED}),
    RescueState.PROPOSED: frozenset({RescueState.INVITED, RescueState.EXPIRED, RescueState.CANCELLED}),
    RescueState.INVITED: frozenset({RescueState.RESPONDED, RescueState.EXPIRED, RescueState.CANCELLED}),
    RescueState.RESPONDED: frozenset({RescueState.CONFIRMED, RescueState.EXPIRED, RescueState.CANCELLED}),
    RescueState.CONFIRMED: frozenset(),
    RescueState.EXPIRED: frozenset(),
    RescueState.CANCELLED: frozenset(),
}


@dataclass
class RescueCaseState:
    """Trạng thái một case (được lưu qua kv adapter — không phải browser store)."""

    case_id: str
    state: RescueState = RescueState.REPORTED
    schedule_snapshot_hash: str = ""
    invited_candidates: list[str] = field(default_factory=list)
    responded_candidate_id: str | None = None
    confirmed_candidate_id: str | None = None
    audit_events: list[dict[str, str]] = field(default_factory=list)

    def can_transition(self, target: RescueState) -> bool:
        return target in VALID_TRANSITIONS.get(self.state, frozenset())

    def transition(
        self,
        target: RescueState | str,
        *,
        actor: str,
        note: str = "",
    ) -> None:
        """Chuyển trạng thái — fail-closed nếu không hợp lệ."""
        if isinstance(target, str):
            target = RescueState(target)
        if not self.can_transition(target):
            raise ValueError(
                f"transition không hợp lệ: {self.state} -> {target}"
            )
        self.state = target
        self.audit_events.append(
            {"actor": actor, "action": f"{target}", "note": note}
        )

    def invite(self, candidate_ids: list[str], actor: str) -> None:
        """Invite idempotent: gọi lại chỉ cập nhật một lần, không gửi trùng."""
        # Idempotent: nếu đã INVITED và candidate đã có → chỉ trả về, không gửi.
        if self.state == RescueState.INVITED and all(
            c in self.invited_candidates for c in candidate_ids
        ):
            return
        if self.state != RescueState.PROPOSED:
            raise ValueError("phải PROPOSED trước khi INVITED")
        # Xoá trùng + giữ thứ tự (idempotent)
        seen = set(self.invited_candidates)
        new_candidates = [c for c in candidate_ids if c not in seen]
        if not new_candidates:
            return  # đã invite rồi — idempotent
        self.invited_candidates.extend(candidate_ids)
        self.transition(RescueState.INVITED, actor=actor, note="invites sent")

    def respond(self, candidate_id: str, accept: bool, actor: str) -> None:
        """Ghi nhận phản hồi. Reject không chuyển state (chờ ứng viên khác)."""
        if self.state != RescueState.INVITED:
            raise ValueError("phải INVITED để respond")
        self.responded_candidate_id = candidate_id
        if accept:
            self.transition(RescueState.RESPONDED, actor=actor, note=f"accept {candidate_id}")
        else:
            self.audit_events.append(
                {"actor": actor, "action": "reject", "note": candidate_id}
            )

    def confirm(self, candidate_id: str, actor: str) -> None:
        """Confirm phải từ RESPONDED (hoặc PROPOSED nếu manager quyết ngay)."""
        if self.state not in (RescueState.RESPONDED, RescueState.PROPOSED):
            raise ValueError("phải RESPONDED/PROPOSED để confirm")
        self.confirmed_candidate_id = candidate_id
        self.transition(RescueState.CONFIRMED, actor=actor, note=f"confirm {candidate_id}")

    def expire(self, actor: str = "system") -> None:
        self.transition(RescueState.EXPIRED, actor=actor, note="expired")

    def cancel(self, actor: str, reason: str = "") -> None:
        self.transition(RescueState.CANCELLED, actor=actor, note=reason)