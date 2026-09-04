from __future__ import annotations

from ca_agents.ag_fbpage_reflection import run_facebook_reflection


def test_facebook_reflection_proposes_pending_rule_from_repeated_manager_edits() -> None:
    events = [
        {
            "id": f"feedback-{index}", "store_id": "quan_01", "channel": "facebook",
            "type": "manager_edit", "materially_edited": True,
            "final": {"body": "Dạ Nhịp Quán xin chào mình ạ!\n\nEm hỗ trợ mình ngay."},
        }
        for index in range(3)
    ]
    report = run_facebook_reflection(store_id="quan_01", feedback_events=events)
    proposal = report["proposal"]
    assert proposal is not None
    assert proposal["status"] == "pending"
    assert proposal["evidence_ids"] == ["feedback-0", "feedback-1", "feedback-2"]


def test_facebook_reflection_requires_minimum_evidence() -> None:
    event = {
        "id": "feedback-1", "store_id": "quan_01", "channel": "facebook",
        "type": "manager_edit", "materially_edited": True,
        "final": {"body": "Dạ Nhịp Quán xin chào mình ạ!"},
    }
    assert run_facebook_reflection(store_id="quan_01", feedback_events=[event]) ["proposal"] is None