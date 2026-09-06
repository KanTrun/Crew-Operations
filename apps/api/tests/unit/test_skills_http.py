from ca_api.interfaces.http.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_http_list_skills() -> None:
    resp = client.get("/skills")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 13
    ids = [s["skill_id"] for s in data]
    assert "solver-scheduling" in ids
    assert "smart-swap-recommender" in ids


def test_http_get_skill_detail() -> None:
    resp = client.get("/skills/solver-scheduling")
    assert resp.status_code == 200
    data = resp.json()
    assert data["skill_id"] == "solver-scheduling"
    assert "validate_solver_payload.py" in data["scripts"]
    assert len(data["content_sha256"]) == 64


def test_http_get_skill_detail_not_found() -> None:
    resp = client.get("/skills/non-existent-skill")
    assert resp.status_code == 404


def test_http_verify_skill_live() -> None:
    resp = client.post("/skills/solver-scheduling/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is True
    assert data["status"] == "VERIFIED"
    assert "validate_solver_payload.py" in data["script_results"]
    assert data["script_results"]["validate_solver_payload.py"]["passed"] is True
