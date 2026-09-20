"""Hợp đồng dữ liệu — HỒN QUÁN Spatial Memory (plan 260920-1442 Phase 05).

Memory data model (Phase 05): spatial_anchors + experience_events +
experience_memories + memory_audit. KHÔNG vector search trong MVP — dùng
deterministic filtering + bounded keyword. Vector retrieval là ADR sau.

Consent: customer preference memory yêu cầu consent tường minh + retention +
delete path. Không nhận diện khuôn mặt/biometric.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from ca_contracts.grand_experience import (
    ExperienceRole,
    MemoryConsentStatus,
    MemoryStatus,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnchorQuery(BaseModel):
    """Query anchor: resolved + role/consent context."""

    anchor_id: str = Field(min_length=1)
    store_id: str = "quan_01"
    role: ExperienceRole = ExperienceRole.NHAN_VIEN
    requester_id: str = Field(min_length=1)


class MemoryQuery(BaseModel):
    """Query ký ức theo anchor/time/status/role — deterministic filter."""

    store_id: str = "quan_01"
    anchor_id: str | None = None
    from_time: datetime | None = None
    to_time: datetime | None = None
    status: MemoryStatus | None = None
    consent_status: MemoryConsentStatus | None = None
    role: ExperienceRole = ExperienceRole.NHAN_VIEN
    requester_id: str = Field(min_length=1)
    keyword: str | None = Field(default=None, max_length=200)


class MemoryProposal(BaseModel):
    """Đề xuất tạo memory từ text/voice — chưa lưu confirmed."""

    proposal_id: str = Field(min_length=1)
    anchor_id: str = Field(min_length=1)
    store_id: str = "quan_01"
    content: str = Field(min_length=1, max_length=4000)
    owner_scope: str = Field(min_length=1)
    visibility: Literal["private", "staff", "manager", "public"] = "staff"
    proposed_by: str = Field(min_length=1)
    source_event_ids: list[str] = Field(default_factory=list)
    snapshot_hash: str = Field(min_length=8)


class MemoryConsentRequest(BaseModel):
    """Khách/manager cấp hoặc thu hồi consent — có audit."""

    memory_id: str = Field(min_length=1)
    consent: MemoryConsentStatus
    actor_id: str = Field(min_length=1)
    actor_role: ExperienceRole = ExperienceRole.NHAN_VIEN
    reason: str = ""


class MemoryAuditEntry(BaseModel):
    """Audit dòng memory — không chứa raw audio/secret."""

    audit_id: str = Field(min_length=1)
    memory_id: str = Field(min_length=1)
    action: Literal[
        "propose", "consent_grant", "consent_revoke", "confirm",
        "expire", "delete", "supersede",
    ]
    actor_id: str = Field(min_length=1)
    reason: str = ""
    occurred_at: datetime = Field(default_factory=_utc_now)


class GroundedAnswer(BaseModel):
    """Trả lời grounded: citations + optional proposal. Không bao giờ bịa."""

    answer_id: str = Field(min_length=1)
    answer_text: str = Field(min_length=1)
    citations: list[str] = Field(default_factory=list)
    memory_ids: list[str] = Field(default_factory=list)
    proposal_id: str | None = None
    unsupported_claims: list[str] = Field(default_factory=list)
    grounded: bool = True


class TourStep(BaseModel):
    """Một bước tour — anchor deterministic + narration có nguồn."""

    step_id: str = Field(min_length=1)
    anchor_id: str = Field(min_length=1)
    narrative: str = Field(min_length=1)
    citation_memory_ids: list[str] = Field(default_factory=list)


class TourPlan(BaseModel):
    """Tour planner: chuỗi anchor đóng (không LLM thêm sự kiện chưa có nguồn)."""

    tour_id: str = Field(min_length=1)
    steps: list[TourStep] = Field(min_length=1)
    grounded: bool = True


class VoiceTurnRequest(BaseModel):
    """Một lượt voice — transcript + context; trả grounded answer."""

    conversation_id: str = Field(min_length=1)
    transcript: str = Field(min_length=1, max_length=4000)
    store_id: str = "quan_01"
    anchor_id: str | None = None
    role: ExperienceRole = ExperienceRole.NHAN_VIEN
    requester_id: str = Field(min_length=1)


class VoiceTurnResponse(BaseModel):
    """Kết quả voice turn — transcript, response, citations, optional proposal."""

    turn_id: str = Field(min_length=1)
    transcript: str
    response_text: str
    citations: list[str] = Field(default_factory=list)
    audio_ref: str | None = None
    proposal: MemoryProposal | None = None
    grounded: bool = True