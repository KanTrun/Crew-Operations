"""Deterministic orchestration — state machine, parallel dispatch, idempotency."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc
from threading import Lock
from typing import Any


class Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def now_ms(self) -> int:
        return int(self.now().timestamp() * 1000)

    def now_iso(self) -> str:
        return self.now().isoformat()


class FrozenClock(Clock):
    def __init__(self, when: datetime) -> None:
        self._when = when

    def now(self) -> datetime:
        return self._when


STATES = ("nhap", "dang_chay", "cho_duyet", "xong", "loi")
_ALLOWED = {
    "nhap": {"dang_chay", "loi"},
    "dang_chay": {"cho_duyet", "xong", "loi"},
    "cho_duyet": {"xong", "loi"},
    "xong": set(),
    "loi": {"nhap"},
}


class StateMachine:
    def __init__(self, start: str = "nhap") -> None:
        if start not in STATES:
            raise ValueError(start)
        self.state = start

    def transition(self, to: str) -> str:
        if to not in _ALLOWED[self.state]:
            raise ValueError(f"illegal:{self.state}->{to}")
        self.state = to
        return self.state


@dataclass
class IdempotencyStore:
    _done: dict[str, Any] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def once(self, key: str, fn: Callable[[], Any]) -> tuple[Any, bool]:
        """Return (result, replayed). Same key never re-runs fn."""
        with self._lock:
            if key in self._done:
                return self._done[key], True
            val = fn()
            self._done[key] = val
            return val, False


def dispatch_parallel(tasks: list[Callable[[], Any]], *, workers: int = 8) -> list[Any]:
    if not tasks:
        return []
    n = min(workers, len(tasks))
    out: list[Any] = [None] * len(tasks)
    with ThreadPoolExecutor(max_workers=n) as pool:
        futs = {pool.submit(fn): i for i, fn in enumerate(tasks)}
        for fut in as_completed(futs):
            out[futs[fut]] = fut.result()
    return out
