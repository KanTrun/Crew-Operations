import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# 1. Load audit_recipe_waste
WASTE_SCRIPT = REPO_ROOT / "skills" / "repositories" / "repo-skills" / "barista-waste-audit" / "scripts" / "audit_recipe_waste.py"
spec_waste = importlib.util.spec_from_file_location("audit_recipe_waste", WASTE_SCRIPT)
mod_waste = importlib.util.module_from_spec(spec_waste)
spec_waste.loader.exec_module(mod_waste)
audit_waste = mod_waste.audit_waste

# 2. Load reconcile_shift_cash
CASH_SCRIPT = REPO_ROOT / "skills" / "repositories" / "repo-skills" / "handover-reconciliation" / "scripts" / "reconcile_shift_cash.py"
spec_cash = importlib.util.spec_from_file_location("reconcile_shift_cash", CASH_SCRIPT)
mod_cash = importlib.util.module_from_spec(spec_cash)
spec_cash.loader.exec_module(mod_cash)
reconcile_cash = mod_cash.reconcile_cash


def test_audit_recipe_waste_compliant() -> None:
    sold = {"latte": 10}  # 180g cafe, 1500ml sữa
    actual = {"coffee_gram": 185.0, "milk_ml": 1550.0}  # Dưới 5% hao hụt
    res = audit_waste(sold, actual)
    assert res["compliant"] is True
    assert len(res["flagged_ingredients"]) == 0


def test_audit_recipe_waste_exceeded() -> None:
    sold = {"espresso": 10}  # 180g cafe
    actual = {"coffee_gram": 220.0}  # Hao hụt > 20%
    res = audit_waste(sold, actual)
    assert res["compliant"] is False
    assert len(res["flagged_ingredients"]) == 1
    assert res["flagged_ingredients"][0]["ingredient"] == "coffee_gram"


def test_reconcile_cash_matched() -> None:
    res = reconcile_cash(opening_cash=500000, pos_cash_sales=2000000, paid_outs=0, actual_cash_counted=2500000)
    assert res["matched"] is True
    assert res["status"] == "MATCHED"
    assert res["discrepancy_amount"] == 0


def test_reconcile_cash_shortage() -> None:
    res = reconcile_cash(opening_cash=500000, pos_cash_sales=2000000, paid_outs=100000, actual_cash_counted=2300000)
    assert res["matched"] is False
    assert res["status"] == "SHORTAGE"
    assert res["discrepancy_amount"] == -100000
