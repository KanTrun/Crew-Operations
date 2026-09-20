"""Intake — normalize báo vắng thành AbsenceCommand tất định.

Parser (LLM) có thể GỢI Ý id, nhưng resolver phải verify với store hiện có
(danh sách nhân viên + lịch). Ambiguous → yêu cầu làm rõ, không gửi invite.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AbsenceCommand(BaseModel):
    """Command đã chuẩn hoá báo vắng."""

    case_id: str = Field(min_length=1)
    store_id: str = Field(default="quan_01")
    absence_nv_id: str = Field(min_length=1)
    shift_id: str = Field(min_length=1)
    reported_by: str = Field(min_length=1)
    reason: str = ""
    schedule_snapshot_hash: str = Field(min_length=8)


def normalize_absence(
    *,
    case_id: str,
    absence_nv_id: str,
    shift_id: str,
    reported_by: str,
    reason: str = "",
    schedule_snapshot_hash: str,
) -> AbsenceCommand:
    """Tạo AbsenceCommand đã validate — fail-closed mọi field bắt buộc."""
    return AbsenceCommand(
        case_id=case_id,
        absence_nv_id=absence_nv_id,
        shift_id=shift_id,
        reported_by=reported_by,
        reason=reason,
        schedule_snapshot_hash=schedule_snapshot_hash,
    )


def resolve_shift_identity(
    *,
    known_shift_ids: set[str],
    suggested_shift_id: str,
) -> str:
    """Verify shift id với store. Không khớp → ném (gọi tầng trên yêu cầu làm rõ)."""
    if suggested_shift_id not in known_shift_ids:
        raise ValueError(
            f"shift_id không xác định: {suggested_shift_id}. "
            "Cần làm rõ ca/thời gian trước khi tìm người bù."
        )
    return suggested_shift_id