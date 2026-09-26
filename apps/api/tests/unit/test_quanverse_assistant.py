"""Trợ lý Quánverse — tổng hợp tất định + cổng grounding (plan quanverse-ai-rework).

Bộ test này khoá đúng ba bất biến quan trọng nhất:

1. **Brief là TẤT ĐỊNH**: cùng đầu vào cho cùng đầu ra; không gọi mạng, không
   phụ thuộc `CA_AGENT_MODE`.
2. **Không bịa số**: câu trả lời ở chế độ replay dựng thẳng từ brief, nên mọi số
   trong đó phải có trong brief.
3. **Không bịa kết luận**: khi brief không có `grounded_refs` nào thì câu trả lời
   PHẢI nói rõ "không suy đoán", và `grounded=False`.

Bất biến 3 là bất biến dễ vỡ nhất khi refactor: nó không làm test đỏ ở đường
"happy path" nào, nên phải có bài kiểm riêng cho đúng nó.
"""

from __future__ import annotations

import pytest
from ca_agents.ag_quanverse import answer_question, audit_answer, build_brief
from ca_agents.ag_quanverse.assistant import _numbers_in
from ca_contracts import QuanversePage


@pytest.fixture(autouse=True)
def _replay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neo chế độ replay: mọi bài ở đây KHÔNG được gọi mạng."""
    monkeypatch.setenv("CA_AGENT_MODE", "replay")


# ── Bất biến 1: tất định ────────────────────────────────────────────────────


def test_brief_living_map_flags_hot_zone() -> None:
    brief = build_brief(
        QuanversePage.LIVING_MAP,
        zones=[
            {"zone_id": "bar", "label": "Quầy pha chế", "active": True, "load_signal": 0.72},
            {"zone_id": "cashier", "label": "Thu ngân", "active": True, "load_signal": 0.3},
        ],
        events=[],
        modes=[{"mode": "dem_nhac", "active": True}],
        horizon=[],
        data_quality=[],
    )
    hot = [m for m in brief.metrics if m.key == "hot_zones"]
    assert hot and hot[0].value == 1.0
    assert hot[0].tone == "danger"
    assert any("quá tải" in r for r in brief.risks)
    assert "bar" in brief.grounded_refs


def test_brief_is_deterministic_same_input_same_output() -> None:
    """Cùng đầu vào → cùng đầu ra (không phụ thuộc thời gian/ngẫu nhiên)."""
    payload = {
        "zones": [{"zone_id": "bar", "label": "Quầy", "active": True, "load_signal": 0.5}],
        "events": [],
        "modes": [],
        "horizon": [],
        "data_quality": [],
    }
    first = build_brief(QuanversePage.LIVING_MAP, **payload)
    second = build_brief(QuanversePage.LIVING_MAP, **payload)
    assert first.model_dump() == second.model_dump()


def test_metric_value_none_means_missing_not_zero() -> None:
    """`None` = chưa có dữ liệu; phải KHÁC `0.0` (quy ước số của dự án)."""
    brief = build_brief(QuanversePage.SPATIAL_MEMORY, anchors=[], memory_counts={})
    memories = next(m for m in brief.metrics if m.key == "memories")
    # 0 ký ức ở đây là số THẬT (có dữ liệu, bằng không) — không phải None.
    assert memories.value == 0.0
    assert memories.value is not None


def test_brief_shift_rescue_lists_why_blocked() -> None:
    brief = build_brief(
        QuanversePage.SHIFT_RESCUE,
        case={
            "case_id": "case_1",
            "status": "candidates_ready",
            "shift_id": "w1_c01",
            "candidates": [
                {
                    "candidate_id": "cand_1",
                    "nv_id": "nv_01",
                    "nv_ten": "Minh",
                    "safe": True,
                    "added_hours": 4,
                    "fairness_delta": -1,
                    "skill_coverage": 0.8,
                }
            ],
            "blocked": [
                {"nv_id": "nv_09", "nv_ten": "Hùng", "reason_blocks": ["qua_gioi_han_gio"]}
            ],
            "invited": [],
        },
    )
    assert any("qua_gioi_han_gio" in r for r in brief.risks)
    assert any("Minh" in f for f in brief.facts)
    assert "case_1" in brief.grounded_refs


def test_brief_war_room_highlights_violations() -> None:
    brief = build_brief(
        QuanversePage.WAR_ROOM,
        simulation={
            "simulation_id": "sim_1",
            "baseline_snapshot_hash": "abcdef123456",
            "baseline": {"so_nguoi": 3},
            "options": [
                {"option_id": "opt_a", "estimated_cost": 100000, "constraint_violations": []},
                {
                    "option_id": "opt_b",
                    "estimated_cost": 200000,
                    "constraint_violations": ["thieu_nguoi"],
                },
            ],
        },
    )
    assert any("vi phạm ràng buộc" in r for r in brief.risks)
    violations = next(m for m in brief.metrics if m.key == "violations")
    assert violations.value == 1.0
    assert violations.tone == "danger"


def test_brief_rules_low_confidence_is_a_risk() -> None:
    brief = build_brief(
        QuanversePage.RULES,
        candidates=[
            {"candidate_id": "rc_1", "sentence": "Cuối tuần cần thêm người", "confidence": 0.3,
             "status": "de_xuat"},
        ],
        sources=["so_lan_sua"],
    )
    assert any("độ tin cậy thấp" in r for r in brief.risks)
    assert "rc_1" in brief.grounded_refs


def test_brief_spatial_memory_empty_reports_two_risks() -> None:
    """Neo rỗng: phải nói rõ vừa không đọc được neo, vừa không có ký ức nào."""
    brief = build_brief(QuanversePage.SPATIAL_MEMORY, anchors=[], memory_counts={})
    assert any("Chưa đọc được neo" in r for r in brief.risks)
    assert any("Chưa có ký ức nào được xác nhận" in r for r in brief.risks)
    anchors_metric = next(m for m in brief.metrics if m.key == "anchors")
    assert anchors_metric.value == 0.0


# ── Bất biến 2: không bịa số ────────────────────────────────────────────────


def test_audit_flags_number_absent_from_brief() -> None:
    brief = build_brief(
        QuanversePage.LIVING_MAP,
        zones=[{"zone_id": "bar", "label": "Quầy", "active": True, "load_signal": 0.8}],
        events=[],
        modes=[],
        horizon=[],
        data_quality=[],
    )
    violations = audit_answer("Quán đang có 999 khách.", brief)
    assert any("999" in v for v in violations)


def test_audit_flags_absolute_language() -> None:
    brief = build_brief(
        QuanversePage.LIVING_MAP,
        zones=[{"zone_id": "bar", "label": "Quầy", "active": True, "load_signal": 0.8}],
        events=[],
        modes=[],
        horizon=[],
        data_quality=[],
    )
    violations = audit_answer("Chắc chắn mọi thứ luôn luôn ổn.", brief)
    assert any("tuyệt đối" in v for v in violations)


def test_audit_accepts_answer_built_from_brief() -> None:
    """Câu trả lời tất định phải QUA cổng grounding — nếu không, cổng quá chặt."""
    payload = {
        "zones": [{"zone_id": "bar", "label": "Quầy", "active": True, "load_signal": 0.8}],
        "events": [],
        "modes": [],
        "horizon": [],
        "data_quality": [],
    }
    brief = build_brief(QuanversePage.LIVING_MAP, **payload)
    resp = answer_question(page=QuanversePage.LIVING_MAP, question="Sao rồi?", brief=brief)
    assert audit_answer(resp.answer, brief) == []


def test_number_extraction_handles_thousand_separators() -> None:
    """'200.000' và '200,000' phải quy về cùng một số để cổng không báo động giả."""
    assert _numbers_in("200.000 đ") == _numbers_in("200,000 đ")


# ── Bất biến 3: không bịa kết luận ──────────────────────────────────────────


def test_empty_brief_is_not_grounded_and_says_so() -> None:
    """Trang trống: KHÔNG được trình bày như một kết luận."""
    brief = build_brief(QuanversePage.SPATIAL_MEMORY, anchors=[], memory_counts={})
    resp = answer_question(
        page=QuanversePage.SPATIAL_MEMORY, question="Khu này có gì?", brief=brief
    )
    assert resp.grounded is False
    assert resp.citations == []
    assert "Không suy đoán" in resp.answer


def test_answer_cites_refs_from_brief() -> None:
    brief = build_brief(
        QuanversePage.LIVING_MAP,
        zones=[{"zone_id": "bar", "label": "Quầy", "active": True, "load_signal": 0.9}],
        events=[{"event_id": "ev_1", "summary": "Khách đoàn tới", "status": "confirmed"}],
        modes=[],
        horizon=[],
        data_quality=[],
    )
    resp = answer_question(page=QuanversePage.LIVING_MAP, question="Có gì?", brief=brief)
    assert resp.grounded is True
    assert "bar" in resp.citations
    assert "ev_1" in resp.citations


def test_replay_never_calls_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chế độ replay phải KHÔNG chạm `llm.complete` — chứng minh bằng cách chặn nó."""
    import ca_agents.ag_quanverse.assistant as assistant

    called = {"n": 0}

    def _boom(*args: object, **kwargs: object) -> object:
        called["n"] += 1
        raise AssertionError("replay không được gọi llm.complete")

    monkeypatch.setattr(assistant, "complete", _boom)
    brief = build_brief(
        QuanversePage.LIVING_MAP,
        zones=[{"zone_id": "bar", "label": "Quầy", "active": True, "load_signal": 0.8}],
        events=[],
        modes=[],
        horizon=[],
        data_quality=[],
    )
    resp = answer_question(page=QuanversePage.LIVING_MAP, question="Sao?", brief=brief)
    assert called["n"] == 0
    assert resp.provider == "replay"


def test_live_bad_llm_answer_falls_back_to_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM thêm số không có trong brief → KHÔNG được trình bày như sự thật."""
    import ca_agents.ag_quanverse.assistant as assistant
    from ca_agents.llm import LlmResult

    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setattr(
        assistant,
        "complete",
        lambda **_: LlmResult(ok=True, text="Quán có 999 khách.", provider="groq", reason="ok"),
    )
    brief = build_brief(
        QuanversePage.LIVING_MAP,
        zones=[{"zone_id": "bar", "label": "Quầy", "active": True, "load_signal": 0.8}],
        events=[],
        modes=[],
        horizon=[],
        data_quality=[],
    )
    resp = answer_question(page=QuanversePage.LIVING_MAP, question="Sao?", brief=brief)
    assert "999" not in resp.answer
    assert resp.unsupported_claims  # lý do bị chặn được ghi lại
    assert resp.provider.startswith("replay")


def test_live_clean_llm_answer_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM diễn đạt lại đúng dữ kiện → dùng lời của nó, ghi rõ provider."""
    import ca_agents.ag_quanverse.assistant as assistant
    from ca_agents.llm import LlmResult

    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setattr(
        assistant,
        "complete",
        lambda **_: LlmResult(
            ok=True, text="Quầy đang quá tải, nên san người.", provider="groq", reason="ok"
        ),
    )
    brief = build_brief(
        QuanversePage.LIVING_MAP,
        zones=[{"zone_id": "bar", "label": "Quầy", "active": True, "load_signal": 0.8}],
        events=[],
        modes=[],
        horizon=[],
        data_quality=[],
    )
    resp = answer_question(page=QuanversePage.LIVING_MAP, question="Sao?", brief=brief)
    assert resp.provider == "groq"
    assert resp.unsupported_claims == []


def test_live_provider_failure_falls_back_silently(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provider chết/hết quota là chuyện thường — phải rơi về tất định, không lỗi."""
    import ca_agents.ag_quanverse.assistant as assistant
    from ca_agents.llm import LlmResult

    monkeypatch.setenv("CA_AGENT_MODE", "live")
    monkeypatch.setattr(
        assistant,
        "complete",
        lambda **_: LlmResult(ok=False, text="", provider="tu_choi", reason="no_key"),
    )
    brief = build_brief(
        QuanversePage.LIVING_MAP,
        zones=[{"zone_id": "bar", "label": "Quầy", "active": True, "load_signal": 0.8}],
        events=[],
        modes=[],
        horizon=[],
        data_quality=[],
    )
    resp = answer_question(page=QuanversePage.LIVING_MAP, question="Sao?", brief=brief)
    assert resp.answer  # vẫn có câu trả lời
    assert resp.provider.startswith("replay")


def test_unknown_page_returns_safe_brief() -> None:
    """Trang không có bộ tổng hợp → brief an toàn, không ném lỗi."""
    brief = build_brief(QuanversePage.RULES, candidates=[], sources=[])
    assert brief.headline
    resp = answer_question(page=QuanversePage.RULES, question="Luật nào?", brief=brief)
    assert resp.answer
    assert resp.grounded is False
