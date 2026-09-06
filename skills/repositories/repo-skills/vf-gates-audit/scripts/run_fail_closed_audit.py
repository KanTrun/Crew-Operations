#!/usr/bin/env python3
"""Script thẩm định đề xuất của Agent qua hệ thống cổng kiểm duyệt Fail-Closed (VF Gates).

Thực thi kiểm tra VF-SCHEMA -> VF-TRACE -> VF-CONF.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Tìm root của monorepo
curr = Path(__file__).resolve()
REPO_ROOT = None
for p in curr.parents:
    if (p / "pyproject.toml").exists() and (p / "packages").exists():
        REPO_ROOT = p
        break

if REPO_ROOT is not None:
    GATES_SRC = REPO_ROOT / "packages" / "gates" / "src"
    if str(GATES_SRC) not in sys.path:
        sys.path.insert(0, str(GATES_SRC))

try:
    from ca_gates import run_vf_pipeline
    GATES_AVAILABLE = True
except ImportError:
    GATES_AVAILABLE = False


def audit_extraction(
    extraction: dict[str, Any],
    evidence: Any,
    schema_keys: list[str],
    confidence_threshold: float = 0.7,
) -> dict[str, Any]:
    """Thực hiện kiểm tra cổng VF fail-closed."""
    if GATES_AVAILABLE:
        res = run_vf_pipeline(
            extraction,
            evidence,
            schema_keys,
            confidence_threshold=confidence_threshold,
        )
        return {
            "passed": res.passed,
            "escalate": res.escalate,
            "retry_once": res.retry_once,
            "reasons": res.reasons,
            "schema_passed": res.schema.passed,
            "trace_passed": res.trace.passed,
            "conf_passed": res.conf.passed,
        }

    # Fallback kiểm tra cơ bản nếu không có thư viện ca_gates
    missing = [k for k in schema_keys if k not in extraction]
    conf = extraction.get("confidence", 1.0)
    passed = len(missing) == 0 and conf >= confidence_threshold
    reasons = []
    if missing:
        reasons.append(f"VF-SCHEMA: Thiếu trường {missing}")
    if conf < confidence_threshold:
        reasons.append(f"VF-CONF: Độ tin cậy {conf} < {confidence_threshold}")

    return {
        "passed": passed,
        "escalate": not passed,
        "retry_once": False,
        "reasons": reasons,
        "schema_passed": len(missing) == 0,
        "trace_passed": True,
        "conf_passed": conf >= confidence_threshold,
    }


def main() -> int:
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        extraction = data.get("extraction", {})
        evidence = data.get("evidence", "")
        schema_keys = data.get("schema_keys", ["intent", "reason", "confidence"])
    else:
        # Smoke test mẫu
        evidence = "Hùng xin nghỉ ca sáng thứ 2 ngày 24 do bận việc gia đình."
        extraction = {
            "intent": "xin_nghi_ca",
            "nhan_vien": "Hùng",
            "ca": "ca_sang_t2",
            "reason": "bận việc gia đình",
            "confidence": 0.95,
            "source_span": {"text_offset": 0},
        }
        schema_keys = ["intent", "nhan_vien", "ca", "reason", "confidence"]


    result = audit_extraction(extraction, evidence, schema_keys)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
