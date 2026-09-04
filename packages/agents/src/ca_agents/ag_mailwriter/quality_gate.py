"""Deterministic Gmail quality gate; never delegates send eligibility to an LLM."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

THRESHOLD_VERSION = "gmail-v1"
GMAIL_THRESHOLD = {"score": 0.80, "accuracy": 0.90, "safety": 0.90}
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}|<[^<>]+>|\[TODO\]", re.IGNORECASE)
_INTERNAL_DATA_RE = re.compile(r"(?:api[_ -]?key|access[_ -]?token|app[_ -]?password|mật khẩu|system prompt)", re.IGNORECASE)
_INJECTION_RE = re.compile(r"(?:ignore previous|bỏ qua.*hướng dẫn|system prompt|jailbreak)", re.IGNORECASE)
_FINANCIAL_PROMISE_RE = re.compile(r"(?:hoàn tiền|đền bù|bồi thường)", re.IGNORECASE)


@dataclass(frozen=True)
class QualityGateResult:
    passed: bool
    action: Literal["send", "queue_review", "block"]
    score: float
    flags: list[str]
    hard_fail_flags: list[str]
    threshold_version: str = THRESHOLD_VERSION
    threshold_store_id: str = "quan_01"
    scores: dict[str, float] | None = None


def feedback_diff(original_subject: str, original_body: str, final_subject: str, final_body: str) -> dict[str, Any]:
    """Return exact changed fields for a human review/edit feedback event."""
    edited_fields = [field for field, original, final in (
        ("subject", original_subject, final_subject),
        ("body", original_body, final_body),
    ) if original != final]
    return {
        "edited_fields": edited_fields,
        "materially_edited": bool(edited_fields),
        "original": {"subject": original_subject, "body": original_body},
        "final": {"subject": final_subject, "body": final_body},
    }


def evaluate_gmail(*, recipients: list[str], subject: str, body: str, store_id: str = "quan_01", store_name: str = "Nhịp Quán", ops_context: dict[str, Any] | None = None) -> QualityGateResult:
    """Evaluate mail safety and quality using fixed, auditable checks and weights."""
    flags: list[str] = []
    hard_fails: list[str] = []
    text = f"{subject}\n{body}"
    if not subject.strip() or not body.strip():
        hard_fails.append("missing_subject_or_body")
    if not recipients or any(not _EMAIL_RE.fullmatch(email.strip()) for email in recipients):
        hard_fails.append("invalid_recipient")
    if _INTERNAL_DATA_RE.search(text):
        hard_fails.append("internal_data_exposure")
    if _INJECTION_RE.search(text):
        hard_fails.append("prompt_injection")
    if ops_context:
        for key in ("gio", "ngay", "mat_hang", "ton_kho", "nguong", "doanh_thu", "so_don"):
            value = ops_context.get(key)
            if value not in (None, "") and str(value) not in text:
                hard_fails.append("factual_mismatch")
                break
    if not subject.startswith(f"[{store_name}]"):
        flags.append("missing_store_subject_prefix")
    if len(subject) > 120:
        flags.append("subject_too_long")
    if _PLACEHOLDER_RE.search(text):
        flags.append("placeholder")
    if _FINANCIAL_PROMISE_RE.search(text):
        flags.append("financial_commitment")
    if not re.search(r"(?:thân gửi|chào)", body, re.IGNORECASE):
        flags.append("missing_greeting")
    if not re.search(r"(?:trân trọng|thân mến|ban quản lý)", body, re.IGNORECASE):
        flags.append("missing_signature")
    if len(body) > 4000:
        flags.append("unusually_long")

    scores = {
        "accuracy": 0.0 if "factual_mismatch" in hard_fails else 1.0,
        "safety": 0.0 if hard_fails else 1.0,
        "completeness": 1.0 if not {"missing_greeting", "missing_signature", "placeholder"}.intersection(flags) else 0.7,
        "tone": 1.0 if "missing_greeting" not in flags else 0.7,
        "actionability": 1.0,
        "personalization": 1.0,
    }
    score = round(
        0.30 * scores["accuracy"] + 0.20 * scores["safety"] + 0.15 * scores["completeness"]
        + 0.15 * scores["tone"] + 0.10 * scores["actionability"] + 0.10 * scores["personalization"], 4
    )
    passed = score >= GMAIL_THRESHOLD["score"] and scores["safety"] >= GMAIL_THRESHOLD["safety"] and scores["accuracy"] >= GMAIL_THRESHOLD["accuracy"] and not hard_fails
    action: Literal["send", "queue_review", "block"] = "block" if hard_fails else "queue_review" if flags else "send"
    return QualityGateResult(passed=passed, action=action, score=score, flags=flags, hard_fail_flags=hard_fails, threshold_store_id=store_id, scores=scores)