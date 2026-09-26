"""Grand AI Experience Portfolio — package tất định, không LLM ở tầng này.

Ranh giới: mô-đun này KHÔNG được import `ca_api`, `ca_playbook`, DB internals
hay web. Chỉ đọc dữ liệu qua `ExperienceReadAdapter` và xuất kết quả tất định
(ADR-002), dùng proposal/consent để mọi mutation chờ người quyết (ADR-008).
"""

from ca_agents.grand_experience.replay import (
    FixtureReader,
    NullReader,
    load_events,
    load_scenarios,
    load_spatial_map,
    replay_fingerprint,
)

__all__ = [
    "FixtureReader",
    "NullReader",
    "load_events",
    "load_scenarios",
    "load_spatial_map",
    "replay_fingerprint",
]