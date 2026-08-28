"""Parse inbound channel payloads — no network."""

from __future__ import annotations

from ca_agents.messaging import is_xem_lich, parse_telegram_update, parse_zalo_webhook


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
