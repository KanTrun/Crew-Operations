"""Unit & Integration tests for Meeting API endpoints."""

from __future__ import annotations

import base64

from ca_api.interfaces.http.main import app
from ca_api.persist import kv_get
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def test_meeting_transcribe_endpoint() -> None:
    ql = headers(client, "lan")
    fake_b64 = base64.b64encode(b"dummy_meeting_audio").decode("ascii")
    
    res = client.post(
        "/api/v1/meeting/transcribe",
        json={"audio_base64": fake_b64, "mime_type": "audio/webm"},
        headers=ql,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert len(body["segments"]) >= 1


def test_meeting_analyze_endpoint() -> None:
    ql = headers(client, "lan")
    res = client.post(
        "/api/v1/meeting/analyze",
        json={
            "text": "Quản lý: Tuấn thay ron máy pha số 2 bị rỉ nước trước 16h. My đổi định lượng trà đào sang 20ml.",
            "meeting_type": "giao_ca",
            "audio_source": "google_meet_tab",
        },
        headers=ql,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["loai_hop"] == "giao_ca"
    assert len(body["action_items"]) >= 1
    assert body["trang_thai"] == "cho_duyet"


def test_meeting_apply_and_opsengine_integration() -> None:
    ql = headers(client, "lan")
    
    # 1. First analyze meeting
    analyze_res = client.post(
        "/api/v1/meeting/analyze",
        json={
            "text": "Quản lý: Tuấn thay ron máy pha số 2 bị rỉ nước trước 16h.",
            "meeting_type": "giao_ca",
            "audio_source": "google_meet_tab",
        },
        headers=ql,
    ).json()

    # 2. Apply the approved meeting
    apply_res = client.post(
        "/api/v1/meeting/apply",
        json=analyze_res,
        headers=ql,
    )
    assert apply_res.status_code == 200, apply_res.text
    apply_body = apply_res.json()
    assert apply_body["ok"] is True
    assert apply_body["tasks_created"] >= 1

    # 3. Verify tasks are now in opsengine treo
    treo_items = kv_get("treo", [])
    assert any("Tuấn" in str(item) for item in treo_items)

    # 4. Verify meeting is listed in meetings history
    list_res = client.get("/api/v1/meetings", headers=ql)
    assert list_res.status_code == 200
    meetings = list_res.json()["items"]
    assert len(meetings) >= 1
    assert meetings[0]["id"] == analyze_res["id"]
