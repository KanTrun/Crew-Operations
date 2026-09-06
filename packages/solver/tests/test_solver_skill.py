import importlib.util
from pathlib import Path

# Load validate_solver_payload từ skills/repositories/repo-skills/solver-scheduling/scripts
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "skills" / "repositories" / "repo-skills" / "solver-scheduling" / "scripts" / "validate_solver_payload.py"

spec = importlib.util.spec_from_file_location("validate_solver_payload", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
validate_solver_payload = mod.validate_solver_payload


def test_validate_solver_payload_valid() -> None:
    payload = {
        "nhan_vien": ["lan", "hung"],
        "ca_ids": ["ca_1"],
        "ca_meta": {
            "ca_1": {"thu": "T2", "bat_dau": "08:00", "ket_thuc": "12:00"}
        },
        "so_nguoi_toi_thieu": {"ca_1": 1},
    }
    res = validate_solver_payload(payload)
    assert res["valid"] is True
    assert len(res["errors"]) == 0
    assert res["total_shifts"] == 1
    assert res["total_staff"] == 2


def test_validate_solver_payload_missing_fields() -> None:
    payload = {"nhan_vien": ["lan"]}
    res = validate_solver_payload(payload)
    assert res["valid"] is False
    assert any("ca_ids" in err for err in res["errors"])
    assert any("ca_meta" in err for err in res["errors"])


def test_validate_solver_payload_invalid_time_and_day() -> None:
    payload = {
        "nhan_vien": ["lan"],
        "ca_ids": ["ca_err"],
        "ca_meta": {
            "ca_err": {"thu": "T8", "bat_dau": "12:00", "ket_thuc": "08:00"}
        },
    }
    res = validate_solver_payload(payload)
    assert res["valid"] is False
    assert any("INVALID_THU" in err for err in res["errors"])
    assert any("INVALID_DURATION" in err for err in res["errors"])


def test_validate_solver_payload_tkb() -> None:
    payload = {
        "nhan_vien": ["lan"],
        "ca_ids": ["ca_1"],
        "ca_meta": {
            "ca_1": {"thu": "T2", "bat_dau": "08:00", "ket_thuc": "12:00"}
        },
        "tkb": {
            "lan": [["T2", "09:00", "11:00"]],
            "unknown_staff": [["T3", "08:00", "10:00"]],
        },
    }
    res = validate_solver_payload(payload)
    assert res["valid"] is True
    assert any("UNKNOWN_STAFF_TKB" in w for w in res["warnings"])
