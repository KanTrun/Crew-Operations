"""Retrieval — deterministic filter theo anchor/time/status/consent + role.

Fail-closed: revoked/deleted/expired không bao giờ được retrieve; pending
(status=draft) bị loại khỏi answer đã xác nhận. Memory store qua storage
adapter (không phải browser store).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

from ca_contracts import (
    ExperienceMemory,
    MemoryConsentStatus,
    MemoryQuery,
    MemoryStatus,
    MemoryVisibility,
)
from ca_contracts.grand_experience import ExperienceRole


class MemoryStore(Protocol):
    """Protocol storage cho memory (fixture/persistent)."""

    def list_memories(self) -> list[dict[str, Any]]: ...

    def add_memory(self, memory: ExperienceMemory) -> None: ...

    def get_memory(self, memory_id: str) -> ExperienceMemory | None: ...


class MemoryRepository:
    """Repository trong-memory tách biệt — không chứa raw audio."""

    def __init__(self) -> None:
        self._rows: dict[str, ExperienceMemory] = {}

    def list_memories(self) -> list[dict[str, Any]]:
        return [dict(m.model_dump(mode="json")) for m in self._rows.values()]

    def all_memories(self) -> list[ExperienceMemory]:
        return list(self._rows.values())

    def add_memory(self, memory: ExperienceMemory) -> None:
        self._rows[memory.memory_id] = memory

    def get_memory(self, memory_id: str) -> ExperienceMemory | None:
        return self._rows.get(memory_id)


def _role_visible(memory: ExperienceMemory, role: ExperienceRole) -> bool:
    """Projection theo role — cắt private/mistmatch visibility."""
    if memory.status == MemoryStatus.DELETED:
        return False
    if memory.consent_status == MemoryConsentStatus.REVOKED:
        return False
    if memory.retention_until and memory.retention_until <= datetime.now(UTC):
        return False
    if memory.visibility == MemoryVisibility.PUBLIC:
        return True
    if memory.visibility == MemoryVisibility.MANAGER:
        return role in (ExperienceRole.QUAN_LY, ExperienceRole.CHU_QUAN)
    if memory.visibility == MemoryVisibility.STAFF:
        return role != ExperienceRole.KHACH
    # private — chỉ owner hoặc manager
    return role in (ExperienceRole.QUAN_LY, ExperienceRole.CHU_QUAN)


def retrieve_filtered(
    store: MemoryStore,
    query: MemoryQuery,
) -> list[ExperienceMemory]:
    """Retrieve theo bộ lọc tất định. KHÔNG bao giờ trả revoked/deleted/hết hạn."""
    out: list[ExperienceMemory] = []
    now = datetime.now(UTC)
    for row in store.list_memories():
        memory = ExperienceMemory.model_validate(row)
        # Consent/trạng thái cơ bản
        if memory.consent_status in (MemoryConsentStatus.REVOKED, MemoryConsentStatus.EXPIRED):
            continue
        if memory.status == MemoryStatus.DELETED:
            continue
        if memory.retention_until and memory.retention_until <= now:
            continue
        # Role visibility
        if not _role_visible(memory, query.role):
            continue
        # Filter theo anchor
        if query.anchor_id and memory.anchor_id != query.anchor_id:
            continue
        # Filter status
        if query.status is not None and memory.status != query.status:
            continue
        if query.consent_status is not None and memory.consent_status != query.consent_status:
            continue
        # Bounded keyword (deterministic)
        if query.keyword and query.keyword.lower() not in memory.content.lower():
            continue
        out.append(memory)
    # Stable ordering theo created time (không hash mutation)
    return out