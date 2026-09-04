"""Runtime operational controls for AI learning channels."""

from __future__ import annotations

from ca_api.persist import kv_get


def circuit_breaker_open(*, store_id: str, channel: str, traffic_class: str = "default") -> bool:
    state = kv_get(f"ai_circuit_breaker:{store_id}:{channel}:{traffic_class}", {})
    return bool(state.get("open")) if isinstance(state, dict) else False