"""ExperienceReadAdapter — ranh giới đọc dữ liệu giữa experience và NHỊP QUÁN.

Chỉ gọi public services của `ca_agents` / `ca_ops` (không import DB, không
import `ca_api`). Khi chưa có adapter production, phải trả về FixtureReader
(replay) — fail-closed, không bịa số.
"""

from __future__ import annotations

import os
from typing import Any, Protocol

from ca_contracts import SpatialAnchor

from ca_agents.grand_experience.replay import FixtureReader


class ReadAdapter(Protocol):
    """Protocol nhỏ — experience layer chỉ phụ thuộc interface này."""

    def list_events(self, **filters: Any) -> list[dict[str, Any]]: ...
    def event_by_id(self, event_id: str) -> dict[str, Any] | None: ...
    def list_anchors(self) -> list[SpatialAnchor]: ...
    def list_scenarios(self) -> list[dict[str, Any]]: ...
    def fingerprint(self) -> str: ...


def resolve_experience_read_adapter() -> ReadAdapter:
    """Chọn adapter đọc cho experience theo môi trường.

    - `NHIPQUAN_EXPERIENCE_READ_ADAPTER=production` → production adapter.
    - mặc định (replay/fixture) → FixtureReader, không mở mạng.
    Production adapter ở phase sau sẽ gọi public services (nhan_vien, lich,
    solver...) qua các hàm public của ca_agents/ca_ops — không DB internals.
    """
    mode = os.environ.get("NHIPQUAN_EXPERIENCE_READ_ADAPTER", "").strip().lower()
    if mode == "production":
        return ProductionExperienceAdapter()
    return FixtureReader()


class ProductionExperienceAdapter:
    """Adapter production mở rộng dần theo phase 02-06.

    Phase 01 MVP: chỉ đọc fixture để giữ tất định (ADR-002). Các phase sau bổ
    sung mapping sang public services (ag_twin.simulate_scenario, nhan_vien...)
    qua hàm public — không truy cập trực tiếp DB.
    """

    def __init__(self) -> None:
        self._fixture = FixtureReader()

    def list_events(self, **filters: Any) -> list[dict[str, Any]]:
        return self._fixture.list_events(**filters)

    def event_by_id(self, event_id: str) -> dict[str, Any] | None:
        return self._fixture.event_by_id(event_id)

    def list_anchors(self) -> list[SpatialAnchor]:
        return self._fixture.list_anchors()

    def list_scenarios(self) -> list[dict[str, Any]]:
        return self._fixture.list_scenarios()

    def fingerprint(self) -> str:
        return self._fixture.fingerprint()