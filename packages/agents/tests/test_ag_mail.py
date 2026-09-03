from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from ca_agents.ag_mail import send_mail


def test_send_mail_empty_recipient() -> None:
    res = send_mail(to_emails=[], subject="Test", body="No recipient")
    assert not res.ok
    assert res.reason == "no_recipient_email"


def test_send_mail_replay_mode(tmp_path: pytest.TempPathFactory) -> None:
    log_file = tmp_path / "mail.jsonl"
    with patch.dict(os.environ, {"CA_AGENT_MODE": "replay", "NHIPQUAN_MAIL_LOG": str(log_file)}):
        res = send_mail(to_emails=["test@example.com"], subject="Xin chào", body="Nội dung test")
        assert res.ok
        assert res.mode == "replay"
        assert len(res.sent) == 1
        assert res.sent[0]["status"] == "queued_replay"
        assert log_file.exists()
        assert "Xin chào" in log_file.read_text(encoding="utf-8")


def test_send_mail_smtp_port_587(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setenv("NHIPQUAN_SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("NHIPQUAN_SMTP_PORT", "587")
    monkeypatch.setenv("NHIPQUAN_SMTP_USER", "shop@gmail.com")
    monkeypatch.setenv("NHIPQUAN_SMTP_PASSWORD", "abcd efgh ijkl mnop")
    monkeypatch.setenv("NHIPQUAN_SMTP_FROM", "Nhịp Quán <shop@gmail.com>")

    mock_smtp = MagicMock()
    mock_instance = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_instance

    with patch("smtplib.SMTP", mock_smtp):
        res = send_mail(
            to_emails=["nv1@gmail.com", "nv2@gmail.com"],
            subject="Lịch ca tuần",
            body="Thông báo ca",
            mode="live",
        )
        assert res.ok
        assert res.mode == "smtp"
        assert len(res.sent) == 2
        mock_instance.starttls.assert_called()
        mock_instance.login.assert_called_with("shop@gmail.com", "abcdefghijklmnop")
        assert mock_instance.sendmail.call_count == 2


def test_send_mail_smtp_port_465(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setenv("NHIPQUAN_SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("NHIPQUAN_SMTP_PORT", "465")
    monkeypatch.setenv("NHIPQUAN_SMTP_USER", "shop@gmail.com")
    monkeypatch.setenv("NHIPQUAN_SMTP_PASSWORD", "secret123")

    mock_smtp_ssl = MagicMock()
    mock_instance = MagicMock()
    mock_smtp_ssl.return_value.__enter__.return_value = mock_instance

    with patch("smtplib.SMTP_SSL", mock_smtp_ssl):
        res = send_mail(
            to_emails=["nv@gmail.com"],
            subject="Khẩn",
            body="Bù ca khẩn",
            mode="live",
        )
        assert res.ok
        assert res.mode == "smtp"
        mock_instance.login.assert_called_with("shop@gmail.com", "secret123")
        assert mock_instance.sendmail.call_count == 1


def test_send_mail_smtp_login_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setenv("NHIPQUAN_SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("NHIPQUAN_SMTP_PORT", "587")
    monkeypatch.setenv("NHIPQUAN_SMTP_USER", "shop@gmail.com")
    monkeypatch.setenv("NHIPQUAN_SMTP_PASSWORD", "bad_pass")

    mock_smtp = MagicMock()
    mock_instance = MagicMock()
    mock_instance.login.side_effect = Exception("535 Authentication failed")
    mock_smtp.return_value.__enter__.return_value = mock_instance

    with patch("smtplib.SMTP", mock_smtp):
        res = send_mail(
            to_emails=["nv1@gmail.com", "nv2@gmail.com"],
            subject="Test",
            body="Test",
            mode="live",
        )
        assert not res.ok
        assert res.mode == "smtp"
        assert len(res.failed) == 2
        assert "535 Authentication failed" in res.failed[0]["reason"]


def test_send_mail_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setenv("NHIPQUAN_SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("NHIPQUAN_SMTP_PORT", "587")
    monkeypatch.setenv("NHIPQUAN_SMTP_USER", "shop@gmail.com")
    monkeypatch.setenv("NHIPQUAN_SMTP_PASSWORD", "secret")

    mock_smtp = MagicMock()
    mock_instance = MagicMock()
    # First send succeeds, second fails
    mock_instance.sendmail.side_effect = [None, Exception("Invalid recipient address")]
    mock_smtp.return_value.__enter__.return_value = mock_instance

    with patch("smtplib.SMTP", mock_smtp):
        res = send_mail(
            to_emails=["good@gmail.com", "bad@gmail.com"],
            subject="Test",
            body="Test",
            mode="live",
        )
        assert len(res.sent) == 1
        assert len(res.failed) == 1
        assert res.sent[0]["email"] == "good@gmail.com"
        assert res.failed[0]["email"] == "bad@gmail.com"
        assert res.reason == "some_failed"


def test_send_mail_with_attachments_replay(tmp_path: pytest.TempPathFactory) -> None:
    log_file = tmp_path / "mail_att.jsonl"
    dummy_img = tmp_path / "lich_ca.png"
    dummy_img.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake")

    with patch.dict(os.environ, {"CA_AGENT_MODE": "replay", "NHIPQUAN_MAIL_LOG": str(log_file)}):
        res = send_mail(
            to_emails=["lan@example.com"],
            subject="Lịch ca tuần kèm ảnh",
            body="Gửi Lan ảnh lịch tuần",
            attachments=[
                {"filename": "lich_ca.png", "path": str(dummy_img), "is_inline": True, "cid": "lich_img"},
                {"filename": "quy_dinh.pdf", "content_bytes": b"%PDF-1.4...", "content_type": "application/pdf"},
            ],
        )
        assert res.ok
        assert res.mode == "replay"
        assert log_file.exists()
        logged_text = log_file.read_text(encoding="utf-8")
        assert "lich_ca.png" in logged_text
        assert "quy_dinh.pdf" in logged_text


def test_build_mime_message_attachment_structure() -> None:
    from ca_agents.ag_mail import _build_mime_message

    msg = _build_mime_message(
        sender="quan@example.com",
        recipient="nhanvien@example.com",
        subject="Ảnh thực đơn mới",
        body="Chào bạn, đây là thực đơn mới.",
        html_body="<p>Chào bạn, đây là thực đơn mới:</p><img src='cid:menu_cid'/>",
        attachments=[
            {
                "filename": "menu_moi.png",
                "content_bytes": b"\x89PNGfakeimage",
                "cid": "menu_cid",
                "is_inline": True,
            }
        ],
    )
    assert msg["Subject"] == "Ảnh thực đơn mới"
    assert msg.is_multipart()
    payload = msg.get_payload()
    assert len(payload) >= 2

