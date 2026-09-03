"""AG-RULE là agent thuần: chỉ diễn đạt lại tín hiệu thật, không bịa luật.

Hợp đồng: lớp điều phối suy luật tất định từ lần sửa thật
(``ca_playbook.derive.derive_rule_from_edits``) rồi truyền vào ``goi_y``.
Không có ``goi_y`` và không có LLM dùng được thì ``propose`` trả ``None``.
"""

from __future__ import annotations

from dataclasses import asdict

from ca_agents.ag_rule.extract import RuleDraft, propose
from ca_gates.vf_rule import validate_rule


def _goi_y(**ghi_de: object) -> dict[str, object]:
    """Gợi ý tất định mẫu, cùng hình dạng derive_rule_from_edits trả về."""
    base: dict[str, object] = {
        "cau": "Thứ năm ca sáng vị trí kho cần ít nhất 3 người trong ca.",
        "loai": "nhu_cau_ca",
        "dieu_kien": {"thu": "T5", "khung": "sang", "vi_tri": "kho", "so_nguoi": 3},
        "bang_chung": ["bc1", "bc2", "bc3"],
    }
    base.update(ghi_de)
    return base


def test_propose_rejects_low_frequency() -> None:
    """Từ chối đề xuất luật khi tần suất n < 3 (n=2 trả về None)."""
    mau = {"n": 2, "bang_chung": ["bc1", "bc2"]}
    assert propose(mau, goi_y=_goi_y(), mode="replay") is None


def test_propose_rejects_zero() -> None:
    """Từ chối đề xuất luật khi n=0 (trả về None)."""
    mau = {"n": 0, "bang_chung": []}
    assert propose(mau, goi_y=_goi_y(), mode="replay") is None


def test_propose_rejects_missing_n() -> None:
    """Từ chối đề xuất luật khi thiếu trường n (dict rỗng trả về None)."""
    assert propose({}, goi_y=_goi_y(), mode="replay") is None


def test_propose_khong_co_goi_y_tra_ve_none() -> None:
    """Đủ tần suất nhưng không có gợi ý tất định thì KHÔNG được bịa luật."""
    mau = {"n": 3, "bang_chung": ["bc1", "bc2", "bc3"]}
    assert propose(mau, mode="replay") is None


def test_propose_goi_y_thieu_cau_tra_ve_none() -> None:
    """Gợi ý không có câu luật thì trả None thay vì dựng câu rỗng."""
    mau = {"n": 3, "bang_chung": ["bc1", "bc2", "bc3"]}
    assert propose(mau, goi_y=_goi_y(cau="   "), mode="replay") is None


def test_propose_dung_goi_y_tat_dinh() -> None:
    """Nhận gợi ý tất định thì trả RuleDraft với độ tin cậy 0.75."""
    mau = {"n": 3, "bang_chung": ["bc1", "bc2", "bc3"]}
    draft = propose(mau, goi_y=_goi_y(), mode="replay")
    assert isinstance(draft, RuleDraft)
    assert draft.do_tin_cay == 0.75
    assert draft.cau == "Thứ năm ca sáng vị trí kho cần ít nhất 3 người trong ca."
    assert draft.dieu_kien == {"thu": "T5", "khung": "sang", "vi_tri": "kho", "so_nguoi": 3}


def test_propose_caps_bang_chung_at_four() -> None:
    """Giới hạn danh sách bằng chứng tối đa là 4 khi đầu vào có 5 phần tử."""
    mau = {"n": 5, "bang_chung": ["x1", "x2", "x3", "x4", "x5"]}
    goi_y = _goi_y(bang_chung=["bc1", "bc2", "bc3", "bc4", "bc5"])
    draft = propose(mau, goi_y=goi_y, mode="replay")
    assert draft is not None
    assert draft.bang_chung == ["bc1", "bc2", "bc3", "bc4"]


def test_propose_bang_chung_lay_tu_mau_khi_goi_y_thieu() -> None:
    """Gợi ý không kèm bằng chứng thì lấy bằng chứng của mẫu."""
    mau = {"n": 3, "bang_chung": ["m1", "m2", "m3"]}
    draft = propose(mau, goi_y=_goi_y(bang_chung=[]), mode="replay")
    assert draft is not None
    assert draft.bang_chung == ["m1", "m2", "m3"]


def test_propose_default_loai() -> None:
    """Mặc định loai là 'nhu_cau_ca' khi cả gợi ý và mẫu đều không nêu loại."""
    goi_y = _goi_y()
    goi_y.pop("loai")
    draft = propose({"n": 3, "bang_chung": ["bc1", "bc2", "bc3"]}, goi_y=goi_y, mode="replay")
    assert draft is not None
    assert draft.loai == "nhu_cau_ca"


def test_propose_loai_theo_mau_khi_goi_y_thieu() -> None:
    """Lấy loai_luat của mẫu khi gợi ý không nêu loại."""
    goi_y = _goi_y()
    goi_y.pop("loai")
    mau = {"n": 3, "loai_luat": "ghep_ky_nang", "bang_chung": ["bc1", "bc2", "bc3"]}
    draft = propose(mau, goi_y=goi_y, mode="replay")
    assert draft is not None
    assert draft.loai == "ghep_ky_nang"


def test_propose_custom_loai() -> None:
    """Sử dụng loại luật tùy chỉnh khi gợi ý nêu loai='ghep_ky_nang'."""
    mau = {"n": 3, "bang_chung": ["bc1", "bc2", "bc3"]}
    goi_y = _goi_y(
        loai="ghep_ky_nang",
        dieu_kien={"thu": "T7", "khung": "chieu", "thang_kinh_nghiem": 6},
    )
    draft = propose(mau, goi_y=goi_y, mode="replay")
    assert draft is not None
    assert draft.loai == "ghep_ky_nang"


def test_propose_loc_truong_dieu_kien_la() -> None:
    """Bỏ khóa dieu_kien không nằm trong hợp đồng trước khi xuống cổng VF."""
    mau = {"n": 3, "bang_chung": ["bc1", "bc2", "bc3"]}
    goi_y = _goi_y(dieu_kien={"thu": "T5", "nhan_vien": "nv_03", "bia_dat": True})
    draft = propose(mau, goi_y=goi_y, mode="replay")
    assert draft is not None
    assert draft.dieu_kien == {"thu": "T5"}


def test_propose_output_passes_vf_rule() -> None:
    """Kết quả đề xuất hợp lệ khi được kiểm tra qua cổng VF-RULE."""
    mau = {"n": 3, "bang_chung": ["bc1", "bc2", "bc3"]}
    draft = propose(mau, goi_y=_goi_y(), mode="replay")
    assert draft is not None
    res = validate_rule(asdict(draft))
    assert res.passed is True
