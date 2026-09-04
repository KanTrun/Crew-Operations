"""Deterministic minimization before AI-learning data reaches SQLite."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?84|0)\d{8,10}(?!\d)")
_SENSITIVE_KEYS = {"email", "phone", "phone_number", "address", "external_psid", "token", "access_token", "app_password", "password", "secret"}


def redact_text(value: str) -> str:
    return _PHONE.sub("[phone_redacted]", _EMAIL.sub("[email_redacted]", value))


def redact_record(record: dict[str, Any], *, minimal_data: bool) -> dict[str, Any]:
    """Remove direct identifiers; minimal mode also replaces draft content with hashes."""
    def clean(value: Any, key: str = "") -> Any:
        if key.lower() in _SENSITIVE_KEYS and value is not None:
            return f"sha256:{hashlib.sha256(str(value).encode()).hexdigest()}"
        if isinstance(value, dict):
            return {str(child_key): clean(child, str(child_key)) for child_key, child in value.items()}
        if isinstance(value, list):
            return [clean(child) for child in value]
        return redact_text(value) if isinstance(value, str) else value

    cleaned = clean(record)
    if minimal_data:
        for field in ("draft", "original", "final"):
            value = cleaned.get(field)
            if isinstance(value, dict):
                cleaned[field] = {key: f"sha256:{hashlib.sha256(str(item).encode()).hexdigest()}" for key, item in value.items() if item is not None}
    return cleaned