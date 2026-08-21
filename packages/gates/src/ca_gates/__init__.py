"""ca-gates — Sprint 2 verification gate pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ca_gates.vf_conf import ConfResult, validate_conf
from ca_gates.vf_schema import SchemaResult, validate_schema
from ca_gates.vf_trace import TraceResult, validate_trace

__all__ = [
    "GateResult",
    "run_vf_pipeline",
    "validate_schema",
    "validate_trace",
    "validate_conf",
    "SchemaResult",
    "TraceResult",
    "ConfResult",
]


@dataclass
class GateResult:
    """Aggregate result for one extraction through all three VF gates."""

    passed: bool
    escalate: bool
    retry_once: bool
    schema: SchemaResult
    trace: TraceResult
    conf: ConfResult
    reasons: list[str] = field(default_factory=list)


def run_vf_pipeline(
    extraction: dict[str, Any],
    evidence: Any,
    schema_keys: list[str],
    *,
    already_retried: bool = False,
    confidence_threshold: float = 0.7,
) -> GateResult:
    """Run VF-SCHEMA → VF-TRACE → VF-CONF gates on a single extraction.

    Gates run in order; each failure is recorded but all three always run so
    the caller gets a full picture in one pass.

    Args:
        extraction: The extraction dict to validate.
        evidence: Raw evidence used by VF-TRACE (str, list[str], or dict with "text").
        schema_keys: Required keys for VF-SCHEMA.
        already_retried: Pass True if this extraction has already been retried once.
        confidence_threshold: Minimum confidence for VF-CONF (default 0.7).

    Returns:
        GateResult summarising all gate decisions.
    """
    schema_result = validate_schema(
        extraction, schema_keys, already_retried=already_retried
    )
    trace_result = validate_trace(extraction, evidence)
    conf_result = validate_conf(extraction, threshold=confidence_threshold)

    reasons: list[str] = []
    if not schema_result.passed:
        reasons.append(f"VF-SCHEMA: {schema_result.reason}")
    if not trace_result.passed:
        reasons.append(f"VF-TRACE: {trace_result.reason}")
    if not conf_result.passed:
        reasons.append(f"VF-CONF: {conf_result.reason}")

    escalate = schema_result.escalate or trace_result.escalate or conf_result.escalate
    # retry_once only when schema says retry AND no other gate forces escalation
    retry_once = schema_result.retry_once and not escalate
    passed = schema_result.passed and trace_result.passed and conf_result.passed

    return GateResult(
        passed=passed,
        escalate=escalate,
        retry_once=retry_once,
        schema=schema_result,
        trace=trace_result,
        conf=conf_result,
        reasons=reasons,
    )
