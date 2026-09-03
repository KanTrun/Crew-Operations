"""Mail service — gửi email cho nhân viên (SMTP thật nếu cấu hình, fallback replay).

Trong `CA_AGENT_MODE=replay` (CI), chỉ ghi log "mail" mà không gửi thật.
Cấu hình SMTP qua env:
  NHIPQUAN_SMTP_HOST / NHIPQUAN_SMTP_PORT / NHIPQUAN_SMTP_USER
  NHIPQUAN_SMTP_PASSWORD / NHIPQUAN_SMTP_FROM
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import smtplib
from dataclasses import dataclass, field
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any


@dataclass
class MailResult:
    ok: bool
    sent: list[dict[str, str]] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    mode: str = "replay"
    reason: str = ""


def _smtp_configured() -> bool:
    return bool(os.environ.get("NHIPQUAN_SMTP_HOST") and os.environ.get("NHIPQUAN_SMTP_USER"))


def _build_mime_message(
    sender: str,
    recipient: str,
    subject: str,
    body: str,
    html_body: str | None = None,
    attachments: list[dict[str, Any] | str] | None = None,
) -> MIMEMultipart | MIMEText:
    """Tạo thông điệp MIME hỗ trợ cả plain text, HTML và đính kèm hình ảnh / file."""
    valid_attachments = attachments or []

    if not valid_attachments and not html_body:
        msg: MIMEMultipart | MIMEText = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = sender
        msg["To"] = recipient
        return msg

    has_inline = any(
        isinstance(a, dict) and (a.get("is_inline") or a.get("cid"))
        for a in valid_attachments
    )

    root_type = "related" if (has_inline and html_body) else "mixed"
    msg = MIMEMultipart(root_type)
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = sender
    msg["To"] = recipient

    if html_body:
        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(body, "plain", "utf-8"))
        alt_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt_part)
    else:
        msg.attach(MIMEText(body, "plain", "utf-8"))

    for att in valid_attachments:
        filename = "attachment"
        content_bytes = b""
        ctype = "application/octet-stream"
        cid = None
        is_inline = False

        if isinstance(att, str):
            fpath = Path(att)
            filename = fpath.name
            if fpath.exists():
                content_bytes = fpath.read_bytes()
            guessed, _ = mimetypes.guess_type(filename)
            if guessed:
                ctype = guessed
        elif isinstance(att, dict):
            filename = att.get("filename") or "attachment"
            cid = att.get("cid")
            is_inline = bool(att.get("is_inline")) or bool(cid)

            if att.get("content_bytes") and isinstance(att["content_bytes"], bytes):
                content_bytes = att["content_bytes"]
            elif att.get("content_base64"):
                try:
                    content_bytes = base64.b64decode(att["content_base64"])
                except Exception:
                    content_bytes = b""
            elif att.get("path") and Path(att["path"]).exists():
                content_bytes = Path(att["path"]).read_bytes()

            if att.get("content_type"):
                ctype = att["content_type"]
            else:
                guessed, _ = mimetypes.guess_type(filename)
                if guessed:
                    ctype = guessed

        if not content_bytes:
            continue

        maintype, subtype = ctype.split("/", 1) if "/" in ctype else ("application", "octet-stream")

        if maintype == "image":
            part: MIMEBase = MIMEImage(content_bytes, _subtype=subtype)
        else:
            part = MIMEBase(maintype, subtype)
            part.set_payload(content_bytes)
            encoders.encode_base64(part)

        if cid:
            clean_cid = cid.strip("<>")
            part.add_header("Content-ID", f"<{clean_cid}>")
            part.add_header("Content-Disposition", "inline", filename=filename)
        elif is_inline:
            part.add_header("Content-Disposition", "inline", filename=filename)
        else:
            part.add_header("Content-Disposition", "attachment", filename=filename)

        msg.attach(part)

    return msg


def send_mail(
    *,
    to_emails: list[str],
    subject: str,
    body: str,
    html_body: str | None = None,
    attachments: list[dict[str, Any] | str] | None = None,
    mode: str | None = None,
) -> MailResult:
    """Gửi email tới danh sách. Hỗ trợ hình ảnh đính kèm và inline CID.
    
    Nếu SMTP chưa cấu hình / replay → ghi log, không gửi thật.
    """
    mode = mode or os.environ.get("CA_AGENT_MODE", "replay")
    to = [t.strip() for t in to_emails if t and t.strip()]

    if not to:
        return MailResult(ok=False, mode=mode, reason="no_recipient_email")

    if mode == "replay" or not _smtp_configured():
        _log_mail_replay(to, subject, body, mode, html_body=html_body, attachments=attachments)
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
    password = os.environ["NHIPQUAN_SMTP_PASSWORD"].strip()
    if ("gmail" in host.lower() or "google" in host.lower()) and " " in password:
        password = password.replace(" ", "")
    sender = os.environ.get("NHIPQUAN_SMTP_FROM", user)

    try:
        server_ctx = (
            smtplib.SMTP_SSL(host, port, timeout=15)
            if port == 465
            else smtplib.SMTP(host, port, timeout=15)
        )
        with server_ctx as server:
            if port != 465:
                server.starttls()
            server.login(user, password)
            for t in to:
                try:
                    msg = _build_mime_message(
                        sender=sender,
                        recipient=t,
                        subject=subject,
                        body=body,
                        html_body=html_body,
                        attachments=attachments,
                    )
                    server.sendmail(sender, [t], msg.as_string())
                    sent.append({"email": t, "status": "sent"})
                except Exception as exc:  # noqa: BLE001
                    failed.append({"email": t, "status": "failed", "reason": str(exc)[:120]})
    except Exception as exc:  # noqa: BLE001
        reason_str = str(exc)[:120]
        already_handled = {s["email"] for s in sent} | {f["email"] for f in failed}
        for t in to:
            if t not in already_handled:
                failed.append({"email": t, "status": "failed", "reason": reason_str})

    return MailResult(
        ok=bool(sent) or not failed,
        sent=sent,
        failed=failed,
        mode="smtp",
        reason="" if not failed else "some_failed",
    )


def _log_mail_replay(
    to: list[str],
    subject: str,
    body: str,
    mode: str,
    html_body: str | None = None,
    attachments: list[dict[str, Any] | str] | None = None,
) -> None:
    """Ghi nhật ký mail trong replay/stub — lưu cả thông tin file/ảnh đính kèm."""
    try:
        path = Path(os.environ.get("NHIPQUAN_MAIL_LOG", "data/out/mail_log.jsonl"))
        path.parent.mkdir(parents=True, exist_ok=True)

        att_summary = []
        if attachments:
            for a in attachments:
                if isinstance(a, str):
                    att_summary.append({"filename": Path(a).name})
                elif isinstance(a, dict):
                    att_summary.append({
                        "filename": a.get("filename") or "file",
                        "cid": a.get("cid"),
                        "is_inline": bool(a.get("is_inline") or a.get("cid")),
                    })

        with path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "mode": mode,
                        "to": to,
                        "subject": subject,
                        "body": body,
                        "has_html": bool(html_body),
                        "attachments": att_summary,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:  # noqa: BLE001
        pass
