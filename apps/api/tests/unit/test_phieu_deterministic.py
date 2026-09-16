from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ca_api.interfaces.http.main import app
from ca_api.persist import kv_set
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)
TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def _snapshot(rows: list[dict]) -> None:
    now = datetime.now(TZ)
    occurrences = []
    for index, row in enumerate(rows):
        occurrences.append(
            {
                "id": row["id"],
                "thu": "T2",
                "khung": row["id"].split("|")[1],
                "date": now.date().isoformat(),
                "bat_dau": row["start"].strftime("%H:%M"),
                "ket_thuc": row["end"].strftime("%H:%M"),
                "ca_ids": [f"w1_c{index + 1:02d}"],
                "nhan_vien": row["staff"],
                "phu_trach_nv_id": row["responsible"],
            }
        )
    kv_set(
        "lich_van_hanh_by_week",
        {
            f"{now.isocalendar().year}-W{now.isocalendar().week:02d}": {
                "store_id": "quan_01",
                "tuan_iso": f"{now.isocalendar().year}-W{now.isocalendar().week:02d}",
                "policy_version": 1,
                "mui_gio": "Asia/Ho_Chi_Minh",
                "cua_so": {
                    "ca_dau_ngay": {"mo_truoc_moc_phut": 60, "dong_sau_moc_phut": 30},
                    "giao_ca": {"mo_truoc_moc_phut": 30, "dong_sau_moc_phut": 15},
                    "ca_cuoi_ngay": {"mo_truoc_moc_phut": 30, "dong_sau_moc_phut": 60},
                },
                "occurrences": occurrences,
            }
        },
    )


def test_opening_is_presented_only_to_responsible_checked_in_employee() -> None:
    now = datetime.now(TZ).replace(second=0, microsecond=0)
    _snapshot(
        [
            {
                "id": "T2|sang",
                "start": now,
                "end": now + timedelta(hours=4),
                "staff": ["nv_03", "nv_01"],
                "responsible": "nv_03",
            }
        ]
    )
    minh = headers(client, "minh")
    lan = headers(client, "lan")

    assert client.get("/api/v1/phieu/current", headers=minh).json()["status"] == "needs_checkin"
    assert client.get("/api/v1/phieu/current", headers=lan).json()["status"] == "done"
    checked = client.post(
        "/api/v1/diem-danh",
        json={"occurrence_id": "T2|sang"},
        headers=minh,
    )
    assert checked.status_code == 200, checked.text
    resolved = client.post("/api/v1/phieu/resolve", headers=minh)
    assert resolved.status_code == 200
    assert resolved.json()["item"]["run"]["mau"] == "mo_quan"
    again = client.post("/api/v1/phieu/resolve", headers=minh)
    assert again.json()["item"]["run"]["id"] == resolved.json()["item"]["run"]["id"]


def test_handover_requires_sender_then_designated_receiver() -> None:
    now = datetime.now(TZ).replace(second=0, microsecond=0)
    _snapshot(
        [
            {
                "id": "T2|sang",
                "start": now - timedelta(hours=2),
                "end": now,
                "staff": ["nv_03"],
                "responsible": "nv_03",
            },
            {
                "id": "T2|chieu",
                "start": now,
                "end": now + timedelta(hours=2),
                "staff": ["nv_01"],
                "responsible": "nv_01",
            },
        ]
    )
    minh = headers(client, "minh")
    lan = headers(client, "lan")
    run = client.post("/api/v1/phieu/resolve", headers=minh).json()["item"]["run"]
    assert run["mau"] == "ban_giao_ca"
    for step in run["buocs"][:-1]:
        response = client.post(
            f"/api/v1/phieu/{run['id']}/buoc",
            json={"ma": step["ma"], "gia_tri": "đã bàn giao"},
            headers=minh,
        )
        assert response.status_code == 200, response.text

    denied = client.post(
        f"/api/v1/phieu/{run['id']}/buoc",
        json={"ma": "nguoi_nhan_xac_nhan", "gia_tri": "ok"},
        headers=minh,
    )
    assert denied.status_code == 403
    receiver_task = client.get("/api/v1/phieu/current", headers=lan).json()
    assert receiver_task["item"]["role"] == "receiver"
    confirmed = client.post(
        f"/api/v1/phieu/{run['id']}/buoc",
        json={"ma": "nguoi_nhan_xac_nhan", "gia_tri": "ok"},
        headers=lan,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["trang_thai"] == "hoan_thanh"


def test_closing_is_the_only_due_form_at_end_of_last_shift() -> None:
    now = datetime.now(TZ).replace(second=0, microsecond=0)
    _snapshot(
        [{
            "id": "T2|toi",
            "start": now - timedelta(hours=4),
            "end": now,
            "staff": ["nv_03"],
            "responsible": "nv_03",
        }]
    )
    minh = headers(client, "minh")
    current = client.get("/api/v1/phieu/current", headers=minh).json()
    assert current["status"] == "needs_checkin"
    assert current["item"]["mau"] == "dong_quan"
    client.post(
        "/api/v1/diem-danh",
        json={"occurrence_id": "T2|toi"},
        headers=minh,
    )
    resolved = client.post("/api/v1/phieu/resolve", headers=minh).json()
    assert resolved["item"]["run"]["mau"] == "dong_quan"
