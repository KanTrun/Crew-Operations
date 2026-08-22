from __future__ import annotations

from ca_agents.ag_handover import extract
from ca_agents.ag_sop import answer


def test_handover_labels() -> None:
    h = extract("Tình hình: hết sữa\nBối cảnh: T3\nĐánh giá: ổn\nĐề nghị: nhập")
    assert "sữa" in h.tinh_hinh


def test_sop_unknown() -> None:
    r = answer("lương tháng này?", buoc=[], luat=[])
    assert r.chua_co
