"""Kiểm tra logic hết hạn token — naive vs aware datetime của google-auth."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest


def test_google_auth_naive_expiry_must_be_read_as_utc() -> None:
    """google-auth ghi `expiry` dạng NAIVE UTC (bỏ tzinfo để tương thích ngược).

    Nếu ta hiểu nhầm chuỗi đó là giờ máy (VN, +07) thì mốc hết hạn bị dịch
    sớm 7 tiếng — token còn hạn bị coi là hết hạn.
    """
    expires_naive = "2026-09-23T10:00:00"  # google-auth ghi kiểu này
    real_now = datetime(2026, 9, 23, 9, 0, tzinfo=UTC)  # 09:00 UTC ⇒ còn 1 giờ

    # Đọc ĐÚNG: naive = UTC.
    correct = datetime.fromisoformat(expires_naive).replace(tzinfo=UTC)
    assert correct > real_now, "đọc là UTC ⇒ token còn hạn"

    # Đọc SAI: naive = giờ máy (+07).
    wrong = datetime.fromisoformat(expires_naive).replace(
        tzinfo=timezone(timedelta(hours=7))
    )
    assert wrong < real_now, "đọc là +07 ⇒ tưởng hết hạn sớm 7 tiếng"


def test_expiry_with_z_suffix_is_aware() -> None:
    """Chuỗi có 'Z' → aware, so sánh với aware cùng múi là đúng."""
    exp = datetime.fromisoformat("2026-09-23T10:00:00Z".replace("Z", "+00:00"))
    assert exp.tzinfo is not None
    assert exp < datetime(2026, 9, 23, 11, 0, tzinfo=UTC)
    assert not exp < datetime(2026, 9, 23, 9, 0, tzinfo=UTC)


def test_parse_handles_naive_and_aware_consistently() -> None:
    """Hàm chuẩn hoá phải coi chuỗi naive là UTC và luôn trả aware UTC."""
    from ca_api.services.gmail_sync import _parse_expiry

    naive = _parse_expiry("2026-09-23T10:00:00")
    with_z = _parse_expiry("2026-09-23T10:00:00Z")
    with_offset = _parse_expiry("2026-09-23T17:00:00+07:00")

    assert naive is not None and naive.tzinfo is not None
    assert naive == with_z == with_offset == datetime(2026, 9, 23, 10, 0, tzinfo=UTC)


def test_parse_expiry_rejects_garbage() -> None:
    from ca_api.services.gmail_sync import _parse_expiry

    assert _parse_expiry("khong-phai-thoi-gian") is None
    assert _parse_expiry("") is None


@pytest.mark.parametrize(
    ("expires_in", "expect_refresh"),
    [(timedelta(minutes=-1), True), (timedelta(minutes=+30), False)],
)
def test_token_needs_refresh(expires_in: timedelta, expect_refresh: bool) -> None:
    """Token hết hạn ⇒ cần làm mới; còn hạn ⇒ không."""
    from ca_api.services.gmail_sync import _token_needs_refresh

    exp = (datetime.now(UTC) + expires_in).isoformat()
    assert _token_needs_refresh(exp) is expect_refresh
