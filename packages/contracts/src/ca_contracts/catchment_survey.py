"""Hợp đồng dữ liệu cho khảo sát giá và đối thủ trong bán kính (Catchment Price Radar).

Tuân thủ ADR-003: contracts-first, pydantic BaseModel, schema chặt chẽ.
Hỗ trợ:
- Khảo sát giá tại chỗ (Dine-in Vision OCR) và giá trên sàn (Delivery).
- Phân tích món thay thế liên ngành (Share of Stomach Substitute Matrix).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ChannelMode = Literal["dine_in_vision", "delivery_platform", "hybrid"]


class DishItem(BaseModel):
    """Một món ăn trong menu đối thủ."""

    name: str = Field(description="Tên món ăn hoặc thức uống")
    price: int = Field(ge=0, description="Giá niêm yết (VNĐ)")
    is_bestseller: bool = Field(default=False, description="Món bán chạy nhất/signature")
    category: str = Field(default="", description="Danh mục món (vd: Cơm, Bún, Cà phê, Món thay thế)")
    source_type: str = Field(default="delivery", description="Nguồn giá: 'dine_in_ocr' hoặc 'delivery'")


class StoreCandidate(BaseModel):
    """Dữ liệu thô của một quán thu thập từ nền tảng delivery hoặc Google Maps."""

    id: str = Field(default="", description="Mã định danh quán")
    place_id: str = Field(default="", description="Alias place_id theo chuẩn SerpApi / Google Maps")
    data_id: str = Field(default="", description="data_id theo chuẩn SerpApi — bắt buộc cho google_maps_photos")
    name: str = Field(description="Tên quán")
    address: str = Field(default="", description="Địa chỉ quán")
    lat: float = Field(default=0.0, description="Tọa độ vĩ độ GPS")
    lng: float = Field(default=0.0, description="Tọa độ kinh độ GPS")
    distance_km: float = Field(default=0.0, ge=0.0, description="Khoảng cách tính từ vị trí khảo sát (km)")
    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Điểm đánh giá sao (thang 5.0)")
    review_count: int = Field(default=0, ge=0, description="Số lượng lượt đánh giá")
    is_favorite: bool = Field(default=False, description="Nhãn quán yêu thích / đối tác uy tín")
    sold_count_text: str = Field(default="", description="Text hiển thị lượt bán (vd: '1k+ đã bán')")
    url: str = Field(default="", description="Đường dẫn đến trang quán")
    menu_image_urls: list[str] = Field(default_factory=list, description="Danh sách URL ảnh menu thực tế")
    dishes: list[DishItem] = Field(default_factory=list, description="Danh sách món trong menu")
    data_source: Literal["serpapi", "camoufox", "cache", "delivery_platform"] = Field(
        default="camoufox", description="Nguồn thu thập dữ liệu: 'serpapi' | 'camoufox' | 'cache' | 'delivery_platform'"
    )
    fetched_at: str | None = Field(default=None, description="Thời điểm thu thập ISO 8601")

    @model_validator(mode="before")
    @classmethod
    def _sync_ids(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "place_id" in data and not data.get("id"):
                data["id"] = data["place_id"]
            elif "id" in data and not data.get("place_id"):
                data["place_id"] = data["id"]
        return data


class ValidatedStore(BaseModel):
    """Quán đối thủ đã vượt qua bộ lọc kép (Dual-Gate) kiểm chứng thị trường."""

    id: str
    name: str
    address: str = ""
    distance_km: float
    rating: float
    review_count: int
    bayesian_rating: float = Field(description="Điểm đánh giá Bayes (Weighted Rating)")
    distance_weight: float = Field(description="Trọng số suy giảm theo khoảng cách")
    is_favorite: bool = False
    url: str = ""
    has_menu_images: bool = False


class PriceDistribution(BaseModel):
    """Thống kê phân bố giá có trọng số (Volume-Weighted Price Distribution)."""

    sample_size: int = Field(ge=0, description="Số lượng món ăn hợp lệ được đưa vào tập mẫu")
    min_price: int = Field(ge=0, description="Giá thấp nhất (VNĐ)")
    max_price: int = Field(ge=0, description="Giá cao nhất (VNĐ)")
    median_price: int = Field(ge=0, description="Giá trung vị P50 (VNĐ)")
    p25_price: int = Field(ge=0, description="Phân vị 25% - Ngưỡng giá phổ thông (VNĐ)")
    p75_price: int = Field(ge=0, description="Phân vị 75% - Ngưỡng giá cao cấp (VNĐ)")
    volume_weighted_mean: int = Field(ge=0, description="Giá trung bình có trọng số lượt bán/đánh giá (VNĐ)")
    sweet_spot_range: list[int] = Field(
        min_length=2,
        max_length=2,
        description="Vùng giá ngọt ngào (Sweet Spot) tập trung nhiều khách nhất [min, max]",
    )


class TopCompetitorSignature(BaseModel):
    """Món tiêu biểu của quán đối thủ hàng đầu."""

    store_name: str
    dish_name: str
    price: int
    is_bestseller: bool = True
    category: str = ""


class MenuSnapshot(BaseModel):
    """Thông tin ảnh menu thu thập được và số món bóc tách thành công."""

    store_id: str
    store_name: str
    image_url: str
    source: str = "google_maps"
    extracted_dishes_count: int = 0


class SubstituteCategoryStats(BaseModel):
    """Thống kê phổ giá của một danh mục món thay thế (vd: Bún, Phở, Hủ tiếu)."""

    category_name: str
    dishes_count: int
    median_price: int
    min_price: int
    max_price: int
    p25_price: int
    p75_price: int
    sweet_spot_range: list[int]


class SubstitutePriceComparison(BaseModel):
    """Bảng so sánh đối chiếu giữa món chính và các món thay thế liên ngành."""

    core_category_name: str
    core_price_distribution: PriceDistribution
    substitute_categories: list[SubstituteCategoryStats]
    area_meal_budget_index: int = Field(
        description="Chỉ số trần ngân sách bữa ăn của khu vực (Area Meal Budget Index - AMBI)"
    )


class CatchmentSurveyRequest(BaseModel):
    """Yêu cầu khảo sát giá theo bán kính."""

    latitude: float = Field(ge=-90.0, le=90.0, description="Tọa độ vĩ độ của quán")
    longitude: float = Field(ge=-180.0, le=180.0, description="Tọa độ kinh độ của quán")
    address: str = Field(default="", description="Địa chỉ dạng text để hiển thị")
    radius_km: float = Field(default=3.0, ge=0.5, le=15.0, description="Bán kính khảo sát (km)")
    category_keyword: str = Field(description="Từ khóa ngành hàng (vd: cơm tấm, cà phê, bún bò)")
    min_reviews: int = Field(default=50, ge=10, description="Ngưỡng đánh giá tối thiểu (Gate 1)")
    min_rating: float = Field(default=4.2, ge=1.0, le=5.0, description="Ngưỡng điểm sao tối thiểu (Gate 2)")
    only_bestsellers: bool = Field(
        default=True,
        description="Chỉ lấy món bán chạy/signature thay vì toàn bộ menu",
    )
    channel_mode: ChannelMode = Field(
        default="dine_in_vision",
        description="Chế độ khảo sát: 'dine_in_vision' (quét menu tại quán), 'delivery_platform' (trên sàn), hoặc 'hybrid'",
    )
    include_substitutes: bool = Field(
        default=True,
        description="Tự động khảo sát các món thay thế cùng nhu cầu (vd: Cơm kèm Bún/Phở/Hủ tiếu)",
    )
    max_menu_images_per_store: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Số lượng ảnh menu tối đa quét trên mỗi quán để tối ưu token Vision AI",
    )


class CatchmentSurveyResponse(BaseModel):
    """Kết quả hoàn chỉnh của một cuộc khảo sát giá thị trường."""

    request: CatchmentSurveyRequest
    total_scanned_stores: int
    validated_stores_count: int
    disqualified_stores_count: int
    validated_stores: list[ValidatedStore]
    price_distribution: PriceDistribution
    top_competitor_signatures: list[TopCompetitorSignature]
    substitute_comparison: SubstitutePriceComparison | None = None
    menu_snapshots: list[MenuSnapshot] = Field(default_factory=list)
    market_insight: str
