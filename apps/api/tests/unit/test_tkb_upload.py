# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""TKB upload → confirm → store."""

from __future__ import annotations

from ca_api.interfaces.http.main import app
from ca_api.persist import kv_get
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def test_tkb_upload_fixture_and_confirm() -> None:
    nv = headers(client, "minh")
    r = client.post(
        "/api/v1/tkb/upload",
        data={"fixture_id": "tkb_01"},
        headers=nv,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rows"] or body["spans"]
    assert body["upload_id"].startswith("fixture:")

    khoang = body.get("rows") or [
        {"thu": s["day"], "start": s["start"], "end": s["end"]} for s in body.get("spans", [])
    ]
    conf = client.post(
        "/api/v1/tkb/confirm",
        json={
            "tuan_iso": "2026-W39",
            "khoang_ban": khoang,
            "source_id": body.get("source_id", "tkb_01"),
        },
        headers=nv,
    )
    assert conf.status_code == 200, conf.text
    assert conf.json()["n"] >= 1
    assert conf.json()["tuan_iso"] == "2026-W39"

    mine = client.get("/api/v1/tkb/mine?tuan_iso=2026-W39", headers=nv)
    assert mine.status_code == 200
    assert mine.json()["item"]["khoang_ban"]
    assert mine.json()["item"]["tuan_iso"] == "2026-W39"

    stored = kv_get("tkb_nv_by_week", {})
    assert mine.json()["nv_id"] in stored["2026-W39"]


def test_tkb_confirm_keeps_multiple_weeks_independent() -> None:
    nv = headers(client, "minh")
    w39 = [{"thu": "T2", "start": "07:00", "end": "12:00"}]
    w40 = [{"thu": "T4", "start": "12:00", "end": "17:00"}]

    for week, blocks in [("2026-W39", w39), ("2026-W40", w40)]:
        response = client.post(
            "/api/v1/tkb/confirm",
            json={"tuan_iso": week, "khoang_ban": blocks},
            headers=nv,
        )
        assert response.status_code == 200, response.text

    mine_w39 = client.get("/api/v1/tkb/mine?tuan_iso=2026-W39", headers=nv)
    mine_w40 = client.get("/api/v1/tkb/mine?tuan_iso=2026-W40", headers=nv)
    assert mine_w39.json()["item"]["khoang_ban"] == w39
    assert mine_w40.json()["item"]["khoang_ban"] == w40


def test_tkb_confirm_empty_rejected() -> None:
    nv = headers(client, "minh")
    r = client.post("/api/v1/tkb/confirm", json={"khoang_ban": []}, headers=nv)
    assert r.status_code == 400


def test_tkb_confirm_invalid_week_rejected() -> None:
    nv = headers(client, "minh")
    r = client.post(
        "/api/v1/tkb/confirm",
        json={
            "tuan_iso": "2026-W00",
            "khoang_ban": [{"thu": "T2", "start": "07:00", "end": "12:00"}],
        },
        headers=nv,
    )
    assert r.status_code == 422


def test_tkb_confirm_rejects_invalid_or_reversed_time_ranges() -> None:
    nv = headers(client, "minh")
    for block in (
        {"thu": "T2", "start": "25:00", "end": "26:00"},
        {"thu": "T2", "start": "12:00", "end": "07:00"},
        {"thu": "T2", "start": "08:99", "end": "12:00"},
    ):
        response = client.post(
            "/api/v1/tkb/confirm",
            json={"tuan_iso": "2026-W39", "khoang_ban": [block]},
            headers=nv,
        )
        assert response.status_code == 400, response.text


def test_tkb_upload_svg_rejected() -> None:
    nv = headers(client, "minh")
    svg_content = b"<svg xmlns='http://www.w3.org/2000/svg'><text>test</text></svg>"
    r = client.post(
        "/api/v1/tkb/upload",
        files={"file": ("test.svg", svg_content, "image/svg+xml")},
        headers=nv,
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "dinh_dang"

