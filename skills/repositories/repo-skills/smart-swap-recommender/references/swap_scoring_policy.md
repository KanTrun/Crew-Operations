# Chính Sách & Tiêu Chí Chấm Điểm Đổi Ca (Smart Swap Policy)

Khi nhân viên xin nghỉ ca đột xuất, thuật toán đề xuất người thế ca (`smart_swap.py`) tính toán điểm phù hợp dựa trên 4 tiêu chí cốt lõi:

| Tiêu chí | Trọng số điểm | Ý nghĩa nghiệp vụ |
|---|---|---|
| **Không trùng lịch (C01, C03, C06)** | Bắt buộc (Điều kiện lọc) | Ứng viên không được có giờ học (TKB), không trực ca khác cùng giờ, và không nghỉ phép. |
| **Kỹ năng phù hợp (C02)** | +40 điểm | Có đúng kỹ năng ca yêu cầu (ví dụ: ca cần `barista` hoặc `thu_ngan`). |
| **Cân bằng giờ làm (Fairness - C05)** | +30 điểm (nghịch đảo số giờ) | Ưu tiên nhân sự có số giờ đã làm trong tuần ít hơn để đảm bảo công bằng thu nhập và không quá trần. |
| **Lịch sử hỗ trợ / Sẵn sàng** | +30 điểm | Ưu tiên nhân viên thường xuyên nhận ca tăng cường hoặc có đăng ký khung giờ rảnh. |

## Phân loại Đề xuất
- **Điểm $\ge 70$:** Đề xuất hàng đầu (Khuyến nghị 1-Click Duyệt).
- **Điểm 50 - 69:** Đề xuất khả thi (Cần xác nhận từ người được chọn).
- **Không có ứng viên:** Báo động thiếu người cho Quản lý / Ca trưởng.
