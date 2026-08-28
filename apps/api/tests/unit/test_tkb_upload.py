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
        json={"khoang_ban": khoang, "source_id": body.get("source_id", "tkb_01")},
        headers=nv,
    )
    assert conf.status_code == 200, conf.text
    assert conf.json()["n"] >= 1

    mine = client.get("/api/v1/tkb/mine", headers=nv)
    assert mine.status_code == 200
    assert mine.json()["item"]["khoang_ban"]

    stored = kv_get("tkb_nv", {})
    assert mine.json()["nv_id"] in stored


def test_tkb_confirm_empty_rejected() -> None:
    nv = headers(client, "minh")
    r = client.post("/api/v1/tkb/confirm", json={"khoang_ban": []}, headers=nv)
    assert r.status_code == 400
