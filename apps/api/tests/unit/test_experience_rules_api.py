"""Rule learning API tests (Phase 04)."""

from __future__ import annotations

import pytest
from ca_api.interfaces.http.experience_rules import clear_rule_state
from ca_api.interfaces.http.main import app
from ca_api.persist import init_db
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    init_db()
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    clear_rule_state()


def _discover_and_get_candidate() -> str:
    d = client.post("/api/v1/experience/rules/discover", headers=headers(client, "lan"))
    assert d.status_code == 200, d.text
    c = client.get("/api/v1/experience/rules/candidates", headers=headers(client, "lan"))
    cands = c.json()["candidates"]
    assert cands, "phải có candidate từ fixture 3 tín hiệu"
    return cands[0]["candidate_id"]


def test_discover_requires_manager() -> None:
    r = client.post("/api/v1/experience/rules/discover", headers=headers(client, "minh"))
    assert r.status_code == 403


def test_discover_finds_candidate() -> None:
    r = client.post("/api/v1/experience/rules/discover", headers=headers(client, "lan"))
    assert r.status_code == 200, r.text
    assert r.json()["count"] >= 1
    assert r.json()["sources"] == "fixture_replay"


def test_candidates_list_after_discover() -> None:
    _discover_and_get_candidate()
    r = client.get("/api/v1/experience/rules/candidates", headers=headers(client, "lan"))
    assert r.status_code == 200
    assert len(r.json()["candidates"]) >= 1


def test_evidence_timeline() -> None:
    cid = _discover_and_get_candidate()
    r = client.get(f"/api/v1/experience/rules/{cid}/evidence", headers=headers(client, "lan"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["repeated_decisions"] >= 3
    assert body["actors"]


def test_evidence_not_found() -> None:
    r = client.get("/api/v1/experience/rules/khong_co/evidence", headers=headers(client, "lan"))
    assert r.status_code == 404


def test_shadow_test_reproducible() -> None:
    cid = _discover_and_get_candidate()
    a = client.post(f"/api/v1/experience/rules/{cid}/shadow-test", headers=headers(client, "lan"))
    b = client.post(f"/api/v1/experience/rules/{cid}/shadow-test", headers=headers(client, "lan"))
    assert a.status_code == 200, a.text
    assert a.json()["shadow"] == b.json()["shadow"]


def test_confirm_requires_shadow_first() -> None:
    cid = _discover_and_get_candidate()
    r = client.post(f"/api/v1/experience/rules/{cid}/confirm", headers=headers(client, "lan"))
    assert r.status_code == 409  # chưa shadow


def test_confirm_after_shadow() -> None:
    cid = _discover_and_get_candidate()
    client.post(f"/api/v1/experience/rules/{cid}/shadow-test", headers=headers(client, "lan"))
    r = client.post(f"/api/v1/experience/rules/{cid}/confirm", headers=headers(client, "lan"))
    assert r.status_code == 200, r.text
    assert r.json()["not_auto_activated"] is True


def test_confirmed_rule_is_persisted_to_store() -> None:
    """Xác nhận phải ghi luật vào kho của quán, không chỉ trả về rồi quên.

    Trước đây `luat` chỉ sống trong biến cục bộ: xác nhận xong luật biến mất,
    nên `revoke` vĩnh viễn 409 và trạng thái `confirmed` trên UI là lời hứa suông.
    """
    from ca_playbook.vong_doi import list_luat

    cid = _discover_and_get_candidate()
    client.post(f"/api/v1/experience/rules/{cid}/shadow-test", headers=headers(client, "lan"))
    confirmed = client.post(
        f"/api/v1/experience/rules/{cid}/confirm", headers=headers(client, "lan")
    )
    assert confirmed.status_code == 200, confirmed.text
    playbook_id = confirmed.json()["playbook_id"]
    assert playbook_id

    ids = {row.get("id") for row in list_luat()}
    assert playbook_id in ids, "luật đã xác nhận phải nằm trong kho luật của quán"


def test_confirmed_rule_can_be_revoked() -> None:
    """Thu hồi phải chạy được sau khi xác nhận — trước đây luôn 409.

    Vòng đời một chiều (ban hành được, không rút lại được) nghĩa là quán mất
    quyền sửa luật của chính mình.
    """
    from ca_playbook.vong_doi import list_luat

    cid = _discover_and_get_candidate()
    client.post(f"/api/v1/experience/rules/{cid}/shadow-test", headers=headers(client, "lan"))
    confirmed = client.post(
        f"/api/v1/experience/rules/{cid}/confirm", headers=headers(client, "lan")
    )
    playbook_id = confirmed.json()["playbook_id"]

    revoked = client.post(
        f"/api/v1/experience/rules/{cid}/revoke", headers=headers(client, "lan")
    )
    assert revoked.status_code == 200, revoked.text
    body = revoked.json()
    assert body["status"] == "revoked"
    assert body["playbook_revoked"] is True
    assert body["reason_required"] is True

    row = next(r for r in list_luat() if r.get("id") == playbook_id)
    assert row["trang_thai"] == "da_go"
    # Gỡ luật không xoá vết — tham số lõi phải bị rút khỏi lưu thông.
    assert "tham_so_loi" not in row


def test_revoke_before_confirm_is_rejected() -> None:
    """Thu hồi một luật chưa từng ban hành là thao tác vô nghĩa — phải nói rõ."""
    cid = _discover_and_get_candidate()
    r = client.post(f"/api/v1/experience/rules/{cid}/revoke", headers=headers(client, "lan"))
    assert r.status_code == 409
    assert r.json()["detail"] == "chua_phai_luat_da_ban_hanh"


def test_revoke_requires_manager() -> None:
    cid = _discover_and_get_candidate()
    client.post(f"/api/v1/experience/rules/{cid}/shadow-test", headers=headers(client, "lan"))
    client.post(f"/api/v1/experience/rules/{cid}/confirm", headers=headers(client, "lan"))
    r = client.post(f"/api/v1/experience/rules/{cid}/revoke", headers=headers(client, "minh"))
    assert r.status_code == 403


def test_reject_candidate() -> None:
    cid = _discover_and_get_candidate()
    r = client.post(f"/api/v1/experience/rules/{cid}/reject", headers=headers(client, "lan"))
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_employee_cannot_activate() -> None:
    cid = _discover_and_get_candidate()
    r = client.post(f"/api/v1/experience/rules/{cid}/confirm", headers=headers(client, "minh"))
    assert r.status_code == 403