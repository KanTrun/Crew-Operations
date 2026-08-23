from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import cast

from ca_api.orchestration import IdempotencyStore, StateMachine, dispatch_parallel


def test_state_machine_legal() -> None:
    sm = StateMachine()
    sm.transition("dang_chay")
    sm.transition("xong")
    assert sm.state == "xong"


def test_idempotency_second_call_replays() -> None:
    store = IdempotencyStore()
    n = {"c": 0}

    def fn() -> int:
        n["c"] += 1
        return n["c"]

    a, r1 = store.once("k", fn)
    b, r2 = store.once("k", fn)
    assert a == 1 and b == 1
    assert r1 is False and r2 is True
    assert n["c"] == 1


def test_idempotency_concurrent_same_key_one_write() -> None:
    store = IdempotencyStore()
    n = {"c": 0}

    def fn() -> int:
        n["c"] += 1
        return n["c"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(store.once, "same", fn) for _ in range(8)]
        results = [f.result() for f in futs]
    values = {v for v, _replayed in results}
    replayed = sum(1 for _v, r in results if r)
    assert values == {1}
    assert n["c"] == 1
    assert replayed == 7


def test_dispatch_eight_parallel() -> None:
    # cast: lambda có tham số mặc định nên mypy không suy được kiểu từ ngữ cảnh
    out = dispatch_parallel(
        [cast("Callable[[], int]", lambda i=i: i * i) for i in range(8)]
    )
    assert out == [i * i for i in range(8)]
