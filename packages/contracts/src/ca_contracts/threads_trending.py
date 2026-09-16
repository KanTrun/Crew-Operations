"""Contract cho bảng "Trending Now" trên Threads (plan 260914-1015 mục 4.1).

ADR-003 — contract tồn tại TRƯỚC logic nghiệp vụ. Mỗi chủ đề xu hướng thu thập
được từ threads.net/search phải đưa về đúng cấu trúc này trước khi vào radar.

Khác với `TrendItem` (dataclass hiển thị của AG-TREND), contract này là
hợp đồng DỮ LIỆU chuẩn hoá: giữ nguyên `volume_raw` (chuỗi gốc trên UI) cùng
`volume_count` (số đã quy đổi) để đối chiếu được khi Meta đổi định dạng hiển thị.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Lifecycle = Literal["NEW", "RISING", "PEAKING", "FADING"]


class ThreadsTrendingItem(BaseModel):
    """Một chủ đề trong bảng Trending Now của Threads Việt Nam."""

    platform: Literal["threads"] = Field(default="threads", description="Nền tảng nguồn")
    topic_id: str = Field(min_length=1, description="Mã băm duy nhất từ tiêu đề chuẩn hoá")
    rank: int = Field(ge=1, le=100, description="Thứ hạng trên bảng Trending Now")
    title: str = Field(min_length=1, description="Tiêu đề chủ đề")
    summary: str = Field(default="", description="Tóm tắt ngữ cảnh do Meta sinh")
    volume_raw: str = Field(default="", description="Số liệu nguyên gốc trên UI, vd '9K posts'")
    volume_count: int = Field(ge=0, description="Số bài viết đã quy đổi, vd 9000")
    thumbnail_url: str = Field(default="", description="Ảnh đại diện chủ đề (nếu có)")
    search_url: str = Field(min_length=1, description="Link tra cứu trực tiếp")
    lifecycle: Lifecycle = Field(description="NEW | RISING | PEAKING | FADING")
    scraped_at: datetime = Field(description="Thời điểm ghi nhận")

    @field_validator("title", "topic_id", "search_url")
    @classmethod
    def _strip_whitespace(cls, v: str) -> str:
        return v.strip()


class ThreadsTrendingSnapshot(BaseModel):
    """Một lần chụp toàn bộ bảng Trending Now (một chu kỳ cào)."""

    items: list[ThreadsTrendingItem] = Field(default_factory=list)
    scraped_at: datetime = Field(description="Thời điểm chụp snapshot")
    source_url: str = Field(default="https://www.threads.net/search")

    @field_validator("items")
    @classmethod
    def _ranks_unique_and_sorted(cls, v: list[ThreadsTrendingItem]) -> list[ThreadsTrendingItem]:
        ranks = [it.rank for it in v]
        if len(ranks) != len(set(ranks)):
            raise ValueError("rank bị trùng trong một snapshot")
        return v
