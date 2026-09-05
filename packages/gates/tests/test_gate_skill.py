import importlib.util
from pathlib import Path

# Load run_fail_closed_audit từ skills/repositories/repo-skills/vf-gates-audit/scripts
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "skills" / "repositories" / "repo-skills" / "vf-gates-audit" / "scripts" / "run_fail_closed_audit.py"

spec = importlib.util.spec_from_file_location("run_fail_closed_audit", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
audit_extraction = mod.audit_extraction


def test_audit_extraction_passed() -> None:
    evidence = "Minh xin nghỉ phép ca chiều thứ 3."
    extraction = {
        "intent": "xin_nghi_phep",
        "nhan_vien": "Minh",
        "ca": "ca_chieu_t3",
        "confidence": 0.92,
        "source_span": {"text_offset": 0},
    }
    schema_keys = ["intent", "nhan_vien", "ca", "confidence"]

    res = audit_extraction(extraction, evidence, schema_keys)
    assert res["passed"] is True
    assert res["escalate"] is False
    assert res["schema_passed"] is True



def test_audit_extraction_missing_schema_key() -> None:
    evidence = "Minh xin nghỉ phép."
    extraction = {
        "intent": "xin_nghi_phep",
        "confidence": 0.90,
    }
    schema_keys = ["intent", "nhan_vien", "ca"]

    res = audit_extraction(extraction, evidence, schema_keys)
    assert res["passed"] is False
    assert res["schema_passed"] is False


def test_audit_extraction_low_confidence() -> None:
    evidence = "Không rõ ai nhắn tin đổi ca."
    extraction = {
        "intent": "doi_ca",
        "confidence": 0.45,
    }
    schema_keys = ["intent", "confidence"]

    res = audit_extraction(extraction, evidence, schema_keys, confidence_threshold=0.7)
    assert res["passed"] is False
    assert res["conf_passed"] is False
    assert res["escalate"] is True
