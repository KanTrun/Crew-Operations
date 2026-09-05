"""Guardrails & Security Filters for Customer-Facing Agents (AG-FBPAGE)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Whitelist of tool functions callable by the customer chatbot
ALLOWED_PUBLIC_TOOLS = frozenset(
    {
        "get_public_menu",
        "get_store_profile",
        "get_active_promotions",
    }
)

# Known prompt injection patterns (Vietnamese & English)
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"bỏ\s+qua\s+(toàn\s+bộ\s+)?(hướng\s+dẫn|chỉ\s+dẫn|lệnh|quy\s+tắc)",
    r"quên\s+(hết|tất\s+cả)\s+(hướng\s+dẫn|quy\s+tắc)",
    r"system\s+prompt",
    r"developer\s+mode",
    r"chế\s+độ\s+nhà\s+phát\s+triển",
    r"tiết\s+lộ\s+(system\s+prompt|hướng\s+dẫn\s+hệ\s+thống|công\s+thức\s+bí\s+mật|dữ\s+liệu\s+nội\s+bộ|mật\s+khẩu|doanh\s+thu|giá\s+vốn)",
    r"bạn\s+là\s+ai\s+trước\s+khi",
    r"đóng\s+vai\s+(hacker|admin|chủ\s+quán)",
    r"act\s+as\s+(an\s+unrestricted|admin|developer)",
    r"jailbreak",
    r"dump\s+database",
    r"drop\s+table",
    r"select\s+.*\s+from\s+",
    r"union\s+select",
]

_INJECTION_REGEX = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


@dataclass(frozen=True)
class GuardrailResult:
    is_safe: bool
    reason: str | None = None
    sanitized_text: str = ""


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Clean control characters and limit text length."""
    if not text:
        return ""
    # Strip null bytes and control characters except common whitespace
    cleaned = "".join(
        ch for ch in text if ch == "\n" or ch == "\t" or (ord(ch) >= 32 and ord(ch) != 127)
    )
    return cleaned.strip()[:max_length]


def check_input_guardrail(text: str) -> GuardrailResult:
    """Validate user input against prompt injection and malicious intents."""
    cleaned = sanitize_input(text)
    if not cleaned:
        return GuardrailResult(is_safe=False, reason="empty_input", sanitized_text="")

    if _INJECTION_REGEX.search(cleaned):
        return GuardrailResult(
            is_safe=False,
            reason="prompt_injection_detected",
            sanitized_text=cleaned,
        )

    return GuardrailResult(is_safe=True, reason=None, sanitized_text=cleaned)


def is_tool_allowed(tool_name: str) -> bool:
    """Validate that tool call is strictly within the public whitelist."""
    return tool_name in ALLOWED_PUBLIC_TOOLS


def normalize_text(text: str) -> str:
    """Chuẩn hóa văn bản để so khớp từ khóa (kế hoạch §6.2c).

    Hạ chữ thường, bỏ dấu tiếng Việt (NFD + bỏ category Mn), quy 'đ'→'d',
    bỏ ký tự chèn giữa từ để né filter (dấu chấm, gạch, ký tự đặc biệt),
    gộp khoảng trắng. Dùng chung cho fb_policy / supervisor / eval.
    """
    lowered = text.lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    ascii_text = stripped.replace("đ", "d")
    cleaned = re.sub(r"[^a-z0-9\s]", "", ascii_text)
    collapsed = re.sub(r"\s+", " ", cleaned).strip()
    # Nối các chữ cái rời bị chèn khoảng trắng để né filter (vd: "ch í" -> "chi", "b a o" -> "bao")
    merged = re.sub(r"(?<=[a-z])\s+([a-z])(?=\s|$)", r"\1", collapsed)
    # Rút gọn ký tự lặp do gõ dính / telex (vd: "baoo" -> "bao", "dd" -> "d")
    de_duped = re.sub(r"([aeouid])\1+", r"\1", merged)
    return re.sub(r"\s+", " ", de_duped).strip()
