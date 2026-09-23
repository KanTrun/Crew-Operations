# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Test đồng bộ tăng dần — phải ÁP DỤNG thay đổi, không chỉ đếm.

Dùng service giả (không gọi Gmail thật) để kiểm chứng: thêm / xoá / đổi nhãn
đều phải phản ánh vào DB local.
"""

from __future__ import annotations

import asyncio
from typing import Any

from ca_api import persist
from ca_api.services import gmail_sync


class _FakeService:
    """GmailService giả: trả kịch bản history cố định."""

    def __init__(self, history_pages: list[dict[str, Any]], messages: dict[str, dict[str, Any]]):
        self._pages = history_pages
        self._messages = messages
        self.get_calls: list[str] = []

    def list_history(self, **_: Any) -> dict[str, Any]:
        if self._pages:
            return self._pages.pop(0)
        return {"history": []}

    def get_message(self, message_id: str, format: str = "full") -> dict[str, Any]:
        self.get_calls.append(message_id)
        return self._messages[message_id]


def _seed_account() -> str:
    acc = persist.gmail_account_create(
        store_id="quan_01", nv_id="nv_01", email="incr@gmail.com"
    )
    aid = str(acc["id"])
    persist.gmail_sync_state_upsert(aid, last_history_id="100")
    return aid


def _raw_message(mid: str) -> dict[str, Any]:
    return {
        "id": mid,
        "threadId": f"th_{mid}",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": f"trích {mid}",
        "internalDate": "1700000000000",
        "payload": {
            "headers": [
                {"name": "From", "value": "a@b.com"},
                {"name": "To", "value": "c@d.com"},
                {"name": "Subject", "value": f"Chủ đề {mid}"},
            ],
            "mimeType": "text/plain",
            "body": {"data": "Tm9pIGR1bmc="},
        },
    }


def test_incremental_sync_fetches_full_message_for_new_mail() -> None:
    """Email mới phải được tải bản ĐẦY ĐỦ (history chỉ có metadata rút gọn)."""
    aid = _seed_account()
    fake = _FakeService(
        history_pages=[
            {
                "history": [
                    {
                        "id": "150",
                        "messagesAdded": [{"message": {"id": "m_new", "threadId": "t1"}}],
                    }
                ]
            }
        ],
        messages={"m_new": _raw_message("m_new")},
    )

    result = asyncio.run(gmail_sync._incremental_sync(aid, fake, "100", "incr@gmail.com"))

    assert result["messages_added"] == 1
    assert fake.get_calls == ["m_new"], "không gọi messages.get ⇒ email thiếu nội dung"
    stored = persist.gmail_message_get(aid, "m_new")
    assert stored is not None
    assert stored["subject"] == "Chủ đề m_new", "subject trống ⇒ history metadata chưa được bổ sung"


def test_incremental_sync_applies_deletion() -> None:
    """Email Gmail báo đã xoá phải bị xoá khỏi hộp thư app."""
    aid = _seed_account()
    persist.gmail_message_upsert(
        aid,
        message_id="m_gone",
        thread_id="t",
        label_ids=["INBOX"],
        snippet="x",
        from_email="a@b.com",
        to_emails=[],
        cc_emails=[],
        subject="s",
        body_text=None,
        body_html=None,
        internal_date="2026-01-01T00:00:00Z",
        is_read=True,
        is_starred=False,
        has_attachment=False,
    )
    fake = _FakeService(
        history_pages=[
            {"history": [{"id": "160", "messagesDeleted": [{"message": {"id": "m_gone"}}]}]}
        ],
        messages={},
    )

    result = asyncio.run(gmail_sync._incremental_sync(aid, fake, "100", "incr@gmail.com"))

    assert result["messages_deleted"] == 1
    assert persist.gmail_message_get(aid, "m_gone") is None, "email đã xoá vẫn còn trong DB"


def test_incremental_sync_applies_read_state_from_labels() -> None:
    """Bỏ nhãn UNREAD trên Gmail ⇒ email phải thành 'đã đọc' trong app."""
    aid = _seed_account()
    persist.gmail_message_upsert(
        aid,
        message_id="m_read",
        thread_id="t",
        label_ids=["INBOX", "UNREAD"],
        snippet="x",
        from_email="a@b.com",
        to_emails=[],
        cc_emails=[],
        subject="s",
        body_text=None,
        body_html=None,
        internal_date="2026-01-01T00:00:00Z",
        is_read=False,
        is_starred=False,
        has_attachment=False,
    )
    assert persist.gmail_message_get(aid, "m_read")["is_read"] is False

    fake = _FakeService(
        history_pages=[
            {
                "history": [
                    {
                        "id": "170",
                        "labelsRemoved": [
                            {"message": {"id": "m_read"}, "labelIds": ["UNREAD"]}
                        ],
                    }
                ]
            }
        ],
        messages={},
    )

    result = asyncio.run(gmail_sync._incremental_sync(aid, fake, "100", "incr@gmail.com"))

    assert result["messages_modified"] == 1
    stored = persist.gmail_message_get(aid, "m_read")
    assert stored["is_read"] is True, "trạng thái đọc không cập nhật theo nhãn"
    assert "UNREAD" not in stored["label_ids"]


def test_incremental_sync_applies_star_from_labels() -> None:
    """Thêm nhãn STARRED ⇒ email phải có sao trong app."""
    aid = _seed_account()
    persist.gmail_message_upsert(
        aid,
        message_id="m_star",
        thread_id="t",
        label_ids=["INBOX"],
        snippet="x",
        from_email="a@b.com",
        to_emails=[],
        cc_emails=[],
        subject="s",
        body_text=None,
        body_html=None,
        internal_date="2026-01-01T00:00:00Z",
        is_read=True,
        is_starred=False,
        has_attachment=False,
    )
    fake = _FakeService(
        history_pages=[
            {
                "history": [
                    {
                        "id": "180",
                        "labelsAdded": [{"message": {"id": "m_star"}, "labelIds": ["STARRED"]}],
                    }
                ]
            }
        ],
        messages={},
    )

    asyncio.run(gmail_sync._incremental_sync(aid, fake, "100", "incr@gmail.com"))

    stored = persist.gmail_message_get(aid, "m_star")
    assert stored["is_starred"] is True
    assert "STARRED" in stored["label_ids"]


def test_incremental_sync_advances_history_id() -> None:
    """History id phải tiến lên, nếu không lần sau đồng bộ lại từ đầu."""
    aid = _seed_account()
    fake = _FakeService(history_pages=[{"history": [{"id": "999"}]}], messages={})

    asyncio.run(gmail_sync._incremental_sync(aid, fake, "100", "incr@gmail.com"))

    state = persist.gmail_sync_state_get(aid)
    assert state["last_history_id"] == "999"


def test_incremental_sync_ignores_label_change_for_unknown_message() -> None:
    """Đổi nhãn cho email chưa có local ⇒ bỏ qua, không tạo bản ghi rác."""
    aid = _seed_account()
    fake = _FakeService(
        history_pages=[
            {
                "history": [
                    {
                        "id": "190",
                        "labelsAdded": [{"message": {"id": "m_la"}, "labelIds": ["STARRED"]}],
                    }
                ]
            }
        ],
        messages={},
    )

    result = asyncio.run(gmail_sync._incremental_sync(aid, fake, "100", "incr@gmail.com"))

    assert result["messages_modified"] == 0
    assert persist.gmail_message_get(aid, "m_la") is None


def test_incremental_sync_survives_message_fetch_failure() -> None:
    """Lỗi khi tải một email không được làm sập cả lượt đồng bộ."""
    aid = _seed_account()

    class _FailingService(_FakeService):
        def get_message(self, message_id: str, format: str = "full") -> dict[str, Any]:
            raise RuntimeError("Gmail tạm lỗi")

    fake = _FailingService(
        history_pages=[
            {"history": [{"id": "200", "messagesAdded": [{"message": {"id": "m_err"}}]}]}
        ],
        messages={},
    )

    result = asyncio.run(gmail_sync._incremental_sync(aid, fake, "100", "incr@gmail.com"))

    assert result["messages_added"] == 0
    assert persist.gmail_sync_state_get(aid)["last_history_id"] == "200", "mất tiến độ history"
