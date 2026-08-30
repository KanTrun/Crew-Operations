"""Unit tests for Pure Trends API endpoints."""

from fastapi.testclient import TestClient
from ca_api.interfaces.http.main import app
from ca_api.persist import login, init_db

client = TestClient(app)


def test_trends_radar_endpoints():
    init_db()
    auth = login("lan", "nhipquan")
    headers = {"Authorization": f"Bearer {auth['token']}"}

    # 1. GET all trends
    res = client.get("/api/v1/trends/radar?region=all&category=all", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert len(data["trends"]) >= 5

    # 2. GET breaking VN trends
    res_vn = client.get("/api/v1/trends/radar?region=breaking_vn_24h&category=all", headers=headers)
    assert res_vn.status_code == 200
    data_vn = res_vn.json()
    assert data_vn["region_filter"] == "breaking_vn_24h"
    assert len(data_vn["trends"]) >= 3
