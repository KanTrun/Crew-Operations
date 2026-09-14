"""Data contract cho xu hướng F&B từ Google Trends / SerpApi (ADR-003).

Tuân thủ kế hoạch 260913-2045-serpapi-integration v2.0 Section 4.3.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TrendItem(BaseModel):
    """Mục xu hướng F&B chuẩn hóa từ Google Trends / SerpApi."""

    keyword: str = Field(description="Từ khóa xu hướng F&B")
    interest_score: int = Field(ge=0, le=100, description="Điểm quan tâm Google Trends (0-100)")
    nguon_goc: Literal["google_vn"] = Field(default="google_vn", description="Nguồn dữ liệu")
    danh_muc: Literal["am_thuc_fnb"] = Field(default="am_thuc_fnb", description="Ngành hàng")
    vong_doi: Literal["moi_nhu", "dang_dinh", "thoai_trao"] = Field(
        description="Giai đoạn vòng đời: moi_nhu | dang_dinh | thoai_trao"
    )
    is_breakout: bool = Field(default=False, description="Đang bùng nổ đột biến (>5000% search growth)")
    window: Literal["now 7-d", "today 1-m"] = Field(default="now 7-d", description="Khung thời gian Google Trends")
    fetched_at: datetime = Field(description="Thời điểm thu thập dữ liệu")
