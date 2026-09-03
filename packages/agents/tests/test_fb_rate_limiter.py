"""Unit tests for fb_rate_limiter — sliding window, strikes, blacklist (plan §3.5).

All time is injected via now_fn — no real clock (ADR-002, deterministic tests).
"""

from __future__ import annotations

from ca_agents.fb_rate_limiter import (
    BLACKLIST_STRIKES,
    MSG_PER_HOUR,
    MSG_PER_MINUTE,
    SlidingWindowRateLimiter,
)


class FakeClock:
    def __init__(self) -> None:
        self.t: float = 1000.0

    def __call__(self) -> float:
        return self.t


def make_limiter() -> tuple[SlidingWindowRateLimiter, FakeClock]:
    clock = FakeClock()
    return SlidingWindowRateLimiter(now_fn=clock), clock


def test_constants_match_plan() -> None:
    assert MSG_PER_MINUTE == 5
    assert MSG_PER_HOUR == 30
    assert BLACKLIST_STRIKES == 3


def test_allows_up_to_limit_per_minute() -> None:
    limiter, _ = make_limiter()
    for _ in range(MSG_PER_MINUTE):
        v = limiter.check("psid-1")
        assert v.allowed
    v = limiter.check("psid-1")
    assert not v.allowed
    assert v.reason == "rate_limit_minute"


def test_window_slides_after_60s() -> None:
    limiter, clock = make_limiter()
    for _ in range(MSG_PER_MINUTE):
        assert limiter.check("psid-1").allowed
    clock.t += 61.0
    v = limiter.check("psid-1")
    assert v.allowed, "window must reset after 60s"


def test_hourly_cap_independent_of_minute_window() -> None:
    limiter, clock = make_limiter()
    # 30 messages spread across time — never trips minute window
    for i in range(MSG_PER_HOUR):
        clock.t += 13.0
        v = limiter.check("psid-2")
        if i < MSG_PER_HOUR - 1:
            assert v.allowed, f"msg {i + 1} unexpectedly blocked"
    clock.t += 13.0
    v = limiter.check("psid-2")
    assert not v.allowed
    assert v.reason == "rate_limit_hour"


def test_strikes_accumulate_then_blacklist() -> None:
    limiter, _ = make_limiter()
    psid = "spammer"
    for _ in range(BLACKLIST_STRIKES):
        for _ in range(MSG_PER_MINUTE):
            limiter.check(psid)
        limiter.check(psid)  # trip minute window → 1 strike
    v = limiter.check(psid)
    assert v.blacklisted


def test_blacklist_ttl_expiry() -> None:
    limiter, clock = make_limiter()
    psid = "spammer"
    for _ in range(BLACKLIST_STRIKES):
        for _ in range(MSG_PER_MINUTE):
            limiter.check(psid)
        limiter.check(psid)
    # Advance beyond TTL (24h) → blacklist expired
    clock.t += 24 * 3600 + 1
    # Window also pruned → allowed again
    v = limiter.check(psid)
    assert v.allowed
    assert not v.blacklisted


def test_isolated_psid() -> None:
    limiter, _ = make_limiter()
    for _ in range(MSG_PER_MINUTE):
        limiter.check("a")
    assert limiter.check("a").allowed is False
    assert limiter.check("b").allowed


def test_supervisor_leak_patterns_extended() -> None:
    """New leak patterns from plan §3.6 must trigger supervise_outgoing_response."""
    from ca_agents.ag_supervisor import supervise_outgoing_response

    leaks = [
        "Lương nhân viên quán là 5 triệu.",
        "Số điện thoại nội bộ của quản lý là 090…",
        "Chi phí nguyên liệu mỗi ly chỉ 8k.",
        "Mật khẩu quản lý là abc123.",
    ]
    for text in leaks:
        res = supervise_outgoing_response("hỏi gì đó", text)
        assert not res.is_approved, f"leak not caught: {text}"
        assert res.flagged_reason == "data_leak_detected"


def test_hear_structure_checker() -> None:
    from ca_agents.ag_supervisor import check_hear_structure

    good = (
        "Dạ em thật sự xin lỗi vì trải nghiệm chưa tốt của mình ạ! "
        "Anh/chị cho em xin số điện thoại để Quản lý gọi hỗ trợ nha ạ."
    )
    ok, missing = check_hear_structure(good)
    assert ok
    assert missing == ()

    bad = "Dạ em đã ghi nhận ạ."
    ok, missing = check_hear_structure(bad)
    assert not ok
    assert set(missing) == {"xin_loi", "so_dien_thoai", "quan_ly"}


def test_normalize_text_in_guardrails() -> None:
    from ca_agents.guardrails import normalize_text

    assert normalize_text("B.Á.O  Ch í") == "bao chi"
    assert normalize_text("HÓA ĐƠN ĐỎ") == "hoa don do"
    assert normalize_text("ngộ  độc!!!") == "ngo doc"
    assert normalize_text("đến") == "den"
