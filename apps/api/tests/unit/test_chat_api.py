"""Enterprise unit tests for employee real-time chat endpoints, security, and WebSocket."""

from __future__ import annotations

import io
import json
import pytest
from fastapi.testclient import TestClient

from ca_api.interfaces.http.main import app
from ca_api.persist import (
    chat_conversation_get,
    chat_messages_list,
    login,
    reset_init_flag,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_lan(client: TestClient) -> dict[str, str]:
    res = client.post("/api/v1/auth/login", json={"username": "lan", "password": "nhipquan"})
    assert res.status_code == 200
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}", "token": token}


@pytest.fixture
def auth_minh(client: TestClient) -> dict[str, str]:
    res = client.post("/api/v1/auth/login", json={"username": "minh", "password": "nhipquan"})
    assert res.status_code == 200
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}", "token": token}


def test_seed_and_list_conversations(client: TestClient, auth_lan: dict[str, str]) -> None:
    headers = {"Authorization": auth_lan["Authorization"]}
    res = client.get("/api/v1/chat/conversations", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    # Đã có phòng mặc định "☕ NHỊP QUÁN · Hội Quán Chung"
    names = [c["display_name"] for c in data["items"]]
    assert any("Hội Quán Chung" in n for n in names)


def test_direct_chat_messaging_edit_and_delete(
    client: TestClient, auth_lan: dict[str, str], auth_minh: dict[str, str]
) -> None:
    headers_lan = {"Authorization": auth_lan["Authorization"]}
    headers_minh = {"Authorization": auth_minh["Authorization"]}

    # Lan tạo chat 1-1 với Minh (nv_03)
    res = client.post(
        "/api/v1/chat/conversations",
        json={"conv_type": "direct", "target_nv_id": "nv_03"},
        headers=headers_lan,
    )
    assert res.status_code == 200
    conv = res.json()
    conv_id = conv["id"]
    assert conv["type"] == "direct"

    # Lan gửi tin nhắn cho Minh
    res_msg = client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"content": "Minh ơi, hôm nay ca sáng đông không em?"},
        headers=headers_lan,
    )
    assert res_msg.status_code == 200
    msg_data = res_msg.json()
    assert msg_data["content"] == "Minh ơi, hôm nay ca sáng đông không em?"
    msg_id = msg_data["id"]

    # Lan chỉnh sửa tin nhắn (Edit trong vòng 15p)
    res_edit = client.patch(
        f"/api/v1/chat/messages/{msg_id}",
        json={"content": "Minh ơi, hôm nay ca sáng có đông khách không em?"},
        headers=headers_lan,
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["content"] == "Minh ơi, hôm nay ca sáng có đông khách không em?"
    assert res_edit.json()["edited_at"] is not None

    # Minh thả tim tin nhắn
    res_react = client.post(
        f"/api/v1/chat/messages/{msg_id}/reactions",
        json={"emoji": "❤️"},
        headers=headers_minh,
    )
    assert res_react.status_code == 200
    assert "❤️" in res_react.json()["reactions"]

    # Minh đánh dấu đã đọc (read receipt)
    res_read = client.post(
        f"/api/v1/chat/conversations/{conv_id}/read?message_id={msg_id}",
        headers=headers_minh,
    )
    assert res_read.status_code == 200

    # Lan thu hồi tin nhắn
    res_del = client.delete(f"/api/v1/chat/messages/{msg_id}", headers=headers_lan)
    assert res_del.status_code == 200
    assert res_del.json()["is_unsent"] is True
    assert "thu hồi" in res_del.json()["content"]


def test_chat_sanitize_stored_xss(client: TestClient, auth_lan: dict[str, str]) -> None:
    headers = {"Authorization": auth_lan["Authorization"]}
    res = client.get("/api/v1/chat/conversations", headers=headers)
    conv_id = res.json()["items"][0]["id"]

    # Gửi tin nhắn chứa script độc hại
    malicious = "<script>alert('hack')</script>Chào cả nhà!"
    res_msg = client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"content": malicious},
        headers=headers,
    )
    assert res_msg.status_code == 200
    content = res_msg.json()["content"]
    assert "<script>" not in content
    assert "alert('hack')" not in content
    assert "Chào cả nhà!" in content


def test_chat_upload_media_magic_bytes(client: TestClient, auth_lan: dict[str, str]) -> None:
    headers = {"Authorization": auth_lan["Authorization"]}

    # 1. File hợp lệ (PNG thật kèm magic bytes \x89PNG\r\n\x1a\n)
    valid_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"A" * 50
    res_ok = client.post(
        "/api/v1/chat/upload",
        files={"file": ("shot.png", io.BytesIO(valid_png), "image/png")},
        headers=headers,
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["url"].startswith("/api/v1/chat/uploads/")

    # 2. File giả mạo extension (đuôi .png nhưng nội dung script/exe)
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00fake executable content"
    res_bad = client.post(
        "/api/v1/chat/upload",
        files={"file": ("danger.png", io.BytesIO(fake_exe), "image/png")},
        headers=headers,
    )
    # Bị chặn bởi magic bytes validator
    assert res_bad.status_code == 415


def test_chat_websocket_first_message_auth(
    client: TestClient, auth_lan: dict[str, str], auth_minh: dict[str, str]
) -> None:
    token_lan = auth_lan["token"]
    token_minh = auth_minh["token"]

    res_conv = client.get("/api/v1/chat/conversations", headers={"Authorization": auth_lan["Authorization"]})
    conv_id = res_conv.json()["items"][0]["id"]

    # 1. Kết nối với token sai -> Bị đóng với mã 4001
    with client.websocket_connect("/ws/chat") as ws_bad:
        ws_bad.send_text(json.dumps({"event": "auth", "token": "wrong_token_123"}))
        with pytest.raises(Exception):
            ws_bad.receive_text()

    # 2. Kết nối chuẩn với First-Message Auth (2 client song song)
    # Lưu ý: TestClient chạy mỗi kết nối trong portal/event-loop riêng, nên
    # broadcast chéo portal bị anyio chặn — mỗi client chỉ nhận được broadcast
    # phát từ loop của chính nó (đúng hành vi single-instance).
    with client.websocket_connect("/ws/chat") as ws_minh:
        ws_minh.send_text(json.dumps({"event": "auth", "token": token_minh}))
        ack_minh = json.loads(ws_minh.receive_text())
        assert ack_minh["event"] == "auth:ack"
        assert ack_minh["data"]["nv_id"] == "nv_03"

        with client.websocket_connect("/ws/chat") as ws_lan:
            ws_lan.send_text(json.dumps({"event": "auth", "token": token_lan}))
            ack_lan = json.loads(ws_lan.receive_text())
            assert ack_lan["event"] == "auth:ack"

            # Lan gửi tin nhắn qua WS; broadcast quay lại kết nối của chính Lan
            ws_lan.send_text(
                json.dumps({
                    "event": "message:send",
                    "data": {"conversation_id": conv_id, "content": "Thông báo kiểm kê ca chiều!"},
                })
            )

            received = json.loads(ws_lan.receive_text())
            while received.get("event") != "message:new":
                received = json.loads(ws_lan.receive_text())

            assert received["event"] == "message:new"
            assert received["data"]["content"] == "Thông báo kiểm kê ca chiều!"
            assert received["data"]["sender_id"] == "nv_01"

    # 3. Tin nhắn được persist đúng
    msgs = chat_messages_list(conv_id)
    assert any(m["content"] == "Thông báo kiểm kê ca chiều!" for m in msgs)


def test_chat_manager_broadcasts_through_backend_and_suppresses_echo() -> None:
    """Broadcast phải đi qua PubSubBackend và không xử lý lại echo của chính mình."""
    import asyncio

    from ca_api.services.chat_ws import ChatConnectionManager, InMemoryPubSubBackend

    class FakeWs:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send_text(self, text: str) -> None:
            self.sent.append(text)

    async def scenario() -> tuple[list[dict[str, object]], list[str]]:
        backend = InMemoryPubSubBackend()
        manager = ChatConnectionManager(backend)
        fake_ws = FakeWs()
        await manager.connect("nv_01", fake_ws)  # type: ignore[arg-type]
        received: list[dict[str, object]] = []

        async def capture(payload: dict[str, object]) -> None:
            received.append(payload)

        await backend.subscribe("chat:broadcast", capture)
        await manager.broadcast_all({"event": "user:test", "data": {"nv_id": "nv_01"}})
        await asyncio.sleep(0)

        # Echo của chính instance phải bị bỏ qua (fake_ws không nhận)
        count_before = len(fake_ws.sent)
        await manager._on_remote_message({"event": "echo", "_origin": manager._origin})
        assert len(fake_ws.sent) == count_before

        # Broadcast từ instance khác phải được forward vào local socket
        await manager._on_remote_message({"event": "remote", "data": {"nv_id": "nv_02"}})
        return received, fake_ws.sent

    received, sent = asyncio.run(scenario())
    assert any(p.get("event") == "user:test" for p in received)
    assert any("remote" in msg for msg in sent)


def test_redis_backend_retries_without_silent_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redis rớt kết nối phải retry re-subscribe, không rơi về in-memory."""
    import asyncio
    import sys
    from unittest.mock import MagicMock

    from ca_api.services.chat_ws import RedisPubSubBackend

    backend = RedisPubSubBackend("redis://localhost:6399/0")
    attempts = 0

    class FakePubSub:
        async def subscribe(self, channel: str) -> None:
            nonlocal attempts
            attempts += 1
            raise ConnectionError("redis down")

        async def listen(self) -> object:
            await asyncio.sleep(3600)
            yield {}

    class FakeRedis:
        def pubsub(self) -> FakePubSub:
            return FakePubSub()

        async def aclose(self) -> None:
            pass

    mock_asyncio = MagicMock()
    mock_asyncio.from_url = lambda *a, **k: FakeRedis()
    mock_redis = MagicMock()
    mock_redis.asyncio = mock_asyncio
    monkeypatch.setitem(sys.modules, "redis", mock_redis)
    monkeypatch.setitem(sys.modules, "redis.asyncio", mock_asyncio)

    backend._RETRY_DELAY_S = 0.01

    async def scenario() -> int:
        await backend._ensure_connected()
        await asyncio.sleep(0.08)
        await backend.aclose()
        return attempts

    final_attempts = asyncio.run(scenario())
    assert final_attempts >= 2, "Redis backend phải retry re-subscribe liên tục"
    assert backend._redis is None  # aclose dọn sạch, không giữ kết nối chết
