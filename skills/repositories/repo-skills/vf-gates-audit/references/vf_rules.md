# Quy tắc Kiểm duyệt An toàn Fail-Closed (VF Gates)

Hệ thống NHỊP QUÁN áp dụng cơ chế kiểm duyệt **Fail-Closed**: nếu có bất kỳ nghi ngờ hoặc thiếu hụt nào về dữ liệu/nguồn gốc, đề xuất của Agent sẽ bị từ chối hoặc chuyển lên người phê duyệt.

## Ba Cổng Kiểm duyệt Cốt lõi

| Cổng | Tên cổng | Nhiệm vụ | Tiêu chuẩn Đạt | Hành động khi Vi phạm |
|---|---|---|---|---|
| **VF-SCHEMA** | Kiểm tra Cấu trúc | Xác minh đầu ra của LLM có chứa đầy đủ các trường bắt buộc hay không. | Có đủ 100% key yêu cầu trong schema. | `retry_once` (nếu lần đầu), sau đó `escalate` lên người duyệt. |
| **VF-TRACE** | Truy vết Nguồn gốc | Kiểm tra mọi thông tin đề xuất (giờ ca, tên người, lý do) có trích dẫn từ bằng chứng raw evidence hay không. | Từng trường quan trọng đều có grounding từ văn bản gốc. | `escalate` (từ chối tự động duyệt, yêu cầu người kiểm tra). |
| **VF-CONF** | Độ tin cậy Tối thiểu | Đo lường điểm tin cậy (confidence score) của LLM trích xuất. | Điểm tin cậy >= 0.70. | `escalate` nếu điểm dưới ngưỡng. |

## Các Cổng Mở rộng
- **VF-RULE:** Kiểm tra đề xuất có vi phạm các luật đã duyệt của quán hay không.
- **VF-NUM:** Kiểm tra tính chính xác của các con số tính toán (tiền nong, giờ công, định lượng).
- **VF-STALE:** Đảm bảo snapshot dữ liệu không bị lỗi thời (kiểm tra hash đối chiếu).
