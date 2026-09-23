"""Gmail data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GmailAccount:
    """Gmail account linked to a staff member."""
    id: str
    store_id: str
    nv_id: str
    email: str
    display_name: str = ""
    is_primary: bool = False
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""


@dataclass
class GmailOAuthTokens:
    """OAuth tokens for a Gmail account."""
    account_id: str
    access_token: str
    refresh_token: str | None
    expires_at: str
    scope: str = ""
    token_type: str = "Bearer"
    updated_at: str = ""


@dataclass
class GmailSyncState:
    """Gmail sync state for incremental sync."""
    account_id: str
    last_history_id: str | None = None
    last_sync_at: str | None = None
    sync_cursor: str | None = None
    total_messages: int = 0
    unread_count: int = 0
    updated_at: str = ""


@dataclass
class GmailMessage:
    """Gmail message."""
    id: str
    account_id: str
    thread_id: str
    label_ids: list[str] = field(default_factory=list)
    snippet: str = ""
    from_email: str = ""
    to_emails: list[str] = field(default_factory=list)
    cc_emails: list[str] = field(default_factory=list)
    subject: str = ""
    body_text: str | None = None
    body_html: str | None = None
    internal_date: str = ""
    is_read: bool = False
    is_starred: bool = False
    has_attachment: bool = False
    raw_headers: str | None = None
    created_at: str = ""


@dataclass
class GmailLabel:
    """Gmail label."""
    id: str
    account_id: str
    name: str
    label_type: str = "user"
    message_list_visibility: str = "show"
    label_list_visibility: str = "labelShow"
    color_background: str | None = None
    color_text: str | None = None
    total_messages: int = 0
    unread_messages: int = 0
    updated_at: str = ""


@dataclass
class GmailFilter:
    """Gmail filter."""
    id: str
    account_id: str
    criteria: dict[str, Any] = field(default_factory=dict)
    action: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class GmailThread:
    """Gmail thread (conversation)."""
    id: str
    account_id: str
    message_ids: list[str] = field(default_factory=list)
    subject: str = ""
    participants: list[str] = field(default_factory=list)
    last_message_date: str = ""
    is_unread: bool = False
    label_ids: list[str] = field(default_factory=list)