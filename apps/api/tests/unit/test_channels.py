"""Kênh tin + Page quán — CI dùng replay; không giả dữ liệu quán."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from ca_agents.ag_msg import MsgResult
from ca_agents.messaging import InboundMessage
from ca_api.interfaces.http.channels import process_inbound
from ca_api.interfaces.http.main import app
from ca_api.persist import kv_get
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def test_channels_status_zalo_first_disconnected(monkeypatch: pytest.MonkeyPatch) -> None:
    # Neo env sạch: test khác (vd ag_meeting qua ensure_dotenv) có thể load .env
    # thật của máy vào os.environ và leak sang đây — phải cô lập để assert ổn định.
    monkeypatch.delenv("NHIPQUAN_ZALO_ENABLED", raising=False)
    monkeypatch.delenv("NHIPQUAN_ZALO_OA_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("NHIPQUAN_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("NHIPQUAN_FB_PAGE_TOKEN", raising=False)
    ql = headers(client, "lan")
    r = client.get("/api/v1/channels/status", headers=ql)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["uu_tien"][0] == "zalo"
    assert body["zalo"]["connected"] is False
    assert body["telegram"]["connected"] is False
    assert body["facebook"]["connected"] is False


def test_replay_forbidden_without_flag() -> None:
    ql = headers(client, "lan")
    r = client.post("/api/v1/channels/replay", json={"limit": 2}, headers=ql)
    assert r.status_code == 403


def test_bind_issue_and_inbound_enqueue(monkeypatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    nv = headers(client, "minh")
    issued = client.post("/api/v1/channels/bind/issue", headers=nv)
    assert issued.status_code == 200, issued.text
    code = issued.json()["code"]
    assert "Zalo" in issued.json()["huong_dan"] or "zalo" in issued.json()["huong_dan"].lower()

    bind = process_inbound(
        InboundMessage(text=f"/bind {code}", channel="zalo", external_user_id="z_user_1"),
        reply_backend="replay",
    )
    assert bind["ok"] is True
    assert bind["hanh"] == "bind"
    assert bind["nv_id"]

    enq = process_inbound(
        InboundMessage(
            text="em xin nghỉ ca sáng mai",
            channel="zalo",
            external_user_id="z_user_1",
        ),
        reply_backend="replay",
    )
    assert enq["ok"] is True
    assert enq["hanh"] == "enqueue"
    item = enq["item"]
    assert item["nguon"] == "zalo"
    assert item["nv_id"]
    assert item["trang_thai"] == "cho_duyet"

    ql = headers(client, "lan")
    items = client.get("/api/v1/inbox/rang-buoc", headers=ql).json()["items"]
    found = next(i for i in items if i["id"] == item["id"])
    assert found["nguon"] == "zalo"
    assert found.get("noi_dung_goc")


def test_live_inbound_llm_result_requires_manager_approval(monkeypatch) -> None:
    from ca_api.interfaces.http import channels as ch
    from ca_api.interfaces.http.sprint3 import _phan_cong

    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setattr(
        ch,
        "classify",
        lambda *args, **kwargs: MsgResult(
            intent="xin_nghi",
            tier=2,
            do_tin_cay=0.78,
            rang_buoc={"nguon": "llm", "can_xac_minh": True},
        ),
    )
    before = _phan_cong()
    nv = headers(client, "minh")
    code = client.post("/api/v1/channels/bind/issue", headers=nv).json()["code"]
    process_inbound(
        InboundMessage(text=f"/bind {code}", channel="telegram", external_user_id="tg_live"),
        reply_backend="replay",
    )

    result = process_inbound(
        InboundMessage(
            text="mai em có việc gia đình nên không đến được",
            channel="telegram",
            external_user_id="tg_live",
        ),
        reply_backend="replay",
    )

    assert result["hanh"] == "enqueue"
    assert result["item"]["trang_thai"] == "cho_duyet"
    assert result["item"]["rang_buoc"] == {"nguon": "llm", "can_xac_minh": True}
    assert _phan_cong() == before


def test_live_inbound_invalid_llm_result_does_not_enqueue(monkeypatch) -> None:
    from ca_api.interfaces.http import channels as ch

    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setattr(
        ch,
        "classify",
        lambda *args, **kwargs: MsgResult(
            intent="khac",
            tier=2,
            do_tin_cay=0.55,
            rang_buoc={"nguon": "tier2_fallback", "can_xac_minh": True},
        ),
    )
    nv = headers(client, "minh")
    code = client.post("/api/v1/channels/bind/issue", headers=nv).json()["code"]
    process_inbound(
        InboundMessage(text=f"/bind {code}", channel="telegram", external_user_id="tg_invalid"),
        reply_backend="replay",
    )

    result = process_inbound(
        InboundMessage(
            text="mai em có việc gia đình nên không đến được",
            channel="telegram",
            external_user_id="tg_invalid",
        ),
        reply_backend="replay",
    )

    assert result["hanh"] == "bo_qua"
    assert result["intent"] == "khac"


def test_xem_lich_after_bind(monkeypatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    nv = headers(client, "minh")
    code = client.post("/api/v1/channels/bind/issue", headers=nv).json()["code"]
    process_inbound(
        InboundMessage(text=f"/bind {code}", channel="telegram", external_user_id="tg_99"),
        reply_backend="replay",
    )
    r = process_inbound(
        InboundMessage(text="xem lịch của tôi", channel="telegram", external_user_id="tg_99"),
        reply_backend="replay",
    )
    assert r["ok"] is True
    assert r["hanh"] == "xem_lich"
    assert r["message"]["ok"] is True
    assert r["message"]["backend"] == "replay"


def test_inbox_duyet_doi_ca_opens_swap(monkeypatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    nv = headers(client, "minh")
    code = client.post("/api/v1/channels/bind/issue", headers=nv).json()["code"]
    process_inbound(
        InboundMessage(text=f"/bind {code}", channel="zalo", external_user_id="z_swap"),
        reply_backend="replay",
    )
    enq = process_inbound(
        InboundMessage(text="anh cho em đổi ca chiều", channel="zalo", external_user_id="z_swap"),
        reply_backend="replay",
    )
    item_id = enq["item"]["id"]
    # Force intent if classifier returns something else in replay
    from ca_api.persist import kv_mutate

    def force(items):
        for it in items:
            if it.get("id") == item_id:
                it["y_dinh"] = "doi_ca"
                it["nv_id"] = enq["item"]["nv_id"]
        return items

    kv_mutate("inbox_rang_buoc", force, [])

    ql = headers(client, "lan")
    decided = client.post(
        f"/api/v1/inbox/rang-buoc/{item_id}",
        json={"quyet_dinh": "duyet", "ca_id": "w1_c03", "doi_tac_nv_id": "nv_01"},
        headers=ql,
    )
    assert decided.status_code == 200, decided.text
    body = decided.json()
    assert body["trang_thai"] == "duyet"
    assert body.get("hieu_luc", {}).get("loai") == "cho_doi_ca"
    assert body["hieu_luc"].get("swap_id")
    swaps = kv_get("swap", [])
    hit = next(s for s in swaps if s.get("id") == body["hieu_luc"]["swap_id"])
    assert hit.get("ca_id") == "w1_c03"
    assert hit.get("b") == "nv_01"


def test_page_empty_without_fixture_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NHIPQUAN_PAGE_MODE", "disconnected")
    monkeypatch.delenv("NHIPQUAN_FB_PAGE_TOKEN", raising=False)
    monkeypatch.delenv("FACEBOOK_PAGE_ACCESS_TOKEN", raising=False)
    ql = headers(client, "lan")
    st = client.get("/api/v1/page/status", headers=ql)
    assert st.status_code == 200
    assert st.json()["connected"] is False
    th = client.get("/api/v1/page/threads", headers=ql)
    assert th.status_code == 200
    assert th.json()["items"] == []


def test_page_status_requires_successful_graph_health(monkeypatch) -> None:
    from ca_api.interfaces.http import channels as ch

    monkeypatch.setenv("NHIPQUAN_PAGE_MODE", "live")
    monkeypatch.setenv("NHIPQUAN_FB_PAGE_TOKEN", "invalid_test_token")
    monkeypatch.setenv("NHIPQUAN_FB_PAGE_ID", "page_1")
    monkeypatch.setattr(ch, "page_health", lambda: {"ok": False, "detail": "graph_http_401"})

    result = client.get("/api/v1/page/status", headers=headers(client, "lan"))

    assert result.status_code == 200
    assert result.json()["mode"] == "live"
    assert result.json()["connected"] is False
    assert result.json()["graph_ok"] is False
    assert result.json()["graph_detail"] == "graph_http_401"


def test_page_replay_remains_available_without_token(monkeypatch) -> None:
    from ca_api.persist import kv_set

    monkeypatch.setenv("NHIPQUAN_PAGE_MODE", "disconnected")
    monkeypatch.delenv("NHIPQUAN_FB_PAGE_TOKEN", raising=False)
    monkeypatch.setenv("NHIPQUAN_PAGE_SEED_FIXTURE", "1")
    kv_set("page_quan", None)

    result = client.get("/api/v1/page/threads", headers=headers(client, "lan"))

    assert result.status_code == 200
    assert result.json()["mode"] == "disconnected"
    assert isinstance(result.json()["items"], list)


def test_facebook_webhook_verify(monkeypatch) -> None:
    monkeypatch.setenv("NHIPQUAN_FB_WEBHOOK_VERIFY", "verify_test_token")
    r = client.get(
        "/api/v1/channels/facebook/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify_test_token",
            "hub.challenge": "12345",
        },
    )
    assert r.status_code == 200
    assert r.text == "12345"
    bad = client.get(
        "/api/v1/channels/facebook/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "sai",
            "hub.challenge": "12345",
        },
    )
    assert bad.status_code == 403


def test_facebook_webhook_inbound_live(monkeypatch) -> None:
    monkeypatch.setenv("NHIPQUAN_PAGE_MODE", "live")
    monkeypatch.setenv("NHIPQUAN_FB_PAGE_TOKEN", "tok_test")
    monkeypatch.setenv("NHIPQUAN_FB_PAGE_ID", "page_1")
    monkeypatch.setenv("NHIPQUAN_FB_APP_SECRET", "secret_test")
    from ca_api.persist import kv_set

    kv_set("page_quan", {"threads": [], "drafts": [], "mode": "live"})
    payload = {
            "entry": [
                {
                    "messaging": [
                        {
                            "sender": {"id": "psid_9"},
                            "message": {"mid": "m1", "text": "xin chào quán"},
                        }
                    ]
                }
            ]
        }
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(b"secret_test", body, hashlib.sha256).hexdigest()
    r = client.post(
        "/api/v1/channels/facebook/webhook",
        content=body,
        headers={"content-type": "application/json", "x-hub-signature-256": f"sha256={signature}"},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("n") == 1
    doc = kv_get("page_quan", {})
    assert any(t.get("psid") == "psid_9" for t in doc.get("threads", []))


def test_zalo_webhook_off_without_enabled() -> None:
    r = client.post(
        "/api/v1/channels/zalo/webhook",
        json={"message": {"text": "hi"}, "sender": {"id": "1"}},
    )
    assert r.status_code == 200
    assert r.json().get("ok") is False


def test_replay_with_flag(monkeypatch) -> None:
    monkeypatch.setenv("NHIPQUAN_ALLOW_MSG_REPLAY", "1")
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    ql = headers(client, "lan")
    # Bind fixture users so enqueue/xem_lich don't all fail chua_bind
    for uid, user in (("10001", "minh"), ("10003", "lan")):
        h = headers(client, user)
        code = client.post("/api/v1/channels/bind/issue", headers=h).json()["code"]
        process_inbound(
            InboundMessage(text=f"/bind {code}", channel="telegram", external_user_id=uid),
            reply_backend="replay",
        )
    r = client.post("/api/v1/channels/replay", json={"limit": 5}, headers=ql)
    assert r.status_code == 200, r.text
    assert r.json()["n"] >= 1


def test_staff_cannot_read_or_write_manager_inbox() -> None:
    staff = headers(client, "minh")
    assert client.get("/api/v1/inbox", headers=staff).status_code == 403
    assert client.get("/api/v1/inbox/rang-buoc", headers=staff).status_code == 403
    assert client.post("/api/v1/inbox", json={"tom_tat": "ngoai le"}, headers=staff).status_code == 403


def test_staff_channel_status_only_returns_own_bind(monkeypatch) -> None:
    from ca_api.persist import kenh_bind_set

    kenh_bind_set("telegram", "tg_minh", "nv_03")
    kenh_bind_set("telegram", "tg_lan", "nv_01")
    staff = headers(client, "minh")
    result = client.get("/api/v1/channels/status", headers=staff)
    assert result.status_code == 200
    assert result.json()["binds"] == [
        {"channel": "telegram", "external_user_id": "tg_minh", "nv_id": "nv_03", "created_at": result.json()["binds"][0]["created_at"]}
    ]


def test_staff_cannot_reply_or_create_treo_from_page() -> None:
    from ca_api.persist import kv_set

    kv_set("page_quan", {"threads": [{"id": "thread_1", "tom_tat": "Khach hoi mon"}], "drafts": []})
    staff = headers(client, "minh")
    assert client.get("/api/v1/page/threads", headers=staff).status_code == 403
    assert client.post("/api/v1/page/threads/thread_1/reply", json={"text": "Tra loi"}, headers=staff).status_code == 403
    assert client.post("/api/v1/page/treo", json={"thread_id": "thread_1"}, headers=staff).status_code == 403


def test_page_drafts_crud_and_ai_generate() -> None:
    from ca_api.persist import kv_set

    kv_set("page_quan", {"threads": [], "drafts": [], "mode": "mock"})
    ql = headers(client, "lan")
    staff = headers(client, "minh")

    # Staff forbidden
    assert client.post("/api/v1/page/drafts", json={"noi_dung": "Test"}, headers=staff).status_code == 403
    assert client.post("/api/v1/page/drafts/ai-generate", json={"topic": "Cafe"}, headers=staff).status_code == 403

    # QL tạo thủ công
    r_create = client.post("/api/v1/page/drafts", json={"noi_dung": "Bai nhap 1"}, headers=ql)
    assert r_create.status_code == 200
    created = r_create.json()
    assert created["noi_dung"] == "Bai nhap 1"
    assert created["trang_thai"] == "cho_duyet"

    # QL AI generate
    r_ai = client.post("/api/v1/page/drafts/ai-generate", json={"topic": "Ca phe trung", "tone": "than thien"}, headers=ql)
    assert r_ai.status_code == 200
    ai_draft = r_ai.json()
    assert len(ai_draft["noi_dung"]) > 10
    assert ai_draft["trang_thai"] == "cho_duyet"

    # QL xem danh sách drafts
    r_list = client.get("/api/v1/page/drafts", headers=ql)
    assert r_list.status_code == 200
    items = r_list.json()["items"]
    assert len(items) >= 2

    # QL duyệt draft
    r_decide = client.post(f"/api/v1/page/drafts/{created['id']}", json={"quyet_dinh": "duyet"}, headers=ql)
    assert r_decide.status_code == 200
    assert r_decide.json()["trang_thai"] in {"da_dang_mock", "da_dang"}

