"""Gmail OAuth 2.0 flow management."""

# google-auth / googleapiclient không ship type stubs đầy đủ — tắt đúng mã lỗi
# no-untyped-call để không phải cast từng lời gọi thư viện.
# mypy: disable-error-code="no-untyped-call"

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, cast

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

# Gmail API scopes needed for full management
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/gmail.settings.sharing",
]


@dataclass
class GmailOAuthConfig:
    """Gmail OAuth configuration."""
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: list[str] = field(default_factory=lambda: list(GMAIL_SCOPES))


def _get_config() -> GmailOAuthConfig:
    """Get OAuth config from environment."""
    client_id = os.environ.get("NHIPQUAN_GMAIL_CLIENT_ID")
    client_secret = os.environ.get("NHIPQUAN_GMAIL_CLIENT_SECRET")
    redirect_uri = os.environ.get("NHIPQUAN_GMAIL_REDIRECT_URI", "http://localhost:8000/api/v1/gmail/oauth/callback")

    if not client_id or not client_secret:
        raise RuntimeError(
            "Gmail OAuth not configured. Set NHIPQUAN_GMAIL_CLIENT_ID and NHIPQUAN_GMAIL_CLIENT_SECRET"
        )

    return GmailOAuthConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )


def build_authorization_url(
    *,
    state: str,
    access_type: str = "offline",
    prompt: str = "consent",
) -> str:
    """Build Google OAuth authorization URL."""
    config = _get_config()

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "redirect_uris": [config.redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=config.scopes,
        redirect_uri=config.redirect_uri,
    )

    auth_url, _ = flow.authorization_url(
        access_type=access_type,
        prompt=prompt,
        state=state,
        include_granted_scopes="true",
    )
    return cast(str, auth_url)


async def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Exchange authorization code for access/refresh tokens."""
    config = _get_config()

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "redirect_uris": [config.redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=config.scopes,
        redirect_uri=config.redirect_uri,
    )

    flow.fetch_token(code=code)
    credentials = flow.credentials

    return {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "expires_at": credentials.expiry.isoformat() if credentials.expiry else "",
        "scope": " ".join(credentials.scopes) if credentials.scopes else "",
        "token_type": "Bearer",
    }


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """Refresh access token using refresh token."""
    config = _get_config()

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.client_id,
        client_secret=config.client_secret,
        scopes=config.scopes,
    )

    request = Request()
    credentials.refresh(request)

    return {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "expires_at": credentials.expiry.isoformat() if credentials.expiry else "",
        "scope": " ".join(credentials.scopes) if credentials.scopes else "",
        "token_type": "Bearer",
    }


async def revoke_token(access_token: str) -> bool:
    """Revoke access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": access_token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    return response.status_code == 200


def create_credentials(access_token: str, refresh_token: str | None, scopes: list[str] | None = None) -> Credentials:
    """Create Google Credentials object from tokens."""
    config = _get_config()
    return Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.client_id,
        client_secret=config.client_secret,
        scopes=scopes or config.scopes,
    )