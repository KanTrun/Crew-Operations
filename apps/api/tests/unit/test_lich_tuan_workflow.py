# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
from __future__ import annotations

from ca_api.interfaces.http.main import app
from ca_api.persist import kv_set
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def test_week_assignments_and_pins_are_isolated() -> None:
    kv_set(
        "lich_tuan_results_by_week",
        {
            "2026-W40": {
                "tuan_iso": "2026-W40",
                "ok": True,
                "status": "OPTIMAL",
                "phan_cong": {"w1_c01": ["nv_01"]},
                "kiem_tra": {"coverage": {"passed": True, "filled": 21, "total": 21}},
            },
            "2026-W41": {
                "tuan_iso": "2026-W41",
                "ok": True,
                "status": "OPTIMAL",
                "phan_cong": {"w1_c01": ["nv_02"]},
            },
        },
    )
    kv_set("pins_by_week", {"2026-W40": {"w1_c01|nv_01": True}})

    auth = headers(client, "lan")
    week_40 = client.get("/api/v1/lich-tuan?tuan=2026-W40", headers=auth).json()
    week_41 = client.get("/api/v1/lich-tuan?tuan=2026-W41", headers=auth).json()

    assert week_40["phan_cong"]["w1_c01"] == ["nv_01"]
    assert week_40["pins"] == [{"ca_id": "w1_c01", "nv_id": "nv_01"}]
    assert week_40["kiem_tra"]["coverage"]["filled"] == 21
    assert week_41["phan_cong"]["w1_c01"] == ["nv_02"]
    assert week_41["pins"] == []


def test_manager_can_export_xlsx_and_pdf_for_selected_week() -> None:
    week = "2026-W42"
    kv_set("phan_cong_by_week", {week: {"w1_c01": ["nv_01"]}})
    auth = headers(client, "lan")

    xlsx = client.get(f"/api/v1/lich/xlsx?tuan={week}", headers=auth)
    pdf = client.get(f"/api/v1/lich/pdf?tuan={week}", headers=auth)

    assert xlsx.status_code == 200
    assert xlsx.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert xlsx.content.startswith(b"PK")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")


def test_employee_export_is_blocked_before_publish() -> None:
    week = "2026-W43"
    kv_set(
        "lich_tuan_lifecycle_by_week",
        {week: {"tuan_iso": week, "trang_thai": "cho_duyet"}},
    )
    response = client.get(f"/api/v1/lich/ics?tuan={week}", headers=headers(client, "minh"))
    assert response.status_code == 409
    assert response.json()["detail"] == "lich_chua_cong_bo"
