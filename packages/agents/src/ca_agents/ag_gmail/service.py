"""Gmail API service — high-level operations for Gmail management."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, cast

from googleapiclient.discovery import build

from ca_agents.ag_gmail.models import (
    GmailFilter,
    GmailLabel,
    GmailMessage,
)
from ca_agents.ag_gmail.oauth import create_credentials


def _as_dict(value: Any) -> dict[str, Any]:
    """Google API client trả `Any`; ép về đúng kiểu cho mypy strict."""
    return cast(dict[str, Any], value)


class GmailService:
    """High-level Gmail API service."""

    def __init__(self, access_token: str, refresh_token: str | None = None):
        self.credentials = create_credentials(access_token, refresh_token)
        self.service = build("gmail", "v1", credentials=self.credentials, cache_discovery=False)

    # ── Account / Profile ────────────────────────────────────────────────

    def get_profile(self) -> dict[str, Any]:
        """Get Gmail profile (email, messagesTotal, threadsTotal, historyId)."""
        return _as_dict(self.service.users().getProfile(userId="me").execute())

    # ── Messages ──────────────────────────────────────────────────────────

    def list_messages(
        self,
        *,
        label_ids: list[str] | None = None,
        query: str | None = None,
        max_results: int = 50,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List messages with optional filters."""
        return _as_dict(
            self.service.users()
            .messages()
            .list(
                userId="me",
                labelIds=label_ids,
                q=query,
                maxResults=max_results,
                pageToken=page_token,
            )
            .execute()
        )

    def get_message(self, message_id: str, format: str = "full") -> dict[str, Any]:
        """Get a single message by ID."""
        return _as_dict(
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format=format)
            .execute()
        )

    def get_message_raw(self, message_id: str) -> dict[str, Any]:
        """Get raw message (RFC 822)."""
        return _as_dict(
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="raw")
            .execute()
        )

    def batch_get_messages(self, message_ids: list[str]) -> list[dict[str, Any]]:
        """Batch get multiple messages."""
        batch = self.service.new_batch_http_request()
        results: dict[str, dict[str, Any]] = {}

        def callback(request_id: str, response: Any, exception: Any) -> None:
            if exception:
                results[request_id] = {"error": str(exception)}
            else:
                results[request_id] = _as_dict(response)

        for msg_id in message_ids:
            batch.add(
                self.service.users().messages().get(userId="me", id=msg_id, format="full"),
                request_id=msg_id,
                callback=callback,
            )
        batch.execute()
        return [results[mid] for mid in message_ids]

    def modify_message(
        self,
        message_id: str,
        *,
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Modify message labels (read/unread, star, archive, etc.)."""
        body: dict[str, Any] = {}
        if add_label_ids:
            body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids
        return _as_dict(
            self.service.users()
            .messages()
            .modify(userId="me", id=message_id, body=body)
            .execute()
        )

    def trash_message(self, message_id: str) -> dict[str, Any]:
        """Move message to trash."""
        return _as_dict(self.service.users().messages().trash(userId="me", id=message_id).execute())

    def delete_message(self, message_id: str) -> None:
        """Permanently delete message."""
        self.service.users().messages().delete(userId="me", id=message_id).execute()

    # ── Send Message ──────────────────────────────────────────────────────

    def send_message(
        self,
        *,
        to: list[str],
        subject: str,
        body_text: str,
        body_html: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        thread_id: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
    ) -> dict[str, Any]:
        """Send an email message."""
        msg: MIMEMultipart | MIMEText
        if body_html:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))
        else:
            msg = MIMEText(body_text, "plain", "utf-8")

        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = ", ".join(cc)
        if bcc:
            msg["Bcc"] = ", ".join(bcc)
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        payload: dict[str, Any] = {"raw": raw}
        if thread_id:
            payload["threadId"] = thread_id

        return _as_dict(self.service.users().messages().send(userId="me", body=payload).execute())

    # ── Labels ────────────────────────────────────────────────────────────

    def list_labels(self) -> list[dict[str, Any]]:
        """List all labels."""
        result = _as_dict(self.service.users().labels().list(userId="me").execute())
        return cast(list[dict[str, Any]], result.get("labels", []))

    def get_label(self, label_id: str) -> dict[str, Any]:
        """Get a single label."""
        return _as_dict(self.service.users().labels().get(userId="me", id=label_id).execute())

    def create_label(
        self,
        *,
        name: str,
        label_list_visibility: str = "labelShow",
        message_list_visibility: str = "show",
        color_background: str | None = None,
        color_text: str | None = None,
    ) -> dict[str, Any]:
        """Create a new label."""
        body: dict[str, Any] = {
            "name": name,
            "labelListVisibility": label_list_visibility,
            "messageListVisibility": message_list_visibility,
        }
        if color_background or color_text:
            color: dict[str, str] = {}
            if color_background:
                color["backgroundColor"] = color_background
            if color_text:
                color["textColor"] = color_text
            body["color"] = color
        return _as_dict(self.service.users().labels().create(userId="me", body=body).execute())

    def update_label(
        self,
        label_id: str,
        *,
        name: str | None = None,
        label_list_visibility: str | None = None,
        message_list_visibility: str | None = None,
        color_background: str | None = None,
        color_text: str | None = None,
    ) -> dict[str, Any]:
        """Update a label."""
        body: dict[str, Any] = {}
        if name:
            body["name"] = name
        if label_list_visibility:
            body["labelListVisibility"] = label_list_visibility
        if message_list_visibility:
            body["messageListVisibility"] = message_list_visibility
        if color_background or color_text:
            color: dict[str, str] = {}
            if color_background:
                color["backgroundColor"] = color_background
            if color_text:
                color["textColor"] = color_text
            body["color"] = color
        return _as_dict(
            self.service.users().labels().update(userId="me", id=label_id, body=body).execute()
        )

    def delete_label(self, label_id: str) -> None:
        """Delete a label."""
        self.service.users().labels().delete(userId="me", id=label_id).execute()

    # ── Filters ───────────────────────────────────────────────────────────

    def list_filters(self) -> list[dict[str, Any]]:
        """List all filters."""
        result = _as_dict(self.service.users().settings().filters().list(userId="me").execute())
        return cast(list[dict[str, Any]], result.get("filter", []))

    def get_filter(self, filter_id: str) -> dict[str, Any]:
        """Get a single filter."""
        return _as_dict(
            self.service.users().settings().filters().get(userId="me", id=filter_id).execute()
        )

    def create_filter(
        self,
        *,
        criteria: dict[str, Any],
        action: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new filter."""
        body = {"criteria": criteria, "action": action}
        return _as_dict(
            self.service.users().settings().filters().create(userId="me", body=body).execute()
        )

    def delete_filter(self, filter_id: str) -> None:
        """Delete a filter."""
        self.service.users().settings().filters().delete(userId="me", id=filter_id).execute()

    # ── Threads ───────────────────────────────────────────────────────────

    def list_threads(
        self,
        *,
        label_ids: list[str] | None = None,
        query: str | None = None,
        max_results: int = 50,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List threads."""
        return _as_dict(
            self.service.users()
            .threads()
            .list(
                userId="me",
                labelIds=label_ids,
                q=query,
                maxResults=max_results,
                pageToken=page_token,
            )
            .execute()
        )

    def get_thread(self, thread_id: str, format: str = "full") -> dict[str, Any]:
        """Get a thread with messages."""
        return _as_dict(
            self.service.users()
            .threads()
            .get(userId="me", id=thread_id, format=format)
            .execute()
        )

    def modify_thread(
        self,
        thread_id: str,
        *,
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Modify thread labels."""
        body: dict[str, Any] = {}
        if add_label_ids:
            body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids
        return _as_dict(
            self.service.users()
            .threads()
            .modify(userId="me", id=thread_id, body=body)
            .execute()
        )

    def trash_thread(self, thread_id: str) -> dict[str, Any]:
        """Move thread to trash."""
        return _as_dict(self.service.users().threads().trash(userId="me", id=thread_id).execute())

    # ── History / Sync ────────────────────────────────────────────────────

    def list_history(
        self,
        *,
        start_history_id: str,
        label_id: str | None = None,
        max_results: int = 100,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List history changes for incremental sync."""
        return _as_dict(
            self.service.users()
            .history()
            .list(
                userId="me",
                startHistoryId=start_history_id,
                labelId=label_id,
                maxResults=max_results,
                pageToken=page_token,
            )
            .execute()
        )

    # ── Settings ──────────────────────────────────────────────────────────

    def get_vacation_settings(self) -> dict[str, Any]:
        """Get vacation responder settings."""
        return _as_dict(self.service.users().settings().getVacation(userId="me").execute())

    def update_vacation_settings(
        self,
        *,
        enable: bool,
        subject: str | None = None,
        response_body_html: str | None = None,
        response_body_plain_text: str | None = None,
        restrict_to_contacts: bool = False,
        restrict_to_domain: bool = False,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        """Update vacation responder settings."""
        body: dict[str, Any] = {"enableAutoReply": enable}
        if subject:
            body["responseSubject"] = subject
        if response_body_html:
            body["responseBodyHtml"] = response_body_html
        if response_body_plain_text:
            body["responseBodyPlainText"] = response_body_plain_text
        body["restrictToContacts"] = restrict_to_contacts
        body["restrictToDomain"] = restrict_to_domain
        if start_time:
            body["startTime"] = start_time
        if end_time:
            body["endTime"] = end_time
        return _as_dict(
            self.service.users().settings().updateVacation(userId="me", body=body).execute()
        )

    def get_send_as(self) -> list[dict[str, Any]]:
        """List send-as aliases."""
        result = _as_dict(self.service.users().settings().sendAs().list(userId="me").execute())
        return cast(list[dict[str, Any]], result.get("sendAs", []))

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def parse_message(raw_message: dict[str, Any]) -> GmailMessage:
        """Parse Gmail API message to GmailMessage model."""
        payload = cast(dict[str, Any], raw_message.get("payload", {}))
        headers = {
            cast(str, h["name"]).lower(): cast(str, h["value"])
            for h in cast(list[dict[str, Any]], payload.get("headers", []))
        }

        # Extract body
        body_text: str | None = None
        body_html: str | None = None

        def extract_body(part: dict[str, Any]) -> None:
            nonlocal body_text, body_html
            mime_type = cast(str, part.get("mimeType", ""))
            data = cast(dict[str, Any], part.get("body", {})).get("data")
            if data:
                decoded = base64.urlsafe_b64decode(cast(str, data)).decode("utf-8", errors="replace")
                if mime_type == "text/plain":
                    body_text = decoded
                elif mime_type == "text/html":
                    body_html = decoded
            for subpart in cast(list[dict[str, Any]], part.get("parts", [])):
                extract_body(subpart)

        extract_body(payload)

        # Parse label IDs
        label_ids = cast(list[str], raw_message.get("labelIds", []))

        # Parse addresses
        from_email = headers.get("from", "")
        to_emails = [e.strip() for e in headers.get("to", "").split(",") if e.strip()]
        cc_emails = [e.strip() for e in headers.get("cc", "").split(",") if e.strip()]

        internal_ms = int(cast(str, raw_message.get("internalDate", "0")))
        has_attachment = any(
            "attachmentId" in cast(dict[str, Any], part.get("body", {}))
            for part in cast(list[dict[str, Any]], payload.get("parts", []))
        )

        return GmailMessage(
            id=cast(str, raw_message["id"]),
            account_id="",  # Set by caller
            thread_id=cast(str, raw_message.get("threadId", "")),
            label_ids=label_ids,
            snippet=cast(str, raw_message.get("snippet", "")),
            from_email=from_email,
            to_emails=to_emails,
            cc_emails=cc_emails,
            subject=headers.get("subject", ""),
            body_text=body_text,
            body_html=body_html,
            internal_date=datetime.fromtimestamp(internal_ms / 1000, tz=UTC).isoformat(),
            is_read="UNREAD" not in label_ids,
            is_starred="STARRED" in label_ids,
            has_attachment=has_attachment,
            raw_headers=json.dumps(headers, ensure_ascii=False),
        )

    @staticmethod
    def parse_label(raw_label: dict[str, Any], account_id: str) -> GmailLabel:
        """Parse Gmail API label to GmailLabel model."""
        color = cast(dict[str, str], raw_label.get("color", {}))
        return GmailLabel(
            id=cast(str, raw_label["id"]),
            account_id=account_id,
            name=cast(str, raw_label["name"]),
            label_type=cast(str, raw_label.get("type", "user")),
            message_list_visibility=cast(str, raw_label.get("messageListVisibility", "show")),
            label_list_visibility=cast(str, raw_label.get("labelListVisibility", "labelShow")),
            color_background=color.get("backgroundColor"),
            color_text=color.get("textColor"),
            total_messages=int(raw_label.get("messagesTotal", 0)),
            unread_messages=int(raw_label.get("messagesUnread", 0)),
            updated_at=datetime.now(UTC).isoformat(),
        )

    @staticmethod
    def parse_filter(raw_filter: dict[str, Any], account_id: str) -> GmailFilter:
        """Parse Gmail API filter to GmailFilter model."""
        return GmailFilter(
            id=cast(str, raw_filter["id"]),
            account_id=account_id,
            criteria=cast(dict[str, Any], raw_filter.get("criteria", {})),
            action=cast(dict[str, Any], raw_filter.get("action", {})),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )