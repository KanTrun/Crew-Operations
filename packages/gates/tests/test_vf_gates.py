"""Tests for ca-gates VF pipeline — VF-SCHEMA, VF-TRACE, VF-CONF."""

from __future__ import annotations

import pytest
from ca_gates import run_vf_pipeline
from ca_gates.vf_conf import blur_case, validate_conf
from ca_gates.vf_schema import validate_schema
from ca_gates.vf_trace import validate_trace

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SCHEMA_KEYS = ["value", "label", "source_span", "confidence"]

GOOD_EXTRACTION = {
    "value": "Nguyen Van A",
    "label": "name",
    "source_span": {"page": 1, "x": 10.0, "y": 20.0, "w": 100.0, "h": 15.0},
    "confidence": 0.92,
}

EVIDENCE_TEXT = "Nguyen Van A is the applicant listed on page 1."


# ---------------------------------------------------------------------------
# VF-SCHEMA
# ---------------------------------------------------------------------------


class TestVfSchema:
    def test_pass_all_keys_present(self):
        result = validate_schema(GOOD_EXTRACTION, SCHEMA_KEYS)
        assert result.passed
        assert not result.retry_once
        assert not result.escalate

    def test_missing_key_first_attempt_triggers_retry(self):
        extraction = {k: v for k, v in GOOD_EXTRACTION.items() if k != "label"}
        result = validate_schema(extraction, SCHEMA_KEYS)
        assert not result.passed
        assert result.retry_once
        assert not result.escalate
        assert "label" in result.missing_keys

    def test_missing_key_after_retry_escalates(self):
        extraction = {k: v for k, v in GOOD_EXTRACTION.items() if k != "label"}
        result = validate_schema(extraction, SCHEMA_KEYS, already_retried=True)
        assert not result.passed
        assert not result.retry_once
        assert result.escalate

    def test_multiple_missing_keys(self):
        result = validate_schema({}, SCHEMA_KEYS)
        assert not result.passed
        assert set(result.missing_keys) == set(SCHEMA_KEYS)


# ---------------------------------------------------------------------------
# VF-TRACE
# ---------------------------------------------------------------------------


class TestVfTrace:
    def test_pass_spatial_span(self):
        result = validate_trace(GOOD_EXTRACTION, EVIDENCE_TEXT)
        assert result.passed
        assert not result.escalate

    def test_pass_text_offset_span(self):
        extraction = {**GOOD_EXTRACTION, "source_span": {"text_offset": 0}}
        result = validate_trace(extraction, EVIDENCE_TEXT)
        assert result.passed

    def test_fail_missing_source_span(self):
        extraction = {k: v for k, v in GOOD_EXTRACTION.items() if k != "source_span"}
        result = validate_trace(extraction, EVIDENCE_TEXT)
        assert not result.passed
        assert result.escalate

    def test_fail_text_offset_out_of_bounds(self):
        extraction = {**GOOD_EXTRACTION, "source_span": {"text_offset": 99999}}
        result = validate_trace(extraction, EVIDENCE_TEXT)
        assert not result.passed
        assert result.escalate

    def test_fail_invalid_span_type(self):
        extraction = {**GOOD_EXTRACTION, "source_span": "page:1"}
        result = validate_trace(extraction, EVIDENCE_TEXT)
        assert not result.passed
        assert result.escalate

    def test_pass_text_offset_with_evidence_list(self):
        extraction = {**GOOD_EXTRACTION, "source_span": {"text_offset": 5}}
        result = validate_trace(extraction, ["Hello", "World"])
        assert result.passed  # "Hello World" len=11, offset 5 is valid

    def test_fail_incomplete_spatial_span(self):
        # Missing 'h' — neither spatial nor text_offset
        extraction = {
            **GOOD_EXTRACTION,
            "source_span": {"page": 1, "x": 0, "y": 0, "w": 10},
        }
        result = validate_trace(extraction, EVIDENCE_TEXT)
        assert not result.passed
        assert result.escalate


# ---------------------------------------------------------------------------
# VF-CONF
# ---------------------------------------------------------------------------


class TestVfConf:
    def test_pass_above_threshold(self):
        result = validate_conf(GOOD_EXTRACTION)
        assert result.passed
        assert not result.escalate
        assert result.confidence == pytest.approx(0.92)

    def test_fail_below_threshold_escalates(self):
        extraction = {**GOOD_EXTRACTION, "confidence": 0.5}
        result = validate_conf(extraction)
        assert not result.passed
        assert result.escalate
        assert result.confidence == pytest.approx(0.5)

    def test_fail_exact_threshold_boundary_escalates(self):
        # confidence == threshold - epsilon → must escalate
        extraction = {**GOOD_EXTRACTION, "confidence": 0.699}
        result = validate_conf(extraction, threshold=0.7)
        assert not result.passed
        assert result.escalate

    def test_pass_exact_threshold(self):
        extraction = {**GOOD_EXTRACTION, "confidence": 0.7}
        result = validate_conf(extraction, threshold=0.7)
        assert result.passed

    def test_fail_missing_confidence_escalates(self):
        extraction = {k: v for k, v in GOOD_EXTRACTION.items() if k != "confidence"}
        result = validate_conf(extraction)
        assert not result.passed
        assert result.escalate

    def test_custom_threshold(self):
        extraction = {**GOOD_EXTRACTION, "confidence": 0.85}
        result = validate_conf(extraction, threshold=0.9)
        assert not result.passed
        assert result.escalate

    # blur_case helper -------------------------------------------------------

    def test_blur_case_low_score_low_confidence(self):
        conf = blur_case(10.0, max_blur=100.0)
        assert conf == pytest.approx(0.1)

    def test_blur_case_full_score_full_confidence(self):
        conf = blur_case(100.0, max_blur=100.0)
        assert conf == pytest.approx(1.0)

    def test_blur_case_clamps_above_max(self):
        conf = blur_case(150.0, max_blur=100.0)
        assert conf == pytest.approx(1.0)

    def test_blur_case_clamps_below_zero(self):
        conf = blur_case(-5.0, max_blur=100.0)
        assert conf == pytest.approx(0.0)

    def test_blur_case_invalid_max_blur(self):
        with pytest.raises(ValueError):
            blur_case(50.0, max_blur=0.0)

    # intentional blur case escalation via VF-CONF ---------------------------

    def test_blur_case_triggers_escalation_via_vf_conf(self):
        """An image with blur_score=20 (very blurry) must escalate — no retry."""
        blur_score = 20.0  # blurry document image
        confidence = blur_case(blur_score, max_blur=100.0)  # → 0.20

        extraction = {
            **GOOD_EXTRACTION,
            "confidence": confidence,
        }
        result = validate_conf(extraction, threshold=0.7)

        assert not result.passed
        assert result.escalate, "Blurry image must always escalate — no retry path"
        assert result.confidence == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# run_vf_pipeline (full pipeline)
# ---------------------------------------------------------------------------


class TestRunVfPipeline:
    def test_all_gates_pass(self):
        result = run_vf_pipeline(GOOD_EXTRACTION, EVIDENCE_TEXT, SCHEMA_KEYS)
        assert result.passed
        assert not result.escalate
        assert not result.retry_once
        assert result.reasons == []

    def test_schema_fail_first_attempt_retry(self):
        extraction = {k: v for k, v in GOOD_EXTRACTION.items() if k != "label"}
        result = run_vf_pipeline(extraction, EVIDENCE_TEXT, SCHEMA_KEYS)
        assert not result.passed
        assert result.retry_once
        assert not result.escalate

    def test_schema_fail_second_attempt_escalate(self):
        extraction = {k: v for k, v in GOOD_EXTRACTION.items() if k != "label"}
        result = run_vf_pipeline(
            extraction, EVIDENCE_TEXT, SCHEMA_KEYS, already_retried=True
        )
        assert not result.passed
        assert result.escalate
        assert not result.retry_once

    def test_trace_fail_escalates_immediately(self):
        extraction = {k: v for k, v in GOOD_EXTRACTION.items() if k != "source_span"}
        result = run_vf_pipeline(extraction, EVIDENCE_TEXT, SCHEMA_KEYS)
        assert not result.passed
        assert result.escalate
        assert not result.retry_once

    def test_conf_fail_escalates_no_retry(self):
        extraction = {**GOOD_EXTRACTION, "confidence": 0.3}
        result = run_vf_pipeline(extraction, EVIDENCE_TEXT, SCHEMA_KEYS)
        assert not result.passed
        assert result.escalate
        assert not result.retry_once

    def test_multiple_gate_failures_all_reasons_reported(self):
        extraction = {"value": "x", "confidence": 0.1}
        result = run_vf_pipeline(extraction, EVIDENCE_TEXT, SCHEMA_KEYS)
        assert not result.passed
        assert result.escalate
        reason_text = " ".join(result.reasons)
        assert "VF-SCHEMA" in reason_text
        assert "VF-TRACE" in reason_text
        assert "VF-CONF" in reason_text

    def test_custom_confidence_threshold(self):
        extraction = {**GOOD_EXTRACTION, "confidence": 0.6}
        # passes at 0.5 threshold
        result = run_vf_pipeline(
            extraction, EVIDENCE_TEXT, SCHEMA_KEYS, confidence_threshold=0.5
        )
        assert result.passed
