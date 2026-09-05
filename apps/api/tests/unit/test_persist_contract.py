from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from ca_api.persist import (
    fb_try_claim_event,
    kv_get,
    kv_mutate,
    kv_set,
    register,
    session,
)


def test_persistence_contract() -> None:
    suffix = uuid4().hex
    key = f"contract-{suffix}"
    kv_set(key, {"count": 1})
    assert kv_get(key, None) == {"count": 1}
    assert kv_mutate(key, lambda value: {"count": value["count"] + 1}, {}) == {
        "count": 2
    }

    username = f"user_{suffix[:12]}"
    auth = register(username, "password123", "Contract User")
    assert session(f"Bearer {auth['token']}") == {
        "username": username,
        "role": "nhan_vien",
        "nv_id": auth["nv_id"],
        "email": "",
        "store_id": "quan_01",
    }

    event_id = f"event-contract-{suffix}"
    assert fb_try_claim_event(event_id) is True
    assert fb_try_claim_event(event_id) is False


def test_kv_mutate_is_atomic_across_connections() -> None:
    key = f"contract-concurrent-counter-{uuid4().hex}"
    increments = 20
    kv_set(key, 0)

    def increment(_: int) -> None:
        kv_mutate(key, lambda value: value + 1, 0)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(increment, range(increments)))

    assert kv_get(key, None) == increments