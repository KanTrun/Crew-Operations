# AG-PRICING — phạm vi (Catchment Area Price Radar)

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Khảo sát thực đơn và định vị giá bán đối thủ trong bán kính 3km – 7km trên các nền tảng delivery, áp dụng bộ lọc kép (Dual-Gate) và thống kê Bayes để xác định mức sẵn sàng chi trả (WTP) |
| Phạm vi | Một khu vực địa lý (tọa độ/bán kính) và một ngành hàng (từ khóa món/ẩm thực). Chạy theo yêu cầu (On-Demand) |
| Đầu vào | `CatchmentSurveyRequest` — tọa độ, bán kính, từ khóa ngành hàng, ngưỡng đánh giá tối thiểu |
| Đầu ra | `CatchmentSurveyResponse` — danh sách đối thủ đạt chuẩn, phân bố giá có trọng số (P25, Median, P75, Sweet spot), món signature, nhận định thị trường |
| Mô hình | Thống kê tất định (ADR-002) cho phân vị và trọng số Bayes. LLM nhỏ để tóm tắt nhận định thị trường mà không bịa số liệu |
| Song song | Chạy threadpool riêng có kiểm soát số lượng browser qua semaphore |
| Điều kiện dừng | Trả báo cáo phân bố giá hoàn chỉnh hoặc báo lỗi không đủ mẫu thống kê nếu khu vực quá ít quán |
| **Cấm** | Quyết định thay đổi giá bán trên POS của quán · Thu thập dữ liệu tài khoản người dùng cá nhân · Đăng nhập tài khoản vi phạm ToS · Ghi trực tiếp vào CSDL · Gọi chéo agent khác · Tự động spam request cào liên tục |
| Cổng | VF-SCHEMA, VF-STATISTICS |

## Vì sao chỉ xét quán có lượt đánh giá cao và đánh giá tích cực

Giá niêm yết của các quán vắng khách hoặc quán chất lượng kém là "giá ảo", chưa được thị trường chấp nhận. Đưa vào tập mẫu sẽ gây nhiễu nghiêm trọng (Sample Bias). Chỉ những quán đạt đồng thời:
1. **Gate 1 (Volume):** Lượng đánh giá $v \ge v_{min}$ (thể hiện quy mô đơn hàng thực tế).
2. **Gate 2 (Quality):** Điểm đánh giá $R \ge R_{min}$ và điểm Bayes $WR \ge 4.0$ (thể hiện khách hàng hài lòng với giá trị nhận lại).
mới được đưa vào tính toán phân bố giá và điểm ngọt thị trường (Sweet Spot).

## Nguyên tắc bất biến (ADR-002, ADR-008)

1. Mọi con số (Min, Max, P25, Median, P75, Mean, Sweet Spot) được tính bằng toán học thuần túy trong `qualifier.py` — tuyệt đối không để LLM đoán mò hoặc tự sinh số.
2. Agent chỉ đưa ra khuyến nghị định vị (Underpriced / Competitive / Premium) — chủ quán là người toàn quyền quyết định giá bán thực tế.
