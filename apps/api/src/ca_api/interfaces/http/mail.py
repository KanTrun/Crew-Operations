"""HTTP router: user profile (email) + mail sending."""

from __future__ import annotations

import os
from typing import Annotated, Any

from ca_agents.ag_mail import send_mail
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ca_api.interfaces.http.sprint3 import _require_manager, _require_role
from ca_api.persist import get_user_emails, session, set_user_email

router = APIRouter(tags=["mail"])


class UpdateEmailBody(BaseModel):
    email: str = Field(min_length=3, max_length=120)


class SendMailBody(BaseModel):
    to_nv_ids: list[str] = Field(min_length=1)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)


@router.get("/api/v1/me/profile")
def get_profile(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Trả profile của nick đang đăng nhập (gồm email)."""
    s = session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    return {"username": s["username"], "role": s["role"], "nv_id": s["nv_id"], "email": s.get("email", "")}


@router.patch("/api/v1/me/profile/email")
def patch_email(
    body: UpdateEmailBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Nick cập nhật gmail của chính mình (người gửi thấy email này)."""
    s = session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    try:
        from ca_api.persist import DangKyLoi

        res = set_user_email(s["username"], body.email)
    except DangKyLoi as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, **res}


@router.get("/api/v1/users/emails")
def users_emails(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Chủ/quản lý xem danh sách email nhân viên đã cập nhật (để gửi mail)."""
    _require_manager(authorization)
    return {"emails": get_user_emails()}


@router.post("/api/v1/mail/send")
def mail_send(
    body: SendMailBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Chủ/quản lý gửi email cho nhân viên theo nv_id.

    - Lấy email từ user table (nhân viên phải tự cập nhật gmail ở trang /toi).
    - Replay/stub mode: chỉ ghi log, không gửi thật (an toàn CI).
    """
    _require_manager(authorization)
    emails_nguoi = get_user_emails()
    to_emails: list[str] = []
    missing: list[str] = []
    for nv in body.to_nv_ids:
        em = emails_nguoi.get(nv)
        if em:
            to_emails.append(em)
        else:
            missing.append(nv)

    if not to_emails:
        return {
            "ok": False,
            "mode": os.environ.get("CA_AGENT_MODE", "replay"),
            "missing": missing,
            "detail": "khong_tim_thay_email",
        }

    res = send_mail(to_emails=to_emails, subject=body.subject, body=body.body)
    return {
        "ok": res.ok,
        "mode": res.mode,
        "sent": res.sent,
        "failed": res.failed,
        "missing": missing,
        "reason": res.reason,
    }
