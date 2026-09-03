"""Tests — feature flag auto-send + endpoint /api/v1/page/fb-policy (kế hoạch §5.5).

Flag OFF (mặc định): pipeline ghi auto_sent nhưng webhook KHÔNG gửi thật.
Flag ON: chỉ nhánh policy auto + supervisor pass mới gửi.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from unit.auth_util import headers


@pytest.fixture()
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    monkeypatch.setenv("NHIPQUAN_PAGE_MODE", "live")
    monkeypatch.setenv("NHIPQUAN_FB_PAGE_TOKEN", "tok_test")
    monkeypatch.setenv("NHIPQUAN_FB_PAGE_ID", "page_1")
    monkeypatch.delenv("NHIPQUAN_FB_APP_SECRET", raising=False)
    monkeypatch.setenv("NHIPQUAN_FB_AUTO_SEND", "0")
    monkeypatch.setenv("NHIPQUAN_DB", str(tmp_path / f"t_{uuid.uuid4().hex[:8]}.db"))

    import ca_api.persist as persist

    monkeypatch.setattr(persist, "_INITIALIZED", False)

    from ca_api.interfaces.http import channels as ch
    from ca_api.interfaces.http.main import app as fastapi_app

    sent: list[tuple[str, str]] = []

    def fake_send(psid: str, text: str, **kw: object) -> dict[str, object]:
        sent.append((psid, text))
        return {"ok": True}

    monkeypatch.setattr(ch, "send_messenger_text", fake_send)
    client = TestClient(fastapi_app)
    client.sent_calls = sent  # type: ignore[attr-defined]
    return client


def _post(client: TestClient, mid: str, text: str, psid: str = "psid_flag") -> object:
    return client.post(
        "/api/v1/channels/facebook/webhook",
        json={
            "entry": [
                {
                    "id": "page_1",
                    "messaging": [
                        {"sender": {"id": psid}, "message": {"mid": mid, "text": text}}
                    ],
                }
            ]
        },
    )


def test_policy_get_requires_manager(api: TestClient) -> None:
    assert api.get("/api/v1/page/fb-policy", headers=headers(api, "minh")).status_code == 403
    r = api.get("/api/v1/page/fb-policy", headers=headers(api, "lan"))
    assert r.status_code == 200
    body = r.json()
    assert body["auto_send_enabled"] is False  # mặc định OFF
    assert body["auto_price_cap_vnd"] == 100000


def test_policy_put_chu_quan_only(api: TestClient) -> None:
    denied = api.put(
        "/api/v1/page/fb-policy",
        json={"auto_send_enabled": True},
        headers=headers(api, "lan"),
    )
    assert denied.status_code == 403
    ok = api.put(
        "/api/v1/page/fb-policy",
        json={"auto_send_enabled": True, "note": "bật thử"},
        headers=headers(api, "hung"),
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["auto_send_enabled"] is True


def test_policy_put_negative_price_rejected(api: TestClient) -> None:
    r = api.put(
        "/api/v1/page/fb-policy",
        json={"auto_price_cap_vnd": -1},
        headers=headers(api, "hung"),
    )
    assert r.status_code == 400


def test_flag_off_auto_becomes_queue(api: TestClient) -> None:
    """Flag OFF: tin 'auto-able' KHÔNG gửi — phải vào queue cho QL duyệt."""
    from ca_api.services import fb_moderation as fm

    fm._RATE_LIMITER = type(fm._RATE_LIMITER)(now_fn=lambda: 1000.0)
    _post(api, "flag_off_1", "Quán mở cửa mấy giờ ạ?")
    calls = getattr(api, "sent_calls", [])
    assert len(calls) == 0, "flag OFF nhưng vẫn gửi thật!"
    items = api.get(
        "/api/v1/page/fb-inbox?status=pending", headers=headers(api, "lan")
    ).json()["items"]
    assert any("mở cửa mấy giờ" in str(i["message_text"]) for i in items)


def test_flag_on_auto_sends_for_safe_intent(api: TestClient, monkeypatch) -> None:
    """Flag ON: policy auto + supervisor pass → gửi thật qua Messenger."""
    monkeypatch.setenv("NHIPQUAN_FB_AUTO_SEND", "1")
    from ca_api.services import fb_moderation as fm

    fm._RATE_LIMITER = type(fm._RATE_LIMITER)(now_fn=lambda: 2000.0)
    _post(api, "flag_on_1", "Cà phê muối bao nhiêu tiền vậy ạ?")
    calls = getattr(api, "sent_calls", [])
    assert len(calls) == 1, f"flag ON nhưng không gửi: {calls}"
    psid, text = calls[0]
    assert psid == "psid_flag"
    # Nội dung phản hồi chứa thông tin menu (không khớp cứng định dạng)
    assert "menu" in text.lower() or "đ" in text


def test_flag_on_escalate_still_not_auto(api: TestClient, monkeypatch) -> None:
    """Flag ON nhưng tin escalate KHÔNG BAO GIỜ tự gửi — phải qua Chủ quán."""
    monkeypatch.setenv("NHIPQUAN_FB_AUTO_SEND", "1")
    from ca_api.services import fb_moderation as fm

    fm._RATE_LIMITER = type(fm._RATE_LIMITER)(now_fn=lambda: 3000.0)
    _post(api, "flag_on_esc", "Hôm qua uống bị ngộ độc quá")
    calls = getattr(api, "sent_calls", [])
    assert len(calls) == 0, "escalate bị tự gửi — NGUY HIỂM!"
