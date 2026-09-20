"""War Room command normalization — tất định, LLM chỉ gợi ý ID, server verify."""

from __future__ import annotations

from ca_contracts import WarRoomScenario
from pydantic import BaseModel, Field


class WarRoomCommand(BaseModel):
    """Command chuẩn hoá từ yêu cầu "nếu... thì..." — đã verify ID/params."""

    request_id: str = Field(min_length=1)
    baseline_snapshot: str = Field(min_length=8)
    scenarios: list[WarRoomScenario] = Field(min_length=1, max_length=10)
    requested_by: str = Field(min_length=1)


def normalize_command(
    request_id: str,
    baseline_snapshot: str,
    scenarios: list[WarRoomScenario],
    requested_by: str,
) -> WarRoomCommand:
    """Chuẩn hoá command — Pydantic fail-closed từng field, không viết tay.

    - Unknown scenario type bị reject (closed enum).
    - Unknown params KHÔNG được ngầm default — phải khớp schema.
    - Thứ tự scenarios giữ nguyên (stable ordering).
    """
    return WarRoomCommand(
        request_id=request_id,
        baseline_snapshot=baseline_snapshot,
        scenarios=scenarios,
        requested_by=requested_by,
    )