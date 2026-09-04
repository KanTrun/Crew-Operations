from __future__ import annotations

from ca_api.ai_learning.rollout import select_active_rules


def _rule(rule_id: str, rollout: dict[str, object] | None = None) -> dict[str, object]:
    rule: dict[str, object] = {"id": rule_id, "rule": {"text": rule_id}}
    if rollout is not None:
        rule["rollout"] = rollout
    return rule


def test_canary_selection_is_stable_for_store_and_recipient() -> None:
    rules = [_rule("canary", {"mode": "canary", "percentage": 50})]
    first = select_active_rules(rules, store_id="quan_a", identity="nv_03")
    assert select_active_rules(rules, store_id="quan_a", identity="nv_03") == first


def test_canary_percentage_boundaries_and_legacy_active_rules() -> None:
    none, none_bucket = select_active_rules([_rule("none", {"mode": "canary", "percentage": 0})], store_id="quan_a", identity="nv_03")
    all_rules, all_bucket = select_active_rules([_rule("all", {"mode": "canary", "percentage": 100})], store_id="quan_a", identity="nv_03")
    legacy, legacy_bucket = select_active_rules([_rule("legacy")], store_id="quan_a", identity="nv_03")
    assert none == [] and none_bucket == "control"
    assert [rule["id"] for rule in all_rules] == ["all"] and all_bucket == "canary_50"
    assert [rule["id"] for rule in legacy] == ["legacy"] and legacy_bucket == "active_100"