# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Audit luồng OAuth thật: Google redirect callback bằng GET, không kèm header.

Đây là lỗi tính năng: nếu callback chỉ nhận POST + bắt buộc header Authorization
thì trình duyệt (do Google điều hướng) KHÔNG BAO GIỜ hoàn tất được OAuth.
"""

from __future__ import annotations

from ca_api.interfaces.http.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

_BASE = "/api/v1/gmail"


def test_google_redirect_uri_accepts_get() -> None:
    """Google redirect người dùng bằng GET tới redirect_uri ⇒ phải có handler GET.

    Nếu chỉ có POST: trình duyệt nhận 405 và người dùng thấy trang lỗi —
    tính năng "Kết nối Gmail" không dùng được trong thực tế.
    """
    res = client.get(
        f"{_BASE}/oauth/callback?code=ma-gia&state=state-gia",
        follow_redirects=False,
    )
    assert res.status_code != 405, (
        "redirect_uri của Google là GET nhưng endpoint chỉ nhận POST ⇒ 405 tại trình duyệt"
    )


def test_get_callback_does_not_require_authorization_header() -> None:
    """Google không gửi header `Authorization` ⇒ handler GET không được đòi token.

    Với `state` đã lưu kèm nv_id, chính `state` là bằng chứng phiên — không cần
    header. Vậy handler GET phải chạy được mà không có header.
    """
    res = client.get(
        f"{_BASE}/oauth/callback?code=ma-gia&state=state-gia",
        follow_redirects=False,
    )
    assert res.status_code != 401, "Handler GET đòi Authorization ⇒ Google không gọi được"
