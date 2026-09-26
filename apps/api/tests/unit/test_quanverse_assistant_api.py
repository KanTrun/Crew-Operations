"""Test HTTP cho Trợ lý Quánverse — 2 route mới (plan quanverse-ai-rework).

Khoá đúng ranh giới: route phải đòi xác thực, chặn trang/câu hỏi không hợp lệ,
và (quan trọng nhất) — ở chế độ replay — trả câu trả lời TẤT ĐỊNH không chạm
mạng, với `grounded`/`citations` phản ánh ĐÚNG dữ liệu thật của quán.
"""

from __future__ import annotations

import pytest
from ca_api.interfaces.http.main import app
from ca_api.interfaces.http.quanverse import clear_quanverse_state
from ca_api.persist import init_db
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    init_db()
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    clear_quanverse_state()


# ── /brief/{page} ───────────────────────────────────────────────────────────


def test_brief_living_map_returns_deterministic_summary() -> None:
    r = client.get(
        "/api/v1/experience/quanverse/brief/living_map", headers=headers(client, "lan")
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["page"] == "living_map"
    assert body["headline"]
    assert body["metrics"], "brief phải có chỉ số thật từ snapshot"
    assert body["grounded_refs"], "brief phải dẫn được về bản ghi hệ thống"


def test_brief_every_page_is_supported() -> None:
    """Cả 5 trang phải trả brief — không trang nào 404 hay rỗng."""
    for page in ("living_map", "war_room", "shift_rescue", "rules", "spatial_memory"):
        r = client.get(
            f"/api/v1/experience/quanverse/brief/{page}", headers=headers(client, "lan")
        )
        assert r.status_code == 200, f"{page}: {r.text}"
        assert r.json()["headline"], f"{page} thiếu headline"


def test_spatial_memory_brief_reads_anchors_from_adapter() -> None:
    """Regression: neo KHÔNG nằm trong fixture `spatial-memory.json`.

    Bản đầu của `_payload_for_page` đọc `data["anchors"]` từ fixture đó — fixture
    chỉ có `memories`/`audit`/`tour_route` nên brief LUÔN báo "0 neo" dù quán có
    đủ neo. Bài này neo đúng nguồn: neo phải đến từ read adapter, giống
    `GET /api/v1/experience/map`.
    """
    r = client.get(
        "/api/v1/experience/quanverse/brief/spatial_memory", headers=headers(client, "lan")
    )
    assert r.status_code == 200, r.text
    body = r.json()
    anchors = next(m for m in body["metrics"] if m["key"] == "anchors")
    assert anchors["value"] and anchors["value"] > 0, "brief phải đọc được neo thật của quán"

    # Và phải khớp với nguồn chính thức.
    r_map = client.get("/api/v1/experience/map", headers=headers(client, "lan"))
    assert r_map.status_code == 200
    assert anchors["value"] == float(len(r_map.json()["anchors"]))


def test_brief_unknown_page_is_404() -> None:
    r = client.get(
        "/api/v1/experience/quanverse/brief/khong_ton_tai", headers=headers(client, "lan")
    )
    assert r.status_code == 404


def test_brief_requires_auth() -> None:
    r = client.get("/api/v1/experience/quanverse/brief/living_map")
    assert r.status_code in (401, 403)


def test_employee_gets_brief_but_not_manager_only_page_data() -> None:
    """Bản chiếu theo vai trò vẫn áp dụng: nhân viên không thấy dữ liệu quản lý."""
    r_manager = client.get(
        "/api/v1/experience/quanverse/brief/living_map", headers=headers(client, "lan")
    )
    r_staff = client.get(
        "/api/v1/experience/quanverse/brief/living_map", headers=headers(client, "minh")
    )
    assert r_manager.status_code == 200
    assert r_staff.status_code == 200
    # Nhân viên thấy ít sự kiện hơn quản lý (ranh giới sự kiện đã có test riêng),
    # nên số dự kiện của brief không được nhiều hơn.
    assert len(r_staff.json()["facts"]) <= len(r_manager.json()["facts"])


# ── /ask ────────────────────────────────────────────────────────────────────


def test_ask_returns_grounded_answer_in_replay() -> None:
    r = client.post(
        "/api/v1/experience/quanverse/ask",
        headers=headers(client, "lan"),
        json={"page": "living_map", "question": "Hôm nay có gì cần chú ý?"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answer"]
    assert body["grounded"] is True
    assert body["citations"], "câu trả lời có căn cứ phải kèm trích dẫn"
    assert body["provider"] == "replay"
    assert body["page"] == "living_map"


def test_ask_answer_has_no_uncited_numbers() -> None:
    """Bất biến số: mọi số trong câu trả lời phải có trong brief."""
    from ca_agents.ag_quanverse.assistant import audit_answer
    from ca_contracts import QuanverseAskResponse

    r = client.post(
        "/api/v1/experience/quanverse/ask",
        headers=headers(client, "lan"),
        json={"page": "living_map", "question": "Quán đang thế nào?"},
    )
    body = r.json()
    resp = QuanverseAskResponse.model_validate(body)
    assert audit_answer(resp.answer, resp.brief) == []


def test_ask_empty_page_is_not_grounded() -> None:
    """Trang chưa có dữ liệu → KHÔNG được trả lời như một kết luận."""
    r = client.post(
        "/api/v1/experience/quanverse/ask",
        headers=headers(client, "lan"),
        json={"page": "war_room", "question": "Phương án nào tốt nhất?"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    if not body["citations"]:
        assert body["grounded"] is False
        assert "Không suy đoán" in body["answer"]


def test_ask_requires_question() -> None:
    r = client.post(
        "/api/v1/experience/quanverse/ask",
        headers=headers(client, "lan"),
        json={"page": "living_map", "question": "   "},
    )
    assert r.status_code == 422


def test_ask_rejects_unknown_page() -> None:
    r = client.post(
        "/api/v1/experience/quanverse/ask",
        headers=headers(client, "lan"),
        json={"page": "khong_ton_tai", "question": "?"},
    )
    assert r.status_code == 404


def test_ask_rejects_overlong_question() -> None:
    r = client.post(
        "/api/v1/experience/quanverse/ask",
        headers=headers(client, "lan"),
        json={"page": "living_map", "question": "x" * 501},
    )
    assert r.status_code == 422


def test_ask_requires_auth() -> None:
    r = client.post(
        "/api/v1/experience/quanverse/ask",
        json={"page": "living_map", "question": "?"},
    )
    assert r.status_code in (401, 403)


def test_ask_brief_matches_brief_endpoint() -> None:
    """Ngữ cảnh của câu trả lời PHẢI trùng bản tóm tắt UI thấy — không lệch số."""
    r_brief = client.get(
        "/api/v1/experience/quanverse/brief/living_map", headers=headers(client, "lan")
    )
    r_ask = client.post(
        "/api/v1/experience/quanverse/ask",
        headers=headers(client, "lan"),
        json={"page": "living_map", "question": "Tóm tắt giúp tôi"},
    )
    brief = r_brief.json()
    ask_brief = r_ask.json()["brief"]
    assert {m["key"]: m["value"] for m in brief["metrics"]} == {
        m["key"]: m["value"] for m in ask_brief["metrics"]
    }
