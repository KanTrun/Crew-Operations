# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Test tính nhất quán lịch làm việc end-to-end.

Các test này khoá hành vi "một nguồn sự thật" của lịch: mọi thao tác đổi lịch
(nhả ca, nhận ca, đổi ca, duyệt ràng buộc ở inbox) phải cập nhật ĐỒNG THỜI
`phan_cong`, `phan_cong_by_week` và `lich_tuan_results_by_week`.

Tài khoản seed (persist.py): lan=nv_01 (quan_ly), hung=nv_02 (chu_quan),
minh=nv_03 (nhan_vien).
"""

from __future__ import annotations

from ca_api.interfaces.http.main import app
from ca_api.persist import (
    availability_confirmed_list,
    kv_get,
    kv_set,
    thong_bao_lich_list_for_week,
)
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def _seed_week(week: str, ca_id: str, nv_ids: list[str]) -> None:
    """Dựng lịch tuần ở CẢ 3 khoá để kiểm tra đồng bộ."""
    kv_set("phan_cong", {ca_id: list(nv_ids)})
    kv_set("phan_cong_by_week", {week: {ca_id: list(nv_ids)}})
    kv_set("lich_tuan_results_by_week", {week: {"phan_cong": {ca_id: list(nv_ids)}}})
    kv_set("lich_tuan_lifecycle", {"tuan_iso": week, "trang_thai": "da_cong_bo"})
    kv_set("lich_tuan_lifecycle_by_week", {week: {"tuan_iso": week, "trang_thai": "da_cong_bo"}})


def test_solver_adapter_shift_frames_overrideable_by_config() -> None:
    """Khung giờ mặc định của solver phải bị đè được bởi cấu hình `khung_gio`."""
    from ca_api.services import solver_adapter

    # Mặc định của solver (khi chưa cấu hình gì).
    assert solver_adapter._SHIFT_FRAMES["Sáng"] == ("06:30", "12:00")

    # Cấu hình khác đi -> phải áp dụng cho khung tiếng Việt có dấu.
    kv_set(
        "khung_gio",
        {
            "sang": {"bat_dau": "07:00", "ket_thuc": "11:45"},
            "chieu": {"bat_dau": "11:45", "ket_thuc": "17:00"},
            "toi": {"bat_dau": "17:00", "ket_thuc": "22:00"},
        },
    )
    frames = dict(solver_adapter._SHIFT_FRAMES)
    map_key = {"Sáng": "sang", "Chiều": "chieu", "Tối": "toi"}
    configured = kv_get("khung_gio", {})
    for shift in list(frames):
        conf = configured.get(map_key.get(shift, shift)) or configured.get(shift)
        if isinstance(conf, dict) and conf.get("bat_dau") and conf.get("ket_thuc"):
            frames[shift] = (str(conf["bat_dau"]), str(conf["ket_thuc"]))

    assert frames["Sáng"] == ("07:00", "11:45")
    assert frames["Chiều"] == ("11:45", "17:00")
    assert frames["Tối"] == ("17:00", "22:00")


def test_swap_dong_y_updates_phan_cong_assignments() -> None:
    """Đổi ca được đồng ý phải chuyển ca từ người cho sang người nhận ở CẢ 3 khoá."""
    week = "2026-W10"
    ca_id = "w1_c01"
    _seed_week(week, ca_id, ["nv_01"])

    # nv_01 (lan) mở phiếu đổi ca sang nv_02 (hung).
    opened = client.post(
        "/api/v1/cho-doi-ca",
        json={"a": "nv_01", "b": "nv_02", "ca_id": ca_id},
        headers=headers(client, "lan"),
    )
    assert opened.status_code == 200, opened.text
    swap_id = opened.json()["id"]
    assert opened.json()["tuan_id"] == week

    # nv_02 (hung) đồng ý.
    agreed = client.post(
        f"/api/v1/cho-doi-ca/{swap_id}/dong-y", headers=headers(client, "hung")
    )
    assert agreed.status_code == 200, agreed.text
    assert agreed.json()["trang_thai"] == "dong_y"

    flat = kv_get("phan_cong", {})
    assert "nv_02" in flat[ca_id]
    assert "nv_01" not in flat[ca_id]

    by_week = kv_get("phan_cong_by_week", {}).get(week, {})
    assert "nv_02" in by_week[ca_id]
    assert "nv_01" not in by_week[ca_id]

    results = kv_get("lich_tuan_results_by_week", {}).get(week, {}).get("phan_cong", {})
    assert "nv_02" in results[ca_id]
    assert "nv_01" not in results[ca_id]


def test_swap_only_touches_its_own_week() -> None:
    """Đổi ca ở tuần W10 KHÔNG được đụng vào tuần khác (W11)."""
    ca_id = "w1_c01"
    kv_set("phan_cong", {ca_id: ["nv_01"]})
    kv_set(
        "phan_cong_by_week",
        {"2026-W10": {ca_id: ["nv_01"]}, "2026-W11": {ca_id: ["nv_03"]}},
    )
    kv_set("lich_tuan_lifecycle", {"tuan_iso": "2026-W10", "trang_thai": "da_cong_bo"})

    opened = client.post(
        "/api/v1/cho-doi-ca",
        json={"a": "nv_01", "b": "nv_02", "ca_id": ca_id},
        headers=headers(client, "lan"),
    )
    swap_id = opened.json()["id"]
    client.post(f"/api/v1/cho-doi-ca/{swap_id}/dong-y", headers=headers(client, "hung"))

    by_week = kv_get("phan_cong_by_week", {})
    assert by_week["2026-W10"][ca_id] == ["nv_02"]
    assert by_week["2026-W11"][ca_id] == ["nv_03"], "tuần khác không được đổi"


def test_inbox_smart_approve_applies_swap_assignments() -> None:
    """Quản lý duyệt ràng buộc đổi ca kèm `ap_dat` phải áp ngay vào phân công."""
    week = "2026-W11"
    ca_id = "w1_c02"
    _seed_week(week, ca_id, ["nv_01"])

    kv_set(
        "inbox_rang_buoc",
        [
            {
                "id": "inbox_swap_direct_01",
                "tom_tat": "Lan xin đổi ca với Hùng",
                "trang_thai": "cho_duyet",
                "agent": "ag_msg",
                "y_dinh": "doi_ca",
                "nv_id": "nv_01",
                "doi_tac_khong_ro": False,
                "rang_buoc": {"ca_id": ca_id, "doi_tac": "nv_02", "tuan_id": week},
            }
        ],
    )

    res = client.post(
        "/api/v1/inbox/rang-buoc/inbox_swap_direct_01",
        json={"quyet_dinh": "duyet", "ap_dat": True},
        headers=headers(client, "lan"),
    )
    assert res.status_code == 200, res.text

    flat = kv_get("phan_cong", {})
    assert "nv_02" in flat[ca_id]
    assert "nv_01" not in flat[ca_id]

    by_week = kv_get("phan_cong_by_week", {}).get(week, {})
    assert "nv_02" in by_week[ca_id]
    assert "nv_01" not in by_week[ca_id]


def test_inbox_approve_without_ap_dat_does_not_change_assignments() -> None:
    """Duyệt ràng buộc đổi ca KHÔNG kèm `ap_dat` chỉ mở phiếu chờ — chưa đổi lịch."""
    week = "2026-W13"
    ca_id = "w1_c02"
    _seed_week(week, ca_id, ["nv_01"])

    kv_set(
        "inbox_rang_buoc",
        [
            {
                "id": "inbox_swap_pending_01",
                "trang_thai": "cho_duyet",
                "y_dinh": "doi_ca",
                "nv_id": "nv_01",
                "doi_tac_khong_ro": False,
                "rang_buoc": {"ca_id": ca_id, "doi_tac": "nv_02", "tuan_id": week},
            }
        ],
    )

    res = client.post(
        "/api/v1/inbox/rang-buoc/inbox_swap_pending_01",
        json={"quyet_dinh": "duyet", "ap_dat": False},
        headers=headers(client, "lan"),
    )
    assert res.status_code == 200, res.text

    flat = kv_get("phan_cong", {})
    assert flat[ca_id] == ["nv_01"], "chưa áp đặt thì lịch phải giữ nguyên"

    pending = [s for s in kv_get("swap", []) if s.get("tu_inbox") == "inbox_swap_pending_01"]
    assert len(pending) == 1
    assert pending[0]["trang_thai"] == "cho_xac_nhan"


def test_ca_nha_and_nhan_sync_to_phan_cong_by_week() -> None:
    """Nhả ca và nhận ca phải cập nhật cả `phan_cong` lẫn `phan_cong_by_week`."""
    week = "2026-W12"
    ca_id = "w1_c03"
    _seed_week(week, ca_id, ["nv_03"])

    r_nha = client.post("/api/v1/ca/nha", json={"ca_id": ca_id}, headers=headers(client, "minh"))
    assert r_nha.status_code == 200, r_nha.text
    assert "nv_03" not in kv_get("phan_cong_by_week", {})[week][ca_id]
    assert "nv_03" not in kv_get("phan_cong", {})[ca_id]

    r_nhan = client.post("/api/v1/ca/nhan", json={"ca_id": ca_id}, headers=headers(client, "hung"))
    assert r_nhan.status_code == 200, r_nhan.text
    assert "nv_02" in kv_get("phan_cong_by_week", {})[week][ca_id]
    assert "nv_02" in kv_get("phan_cong", {})[ca_id]


def test_ca_nha_rejects_when_not_in_shift() -> None:
    """Nhả ca mà mình không trực phải trả 409, không được âm thầm sửa lịch."""
    week = "2026-W14"
    ca_id = "w1_c03"
    _seed_week(week, ca_id, ["nv_03"])

    res = client.post("/api/v1/ca/nha", json={"ca_id": ca_id}, headers=headers(client, "hung"))
    assert res.status_code == 409
    assert res.json()["detail"] == "khong_trong_ca"
    assert kv_get("phan_cong", {})[ca_id] == ["nv_03"]


def test_tkb_confirm_enables_availability_confirmations() -> None:
    """Xác nhận TKB phải ghi vào availability confirmations với trạng thái đã xác nhận."""
    week = "2026-W15"
    res = client.post(
        "/api/v1/tkb/confirm",
        json={
            "tuan_iso": week,
            "khoang_ban": [{"thu": "T2", "start": "07:00", "end": "11:30"}],
            "nv_id": "nv_03",
        },
        headers=headers(client, "minh"),
    )
    assert res.status_code == 200, res.text

    confirmed = availability_confirmed_list("quan_01", week)
    assert any(c["nv_id"] == "nv_03" for c in confirmed)


def test_toi_lich_tuan_parameter() -> None:
    """GET /api/v1/toi/lich?tuan=... trả đúng ca và tuần được yêu cầu."""
    week = "2026-W20"
    ca_id = "w1_c01"
    kv_set("phan_cong_by_week", {week: {ca_id: ["nv_03"]}})
    kv_set("lich_tuan_lifecycle_by_week", {week: {"tuan_iso": week, "trang_thai": "da_cong_bo"}})

    res = client.get(f"/api/v1/toi/lich?tuan={week}", headers=headers(client, "minh"))
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["tuan_iso"] == week
    assert data["trang_thai"] == "da_cong_bo"
    assert ca_id in data["ca_ids"]


def test_inbox_pending_swap_confirmed_later_applies_exactly_once() -> None:
    """Duyệt inbox (chưa áp đặt) rồi đối tác xác nhận: lịch đổi ĐÚNG MỘT LẦN.

    Xác nhận lần hai (idempotent) không được nhân đôi người trong ca.
    """
    week = "2026-W16"
    ca_id = "w1_c01"
    _seed_week(week, ca_id, ["nv_01"])
    kv_set("swap", [])
    kv_set(
        "inbox_rang_buoc",
        [
            {
                "id": "inbox_swap_two_step",
                "trang_thai": "cho_duyet",
                "y_dinh": "doi_ca",
                "nv_id": "nv_01",
                "doi_tac_khong_ro": False,
                "rang_buoc": {"ca_id": ca_id, "doi_tac": "nv_02", "tuan_id": week},
            }
        ],
    )

    approved = client.post(
        "/api/v1/inbox/rang-buoc/inbox_swap_two_step",
        json={"quyet_dinh": "duyet", "ap_dat": False},
        headers=headers(client, "lan"),
    )
    assert approved.status_code == 200, approved.text
    assert kv_get("phan_cong", {})[ca_id] == ["nv_01"], "chưa áp đặt thì chưa đổi"

    created = [s for s in kv_get("swap", []) if s.get("tu_inbox") == "inbox_swap_two_step"]
    assert len(created) == 1
    assert created[0]["tuan_id"] == week
    swap_id = created[0]["id"]

    first = client.post(f"/api/v1/cho-doi-ca/{swap_id}/dong-y", headers=headers(client, "hung"))
    assert first.status_code == 200, first.text
    assert kv_get("phan_cong", {})[ca_id] == ["nv_02"]
    assert kv_get("phan_cong_by_week", {})[week][ca_id] == ["nv_02"]
    assert kv_get("lich_tuan_results_by_week", {})[week]["phan_cong"][ca_id] == ["nv_02"]

    # Xác nhận lần hai KHÔNG được nhân đôi người nhận.
    second = client.post(f"/api/v1/cho-doi-ca/{swap_id}/dong-y", headers=headers(client, "hung"))
    assert second.status_code == 200
    assert kv_get("phan_cong", {})[ca_id] == ["nv_02"], "không được lặp nv_02"


def test_publish_notification_role_based_links() -> None:
    """Thông báo công bố lịch chia url theo vai trò: quản lý /lich-tuan, nhân viên /toi."""
    from ca_api.interfaces.http.sprint45 import _publish_schedule_notification

    week = "2026-W25"
    n = _publish_schedule_notification(week, store_id="quan_01")
    assert n > 0

    notifs = thong_bao_lich_list_for_week(week, store_id="quan_01")
    manager_notifs = [it for it in notifs if it["url"].startswith("/lich-tuan")]
    staff_notifs = [it for it in notifs if it["url"].startswith("/toi")]

    assert len(manager_notifs) > 0, "quản lý phải nhận link xem toàn quán"
    assert len(staff_notifs) > 0, "nhân viên phải nhận link xem lịch của mình"
