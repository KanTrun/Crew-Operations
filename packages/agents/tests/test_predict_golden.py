# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit test cho golden dataset success_patterns (plan 260918 mục 7.4).

So sánh kết quả detect_success_patterns với golden data chuẩn.
"""

from __future__ import annotations

import json
from pathlib import Path

from ca_agents.ag_predict import detect_success_patterns

GOLDEN_PATH = Path(__file__).resolve().parents[3] / "data" / "golden" / "success_patterns.json"


def _load_golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def test_golden_patterns_match() -> None:
    golden = _load_golden()
    patterns = detect_success_patterns(
        doanh_thu_by_ca={
            "T2_sang": 100.0, "T2_chieu": 110.0, "T2_toi": 105.0,
            "T6_toi": 500.0, "T7_toi": 480.0,
        },
        doanh_thu_by_mon={
            "caphe_sua_da": 100.0, "tra_dao": 110.0, "caphe_den": 105.0,
            "matcha": 500.0, "socola": 480.0,
        },
        ton_kho_by_time={},
    )
    # Golden có 2 pattern (1 ca + 1 món)
    assert len(patterns) >= 2
    # Kiểm tra các pattern_id trong golden đều xuất hiện
    golden_ids = {p["pattern_id"] for p in golden["patterns"]}
    actual_ids = {p.pattern_id for p in patterns}
    assert golden_ids.issubset(actual_ids)


def test_golden_suggestions_valid() -> None:
    golden = _load_golden()
    # Golden suggestions phải có đủ field contract
    for s in golden["suggestions"]:
        assert "id" in s
        assert "cau" in s
        assert "do_tin_cay" in s
        assert "trang_thai" in s


def test_golden_file_exists() -> None:
    assert GOLDEN_PATH.exists()