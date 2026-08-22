from __future__ import annotations

from fastapi.testclient import TestClient


def headers(client: TestClient, username: str = "minh") -> dict[str, str]:
    r = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "nhipquan"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}
