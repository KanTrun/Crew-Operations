# Ngưỡng Tồn Kho An Toàn & Điểm Đặt Hàng Lại (Reorder Point - ROP)

Quy định ngưỡng tồn kho tối thiểu cho các mặt hàng thiết yếu của quán cà phê:

| Mã mặt hàng | Tên nguyên liệu | Đơn vị | Mức an toàn tối thiểu (Min) | Mức đặt hàng chuẩn (Pack) | Thời gian giao hàng (Lead Time) |
|---|---|---|---|---|---|
| `ING_COFFEE_ROASTED` | Cà phê hạt rang mộc Robusta/Arabica | kg | 5.0 kg | Thùng 10 kg | 1 - 2 ngày |
| `ING_FRESH_MILK` | Sữa tươi thanh trùng Barista | hộp (1L) | 12 hộp | Thùng 12 hộp | Trong ngày |
| `ING_CONDENSED_MILK` | Sữa đặc có đường | lon (380g)| 6 lon | Thùng 24 lon | 1 ngày |
| `ING_SYRUP_PEACH` | Siro đào cao cấp | chai (700ml)| 2 chai | Thùng 6 chai | 2 ngày |
| `ING_CUP_PLASTIC` | Ly nhựa mang đi (Takeaway 500ml) | cái | 200 cái | Thùng 1.000 cái | 1 ngày |

## Công thức tính Điểm Đặt Hàng Lại (ROP)
$$\text{ROP} = (\text{Lượng tiêu thụ trung bình mỗi ngày} \times \text{Số ngày giao hàng}) + \text{Tồn kho an toàn tối thiểu}$$
- Khi Tồn kho hiện tại $\le \text{ROP}$: Hệ thống phát cảnh báo **CẦN NHẬP HÀNG (RESTOCK_REQUIRED)**.
