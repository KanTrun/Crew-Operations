# Phân Loại Phản Hồi Khách Hàng (Voice of Customer - VOC)

Hệ thống phân loại đánh giá của khách hàng quán cà phê thành 3 nhóm cảm xúc và các nhóm vấn đề chuyên môn:

## 1. Nhóm Cảm Xúc (Sentiment)
- **POSITIVE (Tích cực):** Khen đồ uống ngon, không gian đẹp, nhân viên thân thiện.
- **NEUTRAL (Trung tính):** Hỏi thông tin, đóng góp ý kiến thông thường.
- **NEGATIVE (Tiêu cực):** Phàn nàn thái độ phục vụ, đồ uống sai vị, đợi món quá lâu, quán ồn/bẩn.

## 2. Nhãn Vấn Đề (Problem Tags)
- `TAG_QUALITY`: Chất lượng đồ uống (nhạt, chua, đắng, lạnh).
- `TAG_SERVICE`: Tốc độ ra món, thái độ nhân viên phục vụ/thu ngân.
- `TAG_HYGIENE`: Vệ sinh bàn ghế, quầy bar, nhà vệ sinh.
- `TAG_PRICE`: Phản ánh về giá cả, phụ thu, chương trình khuyến mãi.

## 3. Bộ Nhớ Khách Quen (Customer Preferences)
Lưu trữ các thói quen uống của khách:
- Mức ngọt: 0% đường, 50% đường, 100% đường.
- Đá: Không đá, ít đá, nhiều đá.
- Loại sữa: Sữa tươi thanh trùng, sữa yến mạch (Oat milk - cho khách dị ứng lactose).
