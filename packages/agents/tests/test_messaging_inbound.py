"""Parse inbound channel payloads — no network."""

from __future__ import annotations

import hashlib
import hmac

from ca_agents.facebook_page import verify_fb_webhook_signature
from ca_agents.messaging import is_xem_lich, parse_telegram_update, parse_zalo_webhook


def test_facebook_webhook_signature_fails_closed_without_secret(monkeypatch) -> None:
    monkeypatch.delenv("NHIPQUAN_FB_APP_SECRET", raising=False)
    assert verify_fb_webhook_signature(b"{}", "") is False


def test_facebook_webhook_signature_accepts_valid_hmac(monkeypatch) -> None:
    monkeypatch.setenv("NHIPQUAN_FB_APP_SECRET", "secret_test")
    payload = b'{"entry":[]}'
    digest = hmac.new(b"secret_test", payload, hashlib.sha256).hexdigest()

    assert verify_fb_webhook_signature(payload, f"sha256={digest}") is True
    assert verify_fb_webhook_signature(payload, "sha256=invalid") is False


def test_parse_zalo_user_send_text() -> None:
    msg = parse_zalo_webhook(
        {
            "event_name": "user_send_text",
            "sender": {"id": "z99"},
            "message": {"text": "xem lịch của tôi", "msg_id": "m1"},
        }
    )
    assert msg is not None
    assert msg.channel == "zalo"
    assert msg.external_user_id == "z99"
    assert is_xem_lich(msg.text)


def test_parse_telegram_message() -> None:
    msg = parse_telegram_update(
        {"message": {"text": "/bind abc123", "chat": {"id": 42}, "message_id": 7}}
    )
    assert msg is not None
    assert msg.channel == "telegram"
    assert msg.external_user_id == "42"
