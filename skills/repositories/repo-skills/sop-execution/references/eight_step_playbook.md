# Cẩm Nang 8 Bước Vận Hành (ADR-010)

Quy trình chuẩn hóa cẩm nang quán theo triết lý "Cẩm nang tự viết là bộ nhớ":

1. **Ghi nhận:** Lưu lại mọi thao tác chỉnh sửa hoặc phản ánh thực tế từ ca làm việc.
2. **Tìm mẫu:** Phát hiện các sự cố hoặc mẫu hành vi lặp lại (>= 3 lần).
3. **Đề xuất luật (AG-RULE):** Agent đề xuất luật điều chỉnh bằng đúng một câu ngắn gọn, súc tích.
4. **Kiểm tra cổng (VF-RULE):** Xác minh luật không vi phạm quyền con người, không xung đột với luật hiện hành.
5. **Tập sự:** Cho luật chạy thử nghiệm ngầm trong 5 ca làm việc (chạy im lặng ghi log).
6. **Người duyệt:** Người quản lý thẩm định kết quả tập sự và bấm duyệt chính thức.
7. **Áp dụng tham số lõi:** Luật được đưa vào điều phối tự động (inject vào solver hoặc opsengine).
8. **Theo dõi & Tự đào thải:** Hệ thống tự động theo dõi hiệu quả, nếu tỷ lệ tuân thủ < 80% sẽ tự động tắt luật.
