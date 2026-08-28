from __future__ import annotations

from dataclasses import asdict

from ca_agents.ag_rule.extract import RuleDraft, propose
from ca_gates.vf_rule import validate_rule


def test_propose_rejects_low_frequency() -> None:
    """Từ chối đề xuất luật khi tần suất n < 3 (n=2 trả về None)."""
    mau = {"n": 2, "bang_chung": ["bc1", "bc2"]}
    assert propose(mau) is None


def test_propose_rejects_zero() -> None:
    """Từ chối đề xuất luật khi n=0 (trả về None)."""
    mau = {"n": 0, "bang_chung": []}
    assert propose(mau) is None


def test_propose_rejects_missing_n() -> None:
    """Từ chối đề xuất luật khi thiếu trường n (dict rỗng trả về None)."""
    assert propose({}) is None


def test_propose_accepts_three() -> None:
    """Chấp nhận đề xuất khi n=3 và trả về RuleDraft có độ tin cậy 0.8."""
    mau = {"n": 3, "bang_chung": ["bc1", "bc2", "bc3"]}
    draft = propose(mau)
    assert isinstance(draft, RuleDraft)
    assert draft.do_tin_cay == 0.8


def test_propose_caps_bang_chung_at_four() -> None:
    """Giới hạn danh sách bằng chứng tối đa là 4 khi đầu vào có 5 phần tử."""
    mau = {"n": 5, "bang_chung": ["bc1", "bc2", "bc3", "bc4", "bc5"]}
    draft = propose(mau)
    assert draft is not None
    assert len(draft.bang_chung) == 4
    assert draft.bang_chung == ["bc1", "bc2", "bc3", "bc4"]


def test_propose_default_loai() -> None:
    """Mặc định loai là 'nhu_cau_ca' khi không truyền loai_luat."""
    draft = propose({"n": 3})
    assert draft is not None
    assert draft.loai == "nhu_cau_ca"


def test_propose_custom_loai() -> None:
    """Sử dụng loại luật tùy chỉnh khi loai_luat='ghep_ky_nang'."""
    draft = propose({"n": 3, "loai_luat": "ghep_ky_nang"})
    assert draft is not None
    assert draft.loai == "ghep_ky_nang"


def test_propose_output_passes_vf_rule() -> None:
    """Kết quả đề xuất hợp lệ khi được kiểm tra qua cổng VF-RULE."""
    mau = {"n": 3, "bang_chung": ["bc1", "bc2", "bc3"]}
    draft = propose(mau)
    assert draft is not None
    res = validate_rule(asdict(draft))
    assert res.passed is True
