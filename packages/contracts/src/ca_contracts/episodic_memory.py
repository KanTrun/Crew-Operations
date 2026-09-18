"""Hợp đồng dữ liệu — Episodic Memory & Reflection.

Nguồn: `plans/260918-y-tuong-dot-pha-nho.md` mục 4 (CoALA, arXiv:2309.02427).

ADR-003 (contracts-first): module này phải tồn tại và có unit test validate TRƯỚC
khi bất kỳ logic nghiệp vụ nào được viết.

ADR-002 (tất định): suy ngẫm (reflection) dựng từ dữ liệu thật (episode), không LLM.

ADR-008 (con người quyết định): episodic memory chỉ ĐỌC + suy ngẫm, không thay đổi gì.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EpisodeType(StrEnum):
    """Loại tình huống được ghi nhớ."""

    PHAN_NAN = "phan_nan"
    DOANH_THU_CAO = "doanh_thu_cao"
    DOANH_THU_THAP = "doanh_thu_thap"
    SU_CO = "su_co"
    KHEN_NGOI = "khen_ngoi"


class Episode(BaseModel):
    """Một tình huống cụ thể được ghi nhớ (episodic memory)."""

    episode_id: str
    loai: EpisodeType
    thoi_gian: str
    mo_ta: str
    nhan_vien: str = ""
    ca: str = ""
    chi_tiet: dict[str, object] = Field(default_factory=dict)


class Reflection(BaseModel):
    """Suy ngẫm nguyên nhân gốc từ một nhóm episode."""

    reflection_id: str
    episode_ids: list[str] = Field(default_factory=list)
    nguyen_nhan_goc: str
    de_xuat: str = ""
    do_tin_cay: float = Field(ge=0.0, le=1.0, default=0.8)
    generated_at: datetime = Field(default_factory=datetime.now)


class ReflectionResult(BaseModel):
    """Kết quả suy ngẫm cho một câu hỏi."""

    cau_hoi: str
    episodes: list[Episode] = Field(default_factory=list)
    reflections: list[Reflection] = Field(default_factory=list)
    ket_luan: str = ""