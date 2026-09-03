"""Mail service — gửi email cho nhân viên (SMTP thật nếu cấu hình, fallback replay).

Trong `CA_AGENT_MODE=replay` (CI), chỉ ghi log "mail" mà không gửi thật.
Cấu hình SMTP qua env:
  NHIPQUAN_SMTP_HOST / NHIPQUAN_SMTP_PORT / NHIPQUAN_SMTP_USER
  NHIPQUAN_SMTP_PASSWORD / NHIPQUAN_SMTP_FROM
"""

from __future__ import annotations

import json
import os
import smtplib
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from pathlib import Path


@dataclass
class MailResult:
    ok: bool
    sent: list[dict[str, str]] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    mode: str = "replay"
    reason: str = ""


def _smtp_configured() -> bool:
    return bool(os.environ.get("NHIPQUAN_SMTP_HOST") and os.environ.get("NHIPQUAN_SMTP_USER"))


def send_mail(
    *,
    to_emails: list[str],
    subject: str,
    body: str,
    mode: str | None = None,
) -> MailResult:
    """Gửi email tới danh sách. Nếu SMTP chưa cấu hình / replay → ghi log, không gửi thật.

    `body` là plain text tiếng Việt (đã có nội dung từ AI/tool).
    """
    mode = mode or os.environ.get("CA_AGENT_MODE", "replay")
    to = [t.strip() for t in to_emails if t and t.strip()]

    if not to:
        return MailResult(ok=False, mode=mode, reason="no_recipient_email")

    if mode == "replay" or not _smtp_configured():
        # Replay / chưa cấu hình: chỉ ghi nhật ký, không gửi thật.
        _log_mail_replay(to, subject, body, mode)
        return MailResult(
            ok=True,
            sent=[{"email": t, "status": "queued_replay"} for t in to],
            mode=mode if mode == "replay" else "stub",
            reason="smtp_not_configured_or_replay",
        )

    # Gửi thật qua SMTP
    sent: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    host = os.environ["NHIPQUAN_SMTP_HOST"]
    port = int(os.environ.get("NHIPQUAN_SMTP_PORT", "587"))
    user = os.environ["NHIPQUAN_SMTP_USER"]
    password = os.environ["NHIPQUAN_SMTP_PASSWORD"]
    sender = os.environ.get("NHIPQUAN_SMTP_FROM", user)

    for t in to:
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = t
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.starttls()
                server.login(user, password)
                server.sendmail(sender, [t], msg.as_string())
            sent.append({"email": t, "status": "sent"})
        except Exception as exc:  # noqa: BLE001
            failed.append({"email": t, "status": "failed", "reason": str(exc)[:120]})

    return MailResult(
        ok=bool(sent) or not failed,
        sent=sent,
        failed=failed,
        mode="smtp",
        reason="" if not failed else "some_failed",
    )


def _log_mail_replay(to: list[str], subject: str, body: str, mode: str) -> None:
    """Ghi nhật ký mail trong replay/stub — đủ để test + trace."""
    try:
        path = Path(os.environ.get("NHIPQUAN_MAIL_LOG", "data/out/mail_log.jsonl"))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {"mode": mode, "to": to, "subject": subject, "body": body},
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:  # noqa: BLE001
        pass
