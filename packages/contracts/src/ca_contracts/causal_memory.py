"""Hợp đồng dữ liệu — Causal Memory (Self-Explaining System).

Nguồn: `plans/260918-y-tuong-dot-pha-nho.md` mục 3.

ADR-003 (contracts-first): module này phải tồn tại và có unit test validate TRƯỚC
khi bất kỳ logic nghiệp vụ nào của `ag_explain` causal memory được viết.

ADR-002 (tất định): câu trả lời "tại sao" được dựng từ dữ liệu thật (audit trace,
playbook, solver) — không LLM, không bịa. Độ chính xác 100% từ dữ liệu.

ADR-008 (con người quyết định): causal memory chỉ ĐỌC và giải thích, không thay
đổi gì.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class CausalNodeType(StrEnum):
    """Loại nút trong chuỗi nhân quả."""

    SU_KIEN = "su_kien"          # sự kiện (phàn nàn, doanh thu cao)
    QUYET_DINH = "quyet_dinh"    # quyết định (duyệt luật)
    LUAT = "luat"                # luật (luat_pha_che_toi)
    KET_QUA = "ket_qua"          # kết quả (thời gian chờ giảm 22%)


class CausalNode(BaseModel):
    """Một nút trong chuỗi nhân quả."""

    node_id: str
    loai: CausalNodeType
    mo_ta: str
    thoi_gian: str = ""
    nguon: str = ""  # audit / playbook / solver / store


class CausalLink(BaseModel):
    """Liên kết nhân quả giữa hai nút (from → to)."""

    from_id: str
    to_id: str
    ly_do: str = ""


class CausalChain(BaseModel):
    """Chuỗi nhân quả hoàn chỉnh cho một câu hỏi "tại sao"."""

    chain_id: str
    cau_hoi: str
    nodes: list[CausalNode] = Field(default_factory=list)
    links: list[CausalLink] = Field(default_factory=list)
    ket_luan: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)