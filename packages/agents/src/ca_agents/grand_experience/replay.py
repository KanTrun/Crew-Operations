"""Replay tất định cho Grand AI Experience — hoạt động offline, không mạng.

`CA_AGENT_MODE=replay` + `experience_read_mode=replay` (hoặc auto-detect) dùng
FixtureReader. Mọi output phải byte-deterministic khi JSON object key order
thay đổi (dùng sort_keys).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Protocol

from ca_contracts import SpatialAnchor

_HERE = Path(__file__).resolve()


def _find_fixture_dir() -> Path:
    """Đi lên từ module cho tới khi tìm thấy `data/fixtures/grand_experience`.

    Không phụ thuộc index parents (editable install có thể chen site-packages).
    Env `NHIPQUAN_GRAND_EXPERIENCE_FIXTURE` override cho deployment.
    """
    env_override = os.environ.get("NHIPQUAN_GRAND_EXPERIENCE_FIXTURE")
    if env_override:
        return Path(env_override).resolve()
    target = Path("data") / "fixtures" / "grand_experience"
    for parent in (_HERE, *_HERE.parents):
        candidate = parent / target
        if candidate.is_dir():
            return candidate.resolve()
    # Fallback: repo root theo cwd (nơi chạy test)
    cwd_candidate = Path.cwd() / target
    if cwd_candidate.is_dir():
        return cwd_candidate.resolve()
    raise FileNotFoundError(f"không tìm thấy fixture dir: {target}")


_DEFAULT_FIXTURE_DIR = _find_fixture_dir()


def _read_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"fixture phải là JSON object: {path}")
    return loaded


def replay_fingerprint(data: dict[str, Any]) -> str:
    """Hash ổn định bất kể thứ tự key JSON (ADR-002 determinism)."""
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _env_replay() -> bool:
    return os.environ.get("CA_AGENT_MODE", "").strip().lower() == "replay"


class ExperienceEventReader(Protocol):
    """Protocol đọc sự kiện trải nghiệm (read-only)."""

    def list_events(self, **filters: Any) -> list[dict[str, Any]]: ...

    def event_by_id(self, event_id: str) -> dict[str, Any] | None: ...


class ExperienceSpatialReader(Protocol):
    """Protocol đọc bản đồ không gian (read-only)."""

    def list_anchors(self) -> list[SpatialAnchor]: ...


class FixtureReader:
    """Đọc fixture replay tất định — KHÔNG mở mạng, không DB."""

    def __init__(self, fixture_dir: Path | None = None) -> None:
        self._fixture_dir = fixture_dir or _DEFAULT_FIXTURE_DIR
        self._events_cache: dict[str, Any] | None = None
        self._map_cache: list[SpatialAnchor] | None = None
        self._scn_cache: dict[str, Any] | None = None

    @property
    def events_path(self) -> Path:
        return self._fixture_dir / "events.json"

    @property
    def scenarios_path(self) -> Path:
        return self._fixture_dir / "scenarios.json"

    @property
    def spatial_map_path(self) -> Path:
        return self._fixture_dir / "spatial-map.json"

    def read_json_path(self, name: str) -> dict[str, Any]:
        """Đọc fixture theo tên file (không path traversal — chỉ tên file)."""
        if "/" in name or "\\" in name or not name.endswith(".json"):
            raise ValueError(f"tên fixture không hợp lệ: {name}")
        path = self._fixture_dir / name
        return _read_json(path)

    def list_events(self, **filters: Any) -> list[dict[str, Any]]:
        if self._events_cache is None:
            self._events_cache = _read_json(self.events_path)
        events = list(self._events_cache.get("events", []))
        if "anchor_id" in filters and filters["anchor_id"] is not None:
            events = [e for e in events if e.get("anchor_id") == filters["anchor_id"]]
        if "event_type" in filters and filters["event_type"] is not None:
            events = [e for e in events if e.get("event_type") == filters["event_type"]]
        return events

    def event_by_id(self, event_id: str) -> dict[str, Any] | None:
        for ev in self.list_events():
            if ev.get("event_id") == event_id:
                return ev
        return None

    def list_anchors(self) -> list[SpatialAnchor]:
        if self._map_cache is None:
            raw = _read_json(self.spatial_map_path)
            self._map_cache = [SpatialAnchor.model_validate(a) for a in raw.get("anchors", [])]
        return list(self._map_cache)

    def list_scenarios(self) -> list[dict[str, Any]]:
        if self._scn_cache is None:
            self._scn_cache = _read_json(self.scenarios_path)
        return list(self._scn_cache.get("scenarios", []))

    def fingerprint(self) -> str:
        """Fingerprint toàn bộ fixture — dùng làm snapshot hash mặc định khi replay."""
        parts = {
            "events": self.list_events(),
            "anchors": [a.model_dump(mode="json") for a in self.list_anchors()],
            "scenarios": self.list_scenarios(),
        }
        return replay_fingerprint(parts)


class NullReader:
    """Reader rỗng cho production khi chưa bật adapter — fail-closed."""

    def list_events(self, **filters: Any) -> list[dict[str, Any]]:
        return []

    def event_by_id(self, event_id: str) -> dict[str, Any] | None:
        return None

    def list_anchors(self) -> list[SpatialAnchor]:
        return []


def load_events(fixture_dir: Path | None = None) -> list[dict[str, Any]]:
    return FixtureReader(fixture_dir).list_events()


def load_scenarios(fixture_dir: Path | None = None) -> list[dict[str, Any]]:
    return FixtureReader(fixture_dir).list_scenarios()


def load_spatial_map(fixture_dir: Path | None = None) -> list[SpatialAnchor]:
    return FixtureReader(fixture_dir).list_anchors()