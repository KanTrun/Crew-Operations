# Kế hoạch — Hệ thống Khảo sát Giá & Định vị Thị trường F&B theo Bán kính (Catchment Pricing & Market Radar)

> **Mã kế hoạch:** `260913-1455-khao-sat-gia-fb-online-dinein-substitutes`  
> **Ngày lập:** 2026-09-13 · **Phiên bản:** v1.0 (Bản hoàn chỉnh)  
> **Tuân thủ chuẩn Nhịp Quán:**  
> - **ADR-002:** Điều phối tất định (Mọi chỉ số $P_{25}, P_{50}, P_{75}$, Sweet Spot, AMBI tính bằng công thức toán học thuần túy, không để LLM đoán mò số liệu).  
> - **ADR-003:** Contracts-first (Định nghĩa schema và hợp đồng dữ liệu trước khi triển khai).  
> - **ADR-008:** Agent trích xuất dữ liệu khách quan — Con người (Chủ quán) là người ra quyết định giá cuối cùng.  
>
> **Vùng sở hữu:** C (Agents: `ag_pricing`, `sources`) + B (API: `ca_api`) + D (Web: UI Khảo sát thị trường).

---

## MỤC LỤC

1. [Phần I — Bối cảnh & Nghiên cứu Nghiệp vụ F&B Chuyên sâu](#phần-i--bối-cảnh--nghiên-cứu-nghiệp-vụ-fb-chuyên-sâu)
   - 1.1. Thực tế phân tầng: Giá trên sàn (Delivery) vs Giá tại quầy (Dine-in)
   - 1.2. Lý thuyết "Chiếc dạ dày" (Share of Stomach) & Nhu cầu cốt lõi (Jobs-to-be-Done)
   - 1.3. Chỉ số "Trần ngân sách bữa ăn khu vực" (Area Meal Budget Index - AMBI)
   - 1.4. Bộ lọc kiểm chứng thị trường (Dual-Gate Qualification & Bayesian Rating)
2. [Phần II — Kiến trúc Giải pháp & Ba Phân hệ Chức năng](#phần-ii--kiến-trúc-giải-pháp--ba-phân-hệ-chức-năng)
   - 2.1. Phân hệ 1: Khảo sát Bán Online (Delivery Radar qua ShopeeFood)
   - 2.2. Phân hệ 2: Khảo sát Bán Tại Chỗ (Dine-in Vision Radar qua Google Maps)
   - 2.3. Phân hệ 3: Ma trận Sản phẩm Thay thế (Substitute Matrix Engine)
3. [Phần III — Hợp đồng Dữ liệu & Schema Chuẩn (Contracts-First)](#phần-iii--hợp-đồng-dữ-liệu--schema-chuẩn-contracts-first)
4. [Phần IV — Quy trình Trải nghiệm Người dùng & Giao diện (UI/UX)](#phần-iv--quy-trình-trải-nghiệm-người-dùng--giao-diện-uiux)
5. [Phần V — Kế hoạch Triển khai theo Từng Giai đoạn (Phased Roadmap)](#phần-v--kế-hoạch-triển-khai-theo-từng-giai-đoạn-phased-roadmap)
6. [Phần VI — Ma trận Rủi ro & Biện pháp Kiểm soát (Risk & Mitigation)](#phần-vi--ma-trận-rủi-ro--biện-pháp-kiểm-soát-risk--mitigation)

---

# PHẦN I — BỐI CẢNH & NGHIÊN CỨU NGHIỆP VỤ F&B CHUYÊN SÂU

## 1.1. Thực tế phân tầng: Giá trên sàn (Delivery) vs Giá tại quầy (Dine-in)

Trong kinh doanh ẩm thực tại Việt Nam, **giá bán mang về/đặt qua app không bao giờ đại diện cho giá bán tại chỗ**:

```
                       [CÙNG MỘT MÓN ĂN: CƠM SƯỜN NƯỚNG]
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
   [BÁN TẠI QUẦN (DINE-IN)]                            [BÁN TRÊN SÀN (DELIVERY)]
   • Giá niêm yết: 35.000đ                            • Giá niêm yết: 44.000đ (+25%)
   • Chi phí mặt bằng, phục vụ, máy lạnh              • Chiết khấu sàn: 20% - 27.5%
   • Chén dĩa rửa lại được                            • Hộp xốp, túi ni lông, quai: ~3.000đ
   • Khách đi bộ/xe máy trong 500m - 1.5km            • Shipper giao trong 3km - 7km
```

* **Vấn đề cốt tử:** Nếu một chủ quán mở quán cơm trưa/quán cà phê có chỗ ngồi, nhưng lại dùng công cụ cào dữ liệu từ ShopeeFood để làm mốc định giá, menu in ra sẽ bị **đắt hơn từ 15% – 30% so với toàn bộ các quán ngồi lại lân cận**. Khách vãng lai và dân văn phòng xung quanh sẽ chỉ ăn một lần rồi bỏ đi.
* **Ngược lại:** Nếu chủ quán mở bếp Cloud (chỉ bán online), nhưng lại lấy giá tại bàn của đối thủ làm giá niêm yết trên app, quán sẽ bị **lỗ nặng** sau khi sàn trừ phí hoa hồng và chi phí bao bì.
* $\rightarrow$ **Kết luận:** Hệ thống bắt buộc phải **tách biệt rõ ràng 2 kênh khảo sát** hoặc cung cấp cơ chế quy đổi chính xác.

---

## 1.2. Lý thuyết "Chiếc dạ dày" (Share of Stomach) & Nhu cầu cốt lõi (Jobs-to-be-Done)

Khách hàng khi đi ăn không đưa ra quyết định theo danh mục phân loại món ăn, mà họ đưa ra quyết định dựa trên **Nhu cầu cốt lõi tại thời điểm đó (Job-to-be-Done)**:

### Ví dụ điển hình: Khảo sát ngành "Cơm trưa"
Khi một nhân viên văn phòng đi ăn trưa lúc 12h00:
* Câu hỏi của họ: *"Trưa nay ăn gì cho no, sạch và dưới 45.000đ?"*
* Các lựa chọn xuất hiện trong đầu họ:
  * Cơm sườn bì chả: **40.000đ**
  * Bún bò Huế: **38.000đ**
  * Phở bò: **40.000đ**
  * Hủ tiếu Nam Vang: **35.000đ**
  * Bánh mì chảo: **35.000đ**
  * Bún đậu mắm tôm: **42.000đ**

Nếu quán cơm định giá **48.000đ** và tự tin rằng quán cơm đối thủ cách đó 500m bán 50.000đ, nhưng quán bún bò và quán phở ngay bên cạnh bán **38.000đ** với máy lạnh mát rượi và đồ ăn đầy đặn, thì **khách hàng sẽ bỏ sang ăn bún bò**.

```
                           [SHARE OF STOMACH]
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
   [Nhóm Cơm (Core)]      [Nhóm Sợi Nước (Sub 1)]    [Nhóm Tiện Lợi (Sub 2)]
   • Cơm tấm, cơm gà      • Bún bò, bún chả          • Bánh mì chảo, bánh mì que
   • Cơm văn phòng        • Phở bò, phở gà           • Bún đậu mắm tôm
   • Cơm thố, cơm niêu    • Hủ tiếu, bánh canh       • Xôi mặn, bánh cuốn
```

### Bảng Ma trận Món thay thế (Substitute Matrix) cho 4 nhóm ngành chính:

| Ngành hàng mục tiêu | Nhu cầu cốt lõi (Job-to-be-Done) | Danh mục món thay thế trực tiếp |
|---|---|---|
| **Cơm (Cơm tấm, cơm trưa, cơm gà)** | Bữa trưa nhanh, no bụng, năng lượng làm việc | Bún bò, Bún chả, Bún thịt nướng, Phở, Hủ tiếu, Bánh canh, Bánh mì chảo |
| **Bún / Phở / Hủ tiếu** | Bữa sáng hoặc trưa dạng món nước, dễ nuốt | Cơm tấm, Bánh cuốn, Bánh mì, Miến gà, Mì Quảng |
| **Cà phê (Cà phê muối, sữa, đen)** | Tỉnh táo, nạp caffeine, ngồi làm việc, gặp gỡ | Trà trái cây (đào, sen, vải), Trà sữa, Nước ép/sinh tố, Cacao đá |
| **Trà sữa / Trà giải khát** | Thưởng thức, giải nhiệt, tụ tập bạn bè, ăn xế | Cà phê máy/cà phê muối, Chè, Kem tươi, Nước ép |

---

## 1.3. Chỉ số "Trần ngân sách bữa ăn khu vực" (Area Meal Budget Index - AMBI)

Để giúp chủ quán không bị "ảo tưởng giá", hệ thống xây dựng chỉ số định lượng **AMBI**:

$$\text{AMBI} = \alpha \cdot \text{Median}_{\text{Core}} + (1 - \alpha) \cdot \overline{\text{Median}}_{\text{Substitutes}}$$
*(với $\alpha = 0.5$ — cân bằng giữa món chính và các món thay thế).*

* **Ý nghĩa:** AMBI phản ánh **ngưỡng chi trả tâm lý cao nhất** mà đa số người dân/dân văn phòng trong khu vực chấp nhận chi cho một bữa ăn trưa bình thường mà không cần đắn đo.
* **Quy tắc cảnh báo:**
  * Nếu $\text{Giá quán dự kiến} \le \text{AMBI}$: Điểm giá an toàn, dễ kéo khách đông, tỷ lệ quay lại cao.
  * Nếu $\text{Giá quán dự kiến} > \text{AMBI} + 20\%$: Vùng giá rủi ro cao. Bắt buộc quán phải có điểm cộng vượt trội (máy lạnh, không gian decor đẹp, chỗ đậu ô tô, nước ngọt miễn phí).

---

## 1.4. Bộ lọc kiểm chứng thị trường (Dual-Gate Qualification & Bayesian Rating)

Hệ thống **tuyệt đối không đưa vào phân tích** các quán sau:
1. **Quán ma / Bếp zombie:** Đăng ký trên app nhưng hầu như không có đơn, định giá tùy tiện.
2. **Quán mới mở vài ngày:** Có 2–3 đánh giá 5.0★ từ người quen/nhân viên (Bẫy mẫu nhỏ - Sample Size Trap).
3. **Quán phá giá chất lượng kém:** Bán đồ ăn giá cực rẻ (12k-15k) nhưng điểm đánh giá 2.5★ – 3.2★ do mất vệ sinh, phục vụ tệ (Thị trường quả chanh - Lemon Market).

### Bộ lọc kép (Dual-Gate Filter):
* **Gate 1 — Ngưỡng quy mô (Volume Gate):** $v \ge 50$ đánh giá (hoặc có huy hiệu "Quán yêu thích" / "Đã bán 1k+").
* **Gate 2 — Ngưỡng chất lượng (Quality Gate):** Điểm đánh giá gốc $R \ge 4.2★$ VÀ Điểm Bayes Weighted Rating $WR \ge 4.0★$.

### Công thức xếp hạng Bayes (IMDB Weighted Rating):
$$\text{WR} = \left( \frac{v}{v + m} \right) \cdot R + \left( \frac{m}{v + m} \right) \cdot C$$
*(với $m = 50$ là ngưỡng đánh giá tối thiểu, $C = 4.2$ là điểm kỳ vọng trung bình toàn thị trường).*

---

# PHẦN II — KIẾN TRÚC GIẢI PHÁP & BA PHÂN HỆ CHỨC NĂNG

```
                             [YÊU CẦU KHẢO SÁT]
            Tọa độ quán + Bán kính (1km - 5km) + Ngành hàng ("Cơm")
                                     │
      ┌──────────────────────────────┴──────────────────────────────┐
      ▼                                                             ▼
[KÊNH BÁN ONLINE (DELIVERY)]                          [KÊNH BÁN TẠI CHỖ (DINE-IN)]
ShopeeFood Crawler (Camoufox)                         Google Maps Place Scraper
      │                                                             │
Lọc Dual-Gate: >= 50 reviews, >= 4.2★                 Lấy ảnh album "Thực đơn / Menu"
      │                                                             │
Bóc tách giá Best Sellers trên sàn                    Multimodal AI Vision (Gemini OCR)
      │                                                             │
      │                                               Trích xuất giá bảng hiệu tại quán
      │                                                             │
      └──────────────────────────────┬──────────────────────────────┘
                                     │
                                     ▼
                   [MA TRẬN SẢN PHẨM THAY THẾ (SUBSTITUTE)]
                   Quét song song: Bún, Phở, Hủ tiếu, Bánh mì
                                     │
                                     ▼
                   [ENGINE THỐNG KÊ PHÂN VỊ CÓ TRỌNG SỐ]
                   • Phổ giá Online vs Tại Chỗ (P25 - P50 - P75)
                   • Sweet Spot thị trường (Vùng giá vàng)
                   • Chỉ số trần ngân sách khu vực (AMBI)
                                     │
                                     ▼
                   [BÁO CÁO ĐỊNH VỊ CHIẾN LƯỢC CHO CHỦ QUÁN]
```

---

## 2.1. Phân hệ 1: Khảo sát Bán Online (Delivery Radar qua ShopeeFood)
* **Mục tiêu:** Xác định phổ giá cạnh tranh trên các ứng dụng giao thức ăn trong bán kính **3km – 7km**.
* **Công nghệ thực thi:**
  * Dùng **Camoufox** (Firefox spoofing C++/Rust) mở trang tìm kiếm ShopeeFood theo tọa độ `lat/long` của quán.
  * Chặn bắt (intercept) trực tiếp gói tin JSON nội bộ `/api/delivery/get_browse_dishes` để lấy dữ liệu có cấu trúc.
* **Dữ liệu trích xuất:**
  * Tên quán, khoảng cách giao hàng, số lượt bán hiển thị (`sold_count_text`).
  * Danh mục món ăn, giá bán trên app, đánh dấu món `is_bestseller`.
* **Output:**
  * Phổ giá Online: $P_{25}^{\text{online}}, P_{50}^{\text{online}}, P_{75}^{\text{online}}$.
  * Danh sách Top 5 món bán chạy nhất của các đối thủ dẫn đầu sàn.

---

## 2.2. Phân hệ 2: Khảo sát Bán Tại Chỗ (Dine-in Vision Radar qua Google Maps)
* **Mục tiêu:** Bóc tách giá bán thực tế in trên menu giấy và bảng giá treo tường của các quán ăn có chỗ ngồi trong bán kính **500m – 2km**.
* **Công nghệ thực thi:**
  1. **Google Maps Place Scraper:** Camoufox tìm kiếm các địa điểm ăn uống lân cận trên Google Maps, lọc các quán có lượng check-in và review cao.
  2. **Thu thập ảnh Menu:** Mở album ảnh có nhãn "Thực đơn / Menu", chọn lọc tối đa **2–3 bức ảnh rõ nét nhất** chụp cuốn menu hoặc bảng giá.
  3. **Multimodal AI Vision (Gemini Vision OCR):**
     * Truyền `image_bytes` vào hàm `ca_agents.llm.complete()` với prompt cấu trúc nghiêm ngặt (chế độ `json_mode=True`, `temperature=0`).
     * Nhận diện cách viết giá tiếng Việt: `"35k"`, `"35.000"`, `"35"`, `"42 ngàn"`.
     * Phân tách giá theo size (S/M/L) hoặc phần thường vs phần đặc biệt.
  4. **Cơ chế Fallback thông minh:**
     * Nếu một quán đối thủ lớn không có ảnh menu trên Google Maps, hệ thống tự động áp dụng công thức **Reverse Markup**:
       $$\text{Giá tại quán ước tính} = \text{Giá trên sàn} \times (1 - 0.20)$$
       *(đảm bảo không bỏ sót đối thủ mạnh chỉ vì thiếu ảnh)*.

---

## 2.3. Phân hệ 3: Ma trận Sản phẩm Thay thế (Substitute Matrix Engine)
* **Mục tiêu:** Đánh giá áp lực cạnh tranh liên ngành từ các lựa chọn ăn uống khác cùng giải quyết một nhu cầu.
* **Cơ chế hoạt động:**
  1. **Ánh xạ từ khóa:** Khi người dùng nhập `"cơm"`, module `substitute_matrix.py` tự động kích hoạt truy vấn bổ sung: `["bún", "phở", "hủ tiếu", "bánh mì"]`.
  2. **Tính toán phân vị độc lập:**
     * Nhóm Cơm (Core): Tính $P_{25}, P_{50}, P_{75}$.
     * Nhóm Bún/Phở (Substitutes): Tính $P_{25}, P_{50}, P_{75}$ riêng cho từng nhóm.
  3. **Xác định chỉ số AMBI:** Tổng hợp mức giá cân bằng của toàn bộ bữa trưa trong khu vực.

---

# PHẦN III — HỢP ĐỒNG DỮ LIỆU & SCHEMA CHUẨN (CONTRACTS-FIRST)

Hợp đồng dữ liệu được định nghĩa chặt chẽ trong `packages/contracts/src/ca_contracts/catchment_survey.py`:

```python
class CatchmentSurveyRequest(BaseModel):
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    address: str = ""
    radius_km: float = Field(default=3.0, ge=0.5, le=15.0)
    category_keyword: str  # Vd: "cơm tấm", "cà phê"
    min_reviews: int = Field(default=50, ge=10)
    min_rating: float = Field(default=4.2, ge=1.0, le=5.0)
    channel_mode: Literal["dine_in_vision", "delivery_platform", "hybrid"] = "dine_in_vision"
    include_substitutes: bool = True
    max_menu_images_per_store: int = Field(default=3, ge=1, le=5)

class SubstituteCategoryStats(BaseModel):
    category_name: str           # Vd: "Bún", "Phở", "Hủ tiếu"
    dishes_count: int
    median_price: int
    min_price: int
    max_price: int
    p25_price: int
    p75_price: int
    sweet_spot_range: list[int]  # [p25, p75]

class SubstitutePriceComparison(BaseModel):
    core_category_name: str
    core_price_distribution: PriceDistribution
    substitute_categories: list[SubstituteCategoryStats]
    area_meal_budget_index: int  # Chỉ số AMBI

class CatchmentSurveyResponse(BaseModel):
    request: CatchmentSurveyRequest
    total_scanned_stores: int
    validated_stores_count: int
    disqualified_stores_count: int
    validated_stores: list[ValidatedStore]
    price_distribution: PriceDistribution             # Phổ giá kênh mục tiêu
    top_competitor_signatures: list[TopCompetitorSignature]
    substitute_comparison: SubstitutePriceComparison | None = None
    menu_snapshots: list[MenuSnapshot] = []          # Bằng chứng ảnh menu đã OCR
    market_insight: str                              # Nhận định chiến lược định lượng
```

---

# PHẦN IV — QUY TRÌNH TRẢI NGHIỆM NGƯỜI DÙNG & GIAO DIỆN (UI/UX)

Giao diện khảo sát được thiết kế trực quan, phục vụ trực tiếp cho quyết định kinh doanh của chủ quán:

### 1. Màn hình Thiết lập Khảo sát (Input)
* **Bản đồ chọn vị trí:** Ghim vị trí mặt bằng quán của người dùng.
* **Thanh trượt bán kính:**
  * `1km` (Dành cho quán ăn trưa đi bộ / quán cơm bình dân).
  * `3km` (Dành cho quán cà phê, quán ăn gia đình chạy xe máy).
  * `5km - 7km` (Dành cho bán online delivery).
* **Chọn kênh khảo sát:**
  * 🔘 **Bán Tại Chỗ (Dine-in):** Quét bảng giá thực tế tại quán qua Google Maps OCR.
  * 🔘 **Bán Online (Delivery):** Quét giá bán trên ShopeeFood.
  * 🔘 **Khảo sát Song Song (Hybrid):** So sánh độ chênh giá giữa sàn và quán.
* **Checkbox tùy chọn:** `[x] Tự động phân tích món thay thế (Share of Stomach)`.

---

### 2. Màn hình Kết quả Khảo sát (Output Dashboard)

```
========================================================================================
📊 BÁO CÁO ĐỊNH VỊ GIÁ — NGÀNH: CƠM TRƯA (BÁN KÍNH 2.0 KM)
Địa chỉ khảo sát: 45 Đinh Tiên Hoàng, Phường Đa Kao, Quận 1, TP.HCM
========================================================================================

[1] ĐỐI CHIẾU GIÁ BÁN TẠI BÀN VS GIÁ BÁN ONLINE
┌──────────────────────┬──────────────────────┬──────────────────────┬────────────────┐
│ Món tiêu biểu        │ Giá tại quán (OCR)   │ Giá trên sàn (App)   │ Phí sàn độn lên│
├──────────────────────┼──────────────────────┼──────────────────────┼────────────────┤
│ Cơm sườn bì chả      │ 35.000đ – 37.000đ    │ 44.000đ – 45.000đ    │ +20% - 22%     │
│ Cơm gà xối mỡ        │ 38.000đ – 40.000đ    │ 48.000đ – 50.000đ    │ +25%           │
│ Canh khổ qua nhồi thịt│ 15.000đ             │ 22.000đ              │ +35%           │
│ Trà đá / Khăn lạnh   │ Miễn phí / 2.000đ    │ 5.000đ               │ —              │
└──────────────────────┴──────────────────────┴──────────────────────┴────────────────┘

[2] BẢN ĐỒ MÓN THAY THẾ (SHARE OF STOMACH QUANH 1KM)
• Cơm (Món chính khảo sát):  35.000đ ────────● [37.000đ] ──────── 42.000đ
• Bún bò / Bún chả:          35.000đ ───────────● [38.000đ] ───── 45.000đ
• Phở bò / Gà:               38.000đ ────────● [40.000đ] ──────── 50.000đ
• Hủ tiếu Nam Vang:          32.000đ ─────● [35.000đ] ─────────── 40.000đ
• Bánh mì chảo:              30.000đ ──● [32.000đ] ────────────── 38.000đ
----------------------------------------------------------------------------------------
👉 TRẦN NGÂN SÁCH BỮA TRƯA KHU VỰC (AMBI): 38.000 VNĐ / SUẤT

[3] KHUYẾN NGHỊ ĐỊNH VỊ CHO QUÁN:
1. Món chủ đạo (Cơm sườn): Nên chốt giá 37.000đ (bằng mức trần AMBI khu vực để hút khách).
2. Combo nâng giá trị: Thiết kế combo "Cơm sườn + Trứng ốp la + Trà tắc" giá 47.000đ.
3. Nếu mở bán thêm trên ShopeeFood: Niêm yết 45.000đ, kèm mã giảm giá 15%.
========================================================================================
```

---

# PHẦN V — KẾ HOẠCH TRIỂN KHAI THEO TỪNG GIAI ĐOẠN (PHASED ROADMAP)

```
[Phase 1: Contracts & Domain Logic] ──► [Phase 2: Sources & Vision OCR] ──► [Phase 3: API & Engine] ──► [Phase 4: UI Web]
```

### 📌 Giai đoạn 1: Chuẩn hóa Hợp đồng & Logic Nghiệp vụ thuần (Contracts & Pure Domain)
* **Nhiệm vụ:**
  * Hoàn thiện Pydantic models trong `packages/contracts/src/ca_contracts/catchment_survey.py` và `CatchmentPriceSurvey.json`.
  * Xây dựng `substitute_matrix.py`: Định nghĩa ma trận phân loại món thay thế cho Cơm, Bún/Phở, Cà phê, Trà sữa.
  * Cài đặt công thức toán học tính chỉ số AMBI và phân vị kép.
* **Tiêu chí nghiệm thu (DoD):** 100% unit test offline chạy trong < 1 giây, kiểm thử đầy đủ các trường hợp ngoại lệ.

### 📌 Giai đoạn 2: Phát triển Tầng Thu thập Dữ liệu & AI Vision OCR
* **Nhiệm vụ:**
  * Hoàn thiện `delivery_camoufox_source.py`: Cào ShopeeFood API an toàn, có cache TTL 30 phút.
  * Hoàn thiện `gmaps_menu_source.py`: Điều hướng Google Maps lấy danh sách ảnh album "Thực đơn / Menu".
  * Hoàn thiện `vision_menu_extractor.py`: Kết nối Gemini Vision AI đọc ảnh bảng giá tiếng Việt, có prompt chống ảo giác.
* **Tiêu chí nghiệm thu (DoD):** Kiểm thử trích xuất chính xác tên món và giá tiền từ các file ảnh mẫu fixture.

### 📌 Giai đoạn 3: Tích hợp Bộ điều phối & Backend API
* **Nhiệm vụ:**
  * Nâng cấp `ag_pricing/orchestrator.py`: Điều phối luồng Hybrid (quét cả Online và Tại chỗ, gọi OCR, tổng hợp số liệu).
  * Viết router FastAPI `apps/api/src/ca_api/interfaces/http/pricing_radar.py` chạy trên worker threadpool.
* **Tiêu chí nghiệm thu (DoD):** Endpoint `POST /api/v1/market/catchment-survey` phản hồi chuẩn xác theo schema, có xác thực bảo mật.

### 📌 Giai đoạn 4: Xây dựng Giao diện Web (UI Dashboard)
* **Nhiệm vụ:**
  * Tạo giao diện trực quan trong `apps/web` cho phép chủ quán nhập địa chỉ, chọn bán kính và xem biểu đồ so sánh giá Online vs Tại chỗ.
  * Thể hiện trực quan bảng đối chiếu món thay thế và chỉ số AMBI.

---

# PHẦN VI — MA TRẬN RỦI RO & BIỆN PHÁP KIỂM SOÁT (RISK & MITIGATION)

| # | Rủi ro tiềm ẩn | Mức độ | Biện pháp kiểm soát trong thiết kế |
|---|---|---|---|
| **1** | **Ảnh menu trên Google Maps bị mờ, nghiêng, không đọc được giá** | Cao | Thiết lập `confidence_score` trong Vision prompt. Nếu ảnh mờ $\rightarrow$ bỏ qua ảnh đó. Nếu quán không còn ảnh nào $\rightarrow$ tự động kích hoạt **Fallback Reverse Markup (-20%)** từ ShopeeFood. |
| **2** | **Chi phí token Vision AI tăng cao nếu quét quá nhiều ảnh** | Trung bình | Giới hạn cứng: Chỉ quét đối thủ đã vượt qua bộ lọc kép Dual-Gate ($v \ge 50$ reviews) và mỗi đối thủ chỉ lấy tối đa **2–3 ảnh menu rõ nhất**. |
| **3** | **Quán đối thủ đổi menu hoặc tăng giá nhưng ảnh trên Google Maps là ảnh cũ** | Trung bình | Ưu tiên lấy các ảnh có timestamp tải lên trong vòng 6–12 tháng gần nhất. Ghi chú rõ trên UI: *"Giá tại chỗ bóc tách từ ảnh chụp của khách hàng gần nhất"*. |
| **4** | **Trình duyệt Camoufox tốn RAM trên server** | Trung bình | Tác vụ khảo sát giá chạy **theo yêu cầu (On-Demand)**, không chạy định kỳ dồn dập. Sử dụng Semaphore giới hạn tối đa 2 browser chạy đồng thời. Có cache kết quả 30–60 phút. |
| **5** | **Google Maps hoặc ShopeeFood thay đổi cấu trúc trang** | Thấp | Tách bạch hoàn toàn hàm `fetch()` (browser) và hàm `extract()` (thuần). Tái dùng Camoufox anti-detect đã được kiểm chứng trong dự án. |

---

> **Kết luận:** Bản kế hoạch này thiết lập một phương pháp tiếp cận hoàn toàn khoa học và bám sát thực tế kinh doanh F&B Việt Nam: **Không lấy giá ảo trên sàn áp vào menu tại bàn, và không bỏ qua các món ăn thay thế cạnh tranh trực tiếp chiếc dạ dày của khách**.
