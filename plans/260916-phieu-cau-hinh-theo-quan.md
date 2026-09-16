# Phiếu cấu hình theo quán

## Outcome

Mỗi quán chỉ nhìn thấy và mở được những mẫu Phiếu mà quán đã bật; mẫu fixture
không còn là danh sách bắt buộc ở API hoặc giao diện.

## Constraints

- YAML mẫu vẫn là nguồn duy nhất của các bước và điều kiện mở.
- API và cổng tất định quyết định khả năng mở Phiếu; agent không quyết định luồng.
- Không tự tạo Phiếu từ lịch ca khi chưa có trạng thái ca đáng tin cậy.

## Non-goals

- Không thay đổi nội dung của ba mẫu fixture.
- Không thêm agent hoặc tự động phân công việc treo.

## Acceptance criteria

- Cấu hình quán theo `store_id` kiểm soát danh sách mẫu trả về và từ chối mẫu bị tắt.
- Chỉ mẫu có `mo_khi: nhan_vien_da_diem_danh` cần điểm danh.
- Bàn giao ca có thể mở không cần điểm danh.
- Unit test bao phủ mẫu bị tắt và điều kiện mở theo mẫu.

## Steps

1. Thêm cấu hình và trình nạp có kiểm tra cấu trúc.
2. Thay hằng mẫu hardcode trong API bằng cấu hình.
3. Cập nhật giao diện để chỉ yêu cầu điểm danh khi có mẫu cần điều kiện đó.
4. Chạy test API, engine và typecheck web.