"""Integration tests for Channels Self-Improving CSKH API:

1. Thread Approve Feedback Learning Loop (Golden Memory)
2. Nightly CSKH Reflection & Playbook Rule Application
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from ca_api.interfaces.http.main import app
from ca_api.persist import kv_get, login

client = TestClient(app)


def _login_manager() -> str:
    res = login("lan", "nhipquan")
    return res["token"]


import pytest


def test_page_thread_approve_feedback_learning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NHIPQUAN_PAGE_MODE", "disconnected")
    monkeypatch.delenv("NHIPQUAN_FB_PAGE_TOKEN", raising=False)
    token = _login_manager()

    from ca_api.persist import kv_set

    # Seed test thread in page_quan
    kv_set(
        "page_quan",
        {
            "threads": [
                {
                    "id": "th_test_01",
                    "sender_name": "Anh Tuấn",
                    "psid": "psid_test_01",
                    "intent": "hoi_gio_dia_chi",
                    "suggested_reply": "Dạ quán mở cửa 7h đến 22h ạ.",
                    "pending_approval": True,
                    "messages": [
                        {"from_customer": True, "text": "Quán có chỗ đậu xe ô tô không bạn?"}
                    ],
                    "replies": [],
                }
            ],
            "drafts": [],
            "mode": "mock",
        },
    )

    # 1. Fetch current threads
    res = client.get("/api/v1/page/threads", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) > 0
    th = items[0]
    th_id = th["id"]

    # 2. Manager edits reply before approving
    edited_reply = (
        "Dạ em chào anh Tuấn ạ! Quán thành thật xin lỗi vì trải nghiệm chưa trọn vẹn này. "
        "Anh cho em xin số điện thoại để Quản lý gọi lại hỗ trợ ngay nhé ạ!"
    )
    approve_res = client.post(
        f"/api/v1/page/threads/{th_id}/approve",
        json={"final_reply": edited_reply},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["ok"] is True

    # 3. Verify Golden CSKH Memory recorded the learning sample
    goldens = kv_get("cskh_golden_memory:quan_01", [])
    assert len(goldens) > 0
    latest = goldens[0]
    assert latest["manager_reply"] == edited_reply


def test_page_audit_reflection_and_apply_proposal() -> None:
    token = _login_manager()

    # 1. Trigger Nightly Reflection
    res = client.post(
        "/api/v1/page/audit/reflection",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    report = res.json()["report"]
    assert "csat_score" in report
    assert "hear_compliance_rate" in report
    assert "learning_recommendations" in report
    assert isinstance(report["playbook_rule_proposals"], list)

    # 2. Get latest reflection
    latest_res = client.get(
        "/api/v1/page/audit/reflection/latest",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert latest_res.status_code == 200
    assert latest_res.json()["report"]["csat_score"] == report["csat_score"]

    # 3. Apply a rule proposal to Playbook
    apply_res = client.post(
        "/api/v1/page/audit/reflection/apply-proposal",
        json={
            "proposal_id": "prop_bai_do_xe_test",
            "title": "Bổ sung quy định: Chỗ đậu xe ô tô",
            "suggested_rule": "Chỉ dẫn khách sang bãi đỗ số 12 đường ABC cách 50m.",
            "topic": "Chỗ đậu xe",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert apply_res.status_code == 200
    assert "thành công" in apply_res.json()["message"]

    # 4. Verify rule stored in playbook_rules
    rules = kv_get("playbook_rules:quan_01", [])
    assert any(r["id"] == "prop_bai_do_xe_test" for r in rules)
