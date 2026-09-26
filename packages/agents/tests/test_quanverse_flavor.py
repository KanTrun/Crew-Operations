"""QUANVERSE flavor tests (Phase 06)."""

from __future__ import annotations

from ca_agents.ag_quanverse.flavor import (
    FlavorPreference,
    recommend_from_taste,
    scorer,
)

_CATALOG = [
    {"id": "tr_sua", "ten": "Trà sữa", "do_ngot": "ngot", "co_sua": True, "huong_tra": True, "nguyen_lieu": ["trà", "sữa"]},
    {"id": "tra_dao", "ten": "Trà đào", "do_ngot": "it", "co_sua": False, "huong_tra": True, "nguyen_lieu": ["trà", "đào"]},
    {"id": "cafe_sua", "ten": "Cà phê sữa", "do_ngot": "vua", "co_sua": True, "huong_tra": False, "nguyen_lieu": ["cà phê", "sữa"]},
]


def test_recommend_matches_taste() -> None:
    pref = FlavorPreference(do_ngot="it", co_sua=False, huong_tra=True)
    results = recommend_from_taste(pref, _CATALOG)
    assert results
    assert results[0].mon_id == "tra_dao"
    assert results[0].reasons


def test_allergy_never_inferred_blocked() -> None:
    # Khách khai báo dị ứng sữa → loại món chứa sữa ngay
    pref = FlavorPreference(dietary_allergy=["sữa"])
    results = recommend_from_taste(pref, _CATALOG)
    ids = {r.mon_id for r in results}
    assert "tr_sua" not in ids
    assert "cafe_sua" not in ids
    assert "tra_dao" in ids


def test_allergy_not_inferred_from_taste() -> None:
    # Không khai báo dị ứng → không bao giờ tự "đoán" dị ứng
    pref = FlavorPreference(do_ngot="vua")
    r = scorer(pref, _CATALOG[0])
    assert not r.allergy_flag


def test_scorer_explains_why() -> None:
    pref = FlavorPreference(do_ngot="vua", co_sua=True)
    r = scorer(pref, _CATALOG[2])
    assert r.score > 2
    assert any("độ ngọt" in reason for reason in r.reasons)


def test_no_recommendation_for_allergy_only() -> None:
    catalog = [{"id": "x", "ten": "X", "do_ngot": "vua", "co_sua": True, "huong_tra": False, "nguyen_lieu": ["lanh", "pho mai"]}]
    pref = FlavorPreference(dietary_allergy=["pho mai"])
    assert recommend_from_taste(pref, catalog) == []