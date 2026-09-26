# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""HTTP tests cho quản lý Gmail — tài khoản, hộp thư, nhãn, bộ lọc, đồng bộ.

Không test nào gọi Google API thật: mọi nhánh cần OAuth đều assert lỗi 400
"chưa kết nối" hoặc assert không có 500 khi chưa cấu hình client.
"""

from __future__ import annotations

import pytest
from ca_api.interfaces.http.main import app
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)

_BASE = "/api/v1/gmail"


@pytest.fixture(autouse=True)
def _isolate_gmail_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cô lập env OAuth/encryption — test phải chạy được cả khi máy có .env thật."""
    monkeypatch.delenv("NHIPQUAN_GMAIL_CLIENT_ID", raising=False)
    monkeypatch.delenv("NHIPQUAN_GMAIL_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("NHIPQUAN_PAGE_MODE", "disconnected")


def _create_account(email: str = "quan.nhipquan@gmail.com", **extra: object) -> str:
    payload = {"email": email, "display_name": "Quán Nhịp", **extra}
    res = client.post(_BASE + "/accounts", json=payload, headers=headers(client, "lan"))
    assert res.status_code == 200, res.text
    return str(res.json()["id"])


# ── Xác thực ──────────────────────────────────────────────────────────────

def test_gmail_requires_token() -> None:
    assert client.get(_BASE + "/accounts").status_code == 401


def test_gmail_rejects_unknown_account() -> None:
    res = client.get(_BASE + "/accounts/gmail_khong_ton_tai", headers=headers(client, "lan"))
    assert res.status_code == 404


# ── Tài khoản ─────────────────────────────────────────────────────────────

def test_create_and_list_account() -> None:
    account_id = _create_account(is_primary=True)
    res = client.get(_BASE + "/accounts", headers=headers(client, "lan"))
    assert res.status_code == 200
    accounts = res.json()["accounts"]
    assert any(a["id"] == account_id for a in accounts)
    created = next(a for a in accounts if a["id"] == account_id)
    # Chưa OAuth ⇒ chưa có token.
    assert created["has_tokens"] is False
    assert created["is_primary"] is True


def test_duplicate_email_rejected() -> None:
    _create_account("trung.lap@gmail.com")
    res = client.post(
        _BASE + "/accounts",
        json={"email": "trung.lap@gmail.com"},
        headers=headers(client, "lan"),
    )
    assert res.status_code == 409


def test_invalid_email_rejected() -> None:
    res = client.post(
        _BASE + "/accounts",
        json={"email": "khong-phai-email"},
        headers=headers(client, "lan"),
    )
    assert res.status_code == 422


def test_update_account_display_name() -> None:
    account_id = _create_account("doi.ten@gmail.com")
    res = client.patch(
        f"{_BASE}/accounts/{account_id}",
        json={"display_name": "Tên mới"},
        headers=headers(client, "lan"),
    )
    assert res.status_code == 200
    assert res.json()["display_name"] == "Tên mới"


def test_delete_account_removes_it() -> None:
    account_id = _create_account("se.xoa@gmail.com")
    res = client.delete(f"{_BASE}/accounts/{account_id}", headers=headers(client, "lan"))
    assert res.status_code == 200

    res = client.get(f"{_BASE}/accounts/{account_id}", headers=headers(client, "lan"))
    assert res.status_code == 404


def test_employee_sees_only_own_accounts() -> None:
    """Nhân viên không thấy tài khoản của người khác trong cùng quán."""
    _create_account("cua.quan.ly@gmail.com")
    res = client.get(_BASE + "/accounts", headers=headers(client, "minh"))
    assert res.status_code == 200
    assert res.json()["accounts"] == []


# ── Hộp thư / nhãn / bộ lọc (chưa đồng bộ ⇒ rỗng) ─────────────────────────

def test_messages_empty_before_sync() -> None:
    account_id = _create_account("rong@gmail.com")
    res = client.get(f"{_BASE}/accounts/{account_id}/messages", headers=headers(client, "lan"))
    assert res.status_code == 200
    assert res.json()["messages"] == []


def test_labels_empty_before_sync() -> None:
    account_id = _create_account("nhan.rong@gmail.com")
    res = client.get(f"{_BASE}/accounts/{account_id}/labels", headers=headers(client, "lan"))
    assert res.status_code == 200
    assert res.json()["labels"] == []


def test_filters_empty_before_sync() -> None:
    account_id = _create_account("loc.rong@gmail.com")
    res = client.get(f"{_BASE}/accounts/{account_id}/filters", headers=headers(client, "lan"))
    assert res.status_code == 200
    assert res.json()["filters"] == []


def test_sync_state_empty_before_sync() -> None:
    account_id = _create_account("trang.thai.rong@gmail.com")
    res = client.get(f"{_BASE}/accounts/{account_id}/sync-state", headers=headers(client, "lan"))
    assert res.status_code == 200
    assert res.json() == {}


def test_message_actions_on_unknown_message_are_404() -> None:
    """Chưa đồng bộ nên không có email — đánh dấu đọc/gắn sao phải trả 404."""
    account_id = _create_account("thao.tac.email@gmail.com")
    for action in ("read", "star"):
        res = client.post(
            f"{_BASE}/accounts/{account_id}/messages/msg_khong_co/{action}",
            headers=headers(client, "lan"),
        )
        assert res.status_code == 404


def test_message_query_params_accepted() -> None:
    """Các tham số lọc của UI (?query=, ?is_read=, ?limit=) phải được chấp nhận."""
    account_id = _create_account("loc.hop.thu@gmail.com")
    res = client.get(
        f"{_BASE}/accounts/{account_id}/messages?limit=10&is_read=false&query=don+hang",
        headers=headers(client, "lan"),
    )
    assert res.status_code == 200
    assert res.json()["limit"] == 10


def test_message_limit_out_of_range_is_422() -> None:
    account_id = _create_account("gioi.han@gmail.com")
    res = client.get(
        f"{_BASE}/accounts/{account_id}/messages?limit=999",
        headers=headers(client, "lan"),
    )
    assert res.status_code == 422


def test_revoke_without_tokens_still_succeeds() -> None:
    """Thu hồi tài khoản chưa từng kết nối OAuth vẫn phải sạch (idempotent)."""
    account_id = _create_account("chua.tung.ket.noi@gmail.com")
    res = client.post(
        f"{_BASE}/oauth/revoke?account_id={account_id}",
        headers=headers(client, "lan"),
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True


# ── Nhánh cần OAuth: phải fail-closed, KHÔNG được 500 ─────────────────────

def test_create_label_without_oauth_is_400() -> None:
    account_id = _create_account("nhan.oauth@gmail.com")
    res = client.post(
        f"{_BASE}/accounts/{account_id}/labels",
        json={"name": "Đơn hàng"},
        headers=headers(client, "lan"),
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "tai_khoan_chua_ket_noi_oauth"


def test_delete_label_without_oauth_is_400() -> None:
    account_id = _create_account("xoa.nhan.oauth@gmail.com")
    res = client.delete(
        f"{_BASE}/accounts/{account_id}/labels/Label_1",
        headers=headers(client, "lan"),
    )
    assert res.status_code == 400


def test_create_filter_without_oauth_is_400() -> None:
    account_id = _create_account("loc.oauth@gmail.com")
    res = client.post(
        f"{_BASE}/accounts/{account_id}/filters",
        json={"criteria": {"from": "abc@example.com"}, "action": {"addLabelIds": ["Label_1"]}},
        headers=headers(client, "lan"),
    )
    assert res.status_code == 400


def test_send_without_oauth_is_400() -> None:
    account_id = _create_account("gui.oauth@gmail.com")
    res = client.post(
        f"{_BASE}/accounts/{account_id}/send",
        json={"to": ["a@example.com"], "subject": "Chào", "body_text": "Nội dung"},
        headers=headers(client, "lan"),
    )
    assert res.status_code == 400


def test_sync_without_oauth_is_400() -> None:
    account_id = _create_account("dong.bo.oauth@gmail.com")
    res = client.post(
        _BASE + "/sync",
        json={"account_id": account_id},
        headers=headers(client, "lan"),
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "dong_bo_that_bai"


def test_oauth_authorize_without_config_is_503() -> None:
    """Chưa cấu hình client id/secret ⇒ 503 kèm mã lý do, không phải 500."""
    res = client.get(_BASE + "/oauth/authorize", headers=headers(client, "lan"))
    assert res.status_code == 503
    assert res.json()["detail"] == "chua_cau_hinh_oauth_gmail"


# ── Phân quyền ────────────────────────────────────────────────────────────

def test_sync_requires_manager() -> None:
    res = client.post(_BASE + "/sync", json={}, headers=headers(client, "minh"))
    assert res.status_code == 403


def test_employee_cannot_touch_others_account() -> None:
    """404 (không phải 403) — không tiết lộ tài khoản của đồng nghiệp có tồn tại."""
    account_id = _create_account("cua.lan@gmail.com")
    res = client.patch(
        f"{_BASE}/accounts/{account_id}",
        json={"display_name": "Đổi trộm"},
        headers=headers(client, "minh"),
    )
    assert res.status_code == 404


def test_employee_cannot_delete_others_account() -> None:
    account_id = _create_account("xoa.trom@gmail.com")
    res = client.delete(f"{_BASE}/accounts/{account_id}", headers=headers(client, "minh"))
    assert res.status_code == 404


def test_employee_cannot_read_others_mailbox() -> None:
    """IDOR: nhân viên không được đọc hộp thư / nhãn / bộ lọc của tài khoản khác."""
    account_id = _create_account("hop.thu.rieng@gmail.com")
    employee = headers(client, "minh")

    checks = [
        ("GET", f"{_BASE}/accounts/{account_id}", None),
        ("GET", f"{_BASE}/accounts/{account_id}/messages", None),
        ("GET", f"{_BASE}/accounts/{account_id}/labels", None),
        ("GET", f"{_BASE}/accounts/{account_id}/filters", None),
        ("GET", f"{_BASE}/accounts/{account_id}/sync-state", None),
    ]
    for method, path, body in checks:
        res = client.request(method, path, json=body, headers=employee)
        assert res.status_code in (403, 404), (
            f"RÒ RỈ: nhân viên truy cập được {path} (status={res.status_code})"
        )


def test_employee_cannot_send_from_others_account() -> None:
    account_id = _create_account("gui.trom@gmail.com")
    res = client.post(
        f"{_BASE}/accounts/{account_id}/send",
        json={"to": ["a@example.com"], "subject": "Trộm", "body_text": "x"},
        headers=headers(client, "minh"),
    )
    assert res.status_code in (403, 404)


def test_employee_cannot_revoke_others_account() -> None:
    account_id = _create_account("thu.hoi.trom@gmail.com")
    res = client.post(
        f"{_BASE}/oauth/revoke?account_id={account_id}",
        headers=headers(client, "minh"),
    )
    assert res.status_code in (403, 404)


def test_employee_cannot_manage_others_labels_or_filters() -> None:
    account_id = _create_account("nhan.cua.nguoi.khac@gmail.com")
    employee = headers(client, "minh")

    res = client.post(
        f"{_BASE}/accounts/{account_id}/labels",
        json={"name": "Nhãn trộm"},
        headers=employee,
    )
    assert res.status_code in (403, 404)

    res = client.post(
        f"{_BASE}/accounts/{account_id}/filters",
        json={"criteria": {}, "action": {}},
        headers=employee,
    )
    assert res.status_code in (403, 404)
