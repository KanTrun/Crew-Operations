"""Integration tests for Smart Shift Swap API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ca_api.interfaces.http.main import app
from ca_api.persist import kv_get, kv_set, login

client = TestClient(app)


def _login_manager() -> str:
    res = login("lan", "nhipquan")
    return res["token"]


def test_inbox_list_enriches_swap_candidates_and_emergency() -> None:
    token = _login_manager()

    kv_set(
        "inbox_rang_buoc",
        [
            {
                "id": "item_swap_test_01",
                "tom_tat": "Tuấn xin đổi ca sáng T5 nhưng chưa có người",
                "trang_thai": "cho_duyet",
                "agent": "ag_msg",
                "y_dinh": "doi_ca",
                "nv_id": "nv_01",
                "doi_tac_khong_ro": True,
                "rang_buoc": {
                    "thu": "T5",
                    "start": "07:00",
                    "end": "12:00",
                    "vi_tri": "pha_che",
                },
            },
            {
                "id": "item_leave_urgent_02",
                "tom_tat": "Hùng sốt xuất huyết xin nghỉ khẩn cấp",
                "trang_thai": "cho_duyet",
                "agent": "ag_msg",
                "y_dinh": "xin_nghi",
                "nv_id": "nv_02",
                "rang_buoc": {
                    "thu": "T6",
                    "khan_cap": True,
                },
            },
        ],
    )

    res = client.get(
        "/api/v1/inbox/rang-buoc",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    items = res.json()["items"]

    # 1. Kiểm tra cờ khẩn cấp
    urgent = next(it for it in items if it["id"] == "item_leave_urgent_02")
    assert urgent["khan_cap"] is True

    # 2. Kiểm tra danh sách ứng viên tự động được gợi ý
    swap_item = next(it for it in items if it["id"] == "item_swap_test_01")
    assert "goi_y_doi_tac" in swap_item
    cands = swap_item["goi_y_doi_tac"]
    assert len(cands) > 0
    assert "score" in cands[0]
    assert cands[0]["is_qualified"] is True


def test_inbox_candidates_and_smart_approve() -> None:
    token = _login_manager()

    kv_set(
        "inbox_rang_buoc",
        [
            {
                "id": "item_swap_test_01",
                "tom_tat": "Tuấn xin đổi ca sáng T5 nhưng chưa có người",
                "trang_thai": "cho_duyet",
                "agent": "ag_msg",
                "y_dinh": "doi_ca",
                "nv_id": "nv_01",
                "doi_tac_khong_ro": True,
                "rang_buoc": {
                    "thu": "T5",
                    "start": "07:00",
                    "end": "12:00",
                    "vi_tri": "pha_che",
                },
            }
        ],
    )

    # 1. Test GET /api/v1/inbox/candidates/{item_id}
    res = client.get(
        "/api/v1/inbox/candidates/item_swap_test_01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["item_id"] == "item_swap_test_01"
    candidates = data["candidates"]
    assert len(candidates) > 0

    # 2. Test 1-Click Smart Approve POST /api/v1/inbox/rang-buoc/{item_id}/smart-approve
    approve_res = client.post(
        "/api/v1/inbox/rang-buoc/item_swap_test_01/smart-approve",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert approve_res.status_code == 200
    approved = approve_res.json()
    assert approved["smart_matched"] is True
    assert approved["trang_thai"] == "duyet"
    assert approved["selected_candidate"] is not None

    # 3. Kiểm tra phiếu swap đã được tạo trong kv("swap")
    swaps = kv_get("swap", [])
    assert any(s.get("tu_inbox") == "item_swap_test_01" for s in swaps)
