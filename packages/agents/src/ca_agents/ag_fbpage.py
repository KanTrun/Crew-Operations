"""
AG-FBPAGE: Facebook Page Agent

Handles incoming Facebook Messenger messages, classifies intent,
matches response rules, and either auto-responds or queues for approval.

Architecture:
    webhook → message → classify → rules_engine → [send | queue]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from datetime import datetime, timezone


@dataclass(frozen=True)
class FBMessageInput:
    """Standardized Facebook message input."""
    
    psid: str                    # Page Scope ID (customer identifier)
    text: str                    # Message text
    message_id: str              # Facebook message ID
    timestamp: float             # Unix timestamp
    sender_name: str | None = None  # Customer name if available


@dataclass(frozen=True) 
class FBMessageOutput:
    """Result of processing a Facebook message."""
    
    action: str                  # "auto_respond" | "queue_to_inbox" | "error"
    response: str | None         # Response sent (if auto_respond)
    intent: str                  # Classified intent
    confidence: float            # Intent confidence (0.0 - 1.0)
    reason: str | None = None    # Why this action was taken
    error: str | None = None     # Error message if action=="error"


async def process_fb_message(
    input_msg: FBMessageInput,
    *,
    confidence_threshold: float = 0.8,
    auto_respond_enabled: bool = True
) -> FBMessageOutput:
    """
    Process a Facebook message: classify intent → match rule → action.
    
    Flow:
        1. Classify message intent using AG-MSG
        2. Look up response rule for intent
        3. If confidence >= threshold AND auto enabled → auto-respond
        4. Else → queue to manager inbox for approval
        5. Log to fb_message_log + analytics
    
    Args:
        input_msg: Parsed Facebook message
        confidence_threshold: Min confidence for auto-response (0.0-1.0)
        auto_respond_enabled: Enable auto-responses (can be disabled for testing)
    
    Returns:
        FBMessageOutput with action taken and result
    """
    
    # Placeholder - will be implemented in phase 2
    # For now, just return error to prompt implementation
    
    return FBMessageOutput(
        action="error",
        response=None,
        intent="",
        confidence=0.0,
        error="AG-FBPAGE not yet implemented. This is a placeholder."
    )


async def parse_fb_webhook_message(entry: dict[str, Any]) -> FBMessageInput | None:
    """
    Parse incoming Facebook webhook entry to FBMessageInput.
    
    Format from Facebook Messenger Platform:
    {
        "sender": {"id": "<PSID>"},
        "recipient": {"id": "<PAGE_ID>"},
        "timestamp": 1458692752478,
        "message": {
            "mid": "<MESSAGE_ID>",
            "text": "hello, what is your latency?"
        }
    }
    """
    
    try:
        messaging = entry.get("messaging", [{}])[0]
        message = messaging.get("message", {})
        sender_id = messaging.get("sender", {}).get("id")
        
        if not sender_id or not message.get("text"):
            return None
        
        return FBMessageInput(
            psid=sender_id,
            text=message["text"].strip(),
            message_id=message.get("mid", ""),
            timestamp=messaging.get("timestamp", 0),
            sender_name=None  # Could parse from Graph API if needed
        )
    
    except (KeyError, TypeError, IndexError):
        return None


__all__ = [
    "FBMessageInput",
    "FBMessageOutput",
    "process_fb_message",
    "parse_fb_webhook_message"
]
