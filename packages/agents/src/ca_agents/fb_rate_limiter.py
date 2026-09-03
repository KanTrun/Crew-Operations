"""Sliding-window rate limiter per PSID (deterministic, injectable clock).

GIA ĐỊNH CONCURRENCY (kế hoạch §6.2e): pipeline xử lý inbound TUẦN TỰ theo hàng
đợi (1 consumer). Nếu tương lai có nhiều worker xử lý song song cùng PSID, phải
bọc instance này bằng lock hoặc thay bằng storage có atomic ops — KHÔNG dùng
trực tiếp trong môi trường đa luồng.

Đồng hồ được inject qua ``now_fn`` (trả về giây epoch dạng float) để test tất định
theo replay mode (ADR-002). Module này KHÔNG tự đọc đồng hồ khi now_fn được truyền.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass

MSG_PER_MINUTE = 5
MSG_PER_HOUR = 30
BLACKLIST_STRIKES = 3
BLACKLIST_TTL_MINUTES = 24 * 60


def _default_now() -> float:
    return time.time()


@dataclass(frozen=True)
class RateVerdict:
    allowed: bool
    reason: str | None = None
    blacklisted: bool = False


class SlidingWindowRateLimiter:
    """now_fn injectable → testable in replay mode without real time."""

    def __init__(self, now_fn: Callable[[], float] | None = None) -> None:
        self._now = now_fn or _default_now
        self._minute: dict[str, deque[float]] = defaultdict(deque)
        self._hour: dict[str, deque[float]] = defaultdict(deque)
        # psid -> (last_strike_time, strike_count)
        self._strikes: dict[str, tuple[float, int]] = {}

    def check(self, psid: str) -> RateVerdict:
        now = self._now()
        self._prune(self._minute[psid], now, 60.0)
        self._prune(self._hour[psid], now, 3600.0)

        # Kiểm tra blacklist trước
        if self._is_blacklisted(psid, now):
            return RateVerdict(allowed=False, reason="blacklisted", blacklisted=True)

        # Kiểm tra giới hạn 1 phút
        if len(self._minute[psid]) >= MSG_PER_MINUTE:
            self._bump_strike(psid, now)
            is_bl = self._is_blacklisted(psid, now)
            return RateVerdict(allowed=False, reason="rate_limit_minute", blacklisted=is_bl)

        # Kiểm tra giới hạn 1 giờ
        if len(self._hour[psid]) >= MSG_PER_HOUR:
            self._bump_strike(psid, now)
            is_bl = self._is_blacklisted(psid, now)
            return RateVerdict(allowed=False, reason="rate_limit_hour", blacklisted=is_bl)

        self._minute[psid].append(now)
        self._hour[psid].append(now)
        return RateVerdict(True, None, self._is_blacklisted(psid, now))

    @staticmethod
    def _prune(window: deque[float], now: float, window_seconds: float) -> None:
        cutoff = now - window_seconds
        while window and window[0] <= cutoff:
            window.popleft()

    def _bump_strike(self, psid: str, now: float) -> None:
        ts, count = self._strikes.get(psid, (now, 0))
        if now - ts > BLACKLIST_TTL_MINUTES * 60:
            ts, count = now, 0  # strike cũ hết hạn — reset (kế hoạch §6.2e)
        self._strikes[psid] = (ts, count + 1)

    def _is_blacklisted(self, psid: str, now: float) -> bool:
        ts, count = self._strikes.get(psid, (now, 0))
        if now - ts > BLACKLIST_TTL_MINUTES * 60:
            return False
        return count >= BLACKLIST_STRIKES
