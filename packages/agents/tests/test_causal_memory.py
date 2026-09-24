# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit test cho Causal Memory (Self-Explaining System) — plan 260918 mục 3.

ADR-002: câu trả lời "tại sao" tất định, từ dữ liệu thật, không LLM.
"""

from __future__ import annotations

from ca_agents.ag_explain import build_causal_chain
from ca_contracts.causal_memory import CausalNodeType


def test_build_causal_chain_with_luat() -> None:
    luat_list = [
        {
            "id": "luat_pha_che_toi",
            "cau": "Tăng 1 pha chế ca tối T6, T7",
            "bang_chung": ["phàn nàn chờ lâu", "phàn nàn chờ lâu", "phàn nàn chờ lâu"],
        }
    ]
    audit_list = [
        {"entity_id": "luat_pha_che_toi", "hanh_dong": "duyet", "actor": "chu_quan", "luc": "2026-09-12"}
    ]
    ket_qua_list = [{"mo_ta": "thời gian chờ giảm 22%"}]

    chain = build_causal_chain(
        cau_hoi="Tại sao ca tối T6 có 2 pha chế?",
        luat_list=luat_list,
        audit_list=audit_list,
        ket_qua_list=ket_qua_list,
    )

    assert chain.cau_hoi == "Tại sao ca tối T6 có 2 pha chế?"
    # Có nút luật
    luat_nodes = [n for n in chain.nodes if n.loai == CausalNodeType.LUAT]
    assert len(luat_nodes) == 1
    assert luat_nodes[0].mo_ta == "Tăng 1 pha chế ca tối T6, T7"
    # Có nút quyết định
    quyet_dinh_nodes = [n for n in chain.nodes if n.loai == CausalNodeType.QUYET_DINH]
    assert len(quyet_dinh_nodes) == 1
    # Có nút kết quả
    ket_qua_nodes = [n for n in chain.nodes if n.loai == CausalNodeType.KET_QUA]
    assert len(ket_qua_nodes) == 1
    # Kết luận không rỗng
    assert chain.ket_luan != ""


def test_build_causal_chain_empty() -> None:
    chain = build_causal_chain(
        cau_hoi="Tại sao?",
        luat_list=[],
        audit_list=[],
        ket_qua_list=[],
    )
    assert chain.nodes == []
    assert "Không tìm thấy" in chain.ket_luan


def test_build_causal_chain_links() -> None:
    luat_list = [{"id": "luat_1", "cau": "Luật 1", "bang_chung": ["bc1"]}]
    audit_list = [{"entity_id": "luat_1", "hanh_dong": "duyet", "actor": "ql"}]
    ket_qua_list = [{"mo_ta": "kết quả tốt"}]

    chain = build_causal_chain("Tại sao?", luat_list, audit_list, ket_qua_list)
    # Có ít nhất 1 liên kết
    assert len(chain.links) >= 1