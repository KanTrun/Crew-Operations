from __future__ import annotations

from ca_api.ai_learning.repository import AILearningRepository
from ca_api.interfaces.http.mail import execute_supervised_mail
from ca_api.interfaces.http.main import app
from fastapi.testclient import TestClient

from unit.auth_util import headers


client = TestClient(app)


def _set_minh_email() -> None:
    response = client.patch(
        "/api/v1/me/profile/email",
        json={"email": "minh@example.com"},
        headers=headers(client, "minh"),
    )
    assert response.status_code == 200


def test_quality_gate_blocks_before_mail_transport(monkeypatch) -> None:
    _set_minh_email()
    monkeypatch.setattr("ca_api.interfaces.http.mail.send_mail", lambda **_: (_ for _ in ()).throw(AssertionError("must not send")))
    response = client.post(
        "/api/v1/mail/send",
        json={"to_nv_ids": ["nv_03"], "subject": "[Nhịp Quán] Test", "body": "Thân gửi Minh,\napi_key=secret\nTrân trọng"},
        headers=headers(client, "lan"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reason"] == "quality_gate"
    assert body["quality_gate"]["action"] == "block"
    assert "internal_data_exposure" in body["quality_gate"]["hard_fail_flags"]


def test_sent_mail_persists_generation_feedback_and_exact_edit_diff(monkeypatch) -> None:
    _set_minh_email()
    class Result:
        ok = True
        mode = "replay"
        sent = [{"email": "minh@example.com"}]
        failed: list[dict[str, str]] = []
        reason = ""

    monkeypatch.setattr("ca_api.interfaces.http.mail.send_mail", lambda **_: Result())
    response = client.post(
        "/api/v1/mail/send",
        json={
            "to_nv_ids": ["nv_03"],
            "original_subject": "[Nhịp Quán] Bản nháp", "original_body": "Nội dung ban đầu",
            "subject": "[Nhịp Quán] Lịch ca", "body": "Thân gửi Minh,\n\nCa sáng 07:00.\n\nTrân trọng,\nBan Quản Lý Nhịp Quán",
        },
        headers=headers(client, "lan"),
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    repository = AILearningRepository()
    generations = repository.list("generation", store_id="quan_01")
    evaluations = repository.list("evaluation", store_id="quan_01")
    feedback = repository.list("feedback", store_id="quan_01")
    assert any(item["draft"]["subject"] == "[Nhịp Quán] Lịch ca" for item in generations)
    assert any(
        item["threshold_version"] == "gmail-v1" and item["aggregate_score"] == 1.0 and item["passed"]
        for item in evaluations
    )
    manager_edit = next(item for item in feedback if item["type"] == "manager_edit" and item["final"]["subject"] == "[Nhịp Quán] Lịch ca")
    assert manager_edit["edited_fields"] == ["subject", "body"]
    assert manager_edit["materially_edited"] is True
    assert any(item["type"] == "send_success" for item in feedback)


def test_mail_adapter_replays_same_idempotency_key_without_resending(monkeypatch) -> None:
    calls = 0

    class Result:
        ok = True
        mode = "smtp"
        sent = [{"email": "minh@example.com", "status": "sent"}]
        failed: list[dict[str, str]] = []
        reason = ""

    def send_once(**_: object) -> Result:
        nonlocal calls
        calls += 1
        return Result()

    monkeypatch.setattr("ca_api.interfaces.http.mail.send_mail", send_once)
    kwargs = {
        "store_id": "quan_01", "actor_user_id": "nv_02", "actor_role": "chu_quan",
        "to_emails": ["minh@example.com"], "subject": "[Nhịp Quán] Lịch ca",
        "body": "Thân gửi Minh,\n\nCa sáng 07:00 ngày mai.\n\nTrân trọng,\nBan Quản Lý Nhịp Quán",
        "idempotency_key": "mail-key-1",
    }

    first = execute_supervised_mail(**kwargs)
    second = execute_supervised_mail(**kwargs)

    assert first["ok"] is True
    assert second == first
    assert calls == 1


def test_mail_adapter_marks_transport_exception_delivery_unknown_and_does_not_retry(monkeypatch) -> None:
    calls = 0

    def fail_transport(**_: object) -> object:
        nonlocal calls
        calls += 1
        raise TimeoutError("smtp timeout")

    monkeypatch.setattr("ca_api.interfaces.http.mail.send_mail", fail_transport)
    kwargs = {
        "store_id": "quan_01", "actor_user_id": "nv_02", "actor_role": "chu_quan",
        "to_emails": ["minh@example.com"], "subject": "[Nhịp Quán] Lịch ca",
        "body": "Thân gửi Minh,\n\nCa sáng 07:00 ngày mai.\n\nTrân trọng,\nBan Quản Lý Nhịp Quán",
        "idempotency_key": "mail-unknown-1",
    }

    first = execute_supervised_mail(**kwargs)
    second = execute_supervised_mail(**kwargs)

    assert first["ok"] is False
    assert first["reason"] == "delivery_unknown"
    assert second == first
    assert calls == 1