from __future__ import annotations

from ca_agents.ag_mailwriter.style_extractor import (
    extract_style_preferences,
    format_style_prompt,
)
from ca_agents.ag_mailwriter.writer import EmailDraft, draft_email

__all__ = [
    "EmailDraft",
    "draft_email",
    "extract_style_preferences",
    "format_style_prompt",
]
