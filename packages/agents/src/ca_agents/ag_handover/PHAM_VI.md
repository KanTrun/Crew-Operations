# AG-HANDOVER — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Đọc bàn giao ca tiếng Việt thành 4 ô SBAR + việc treo |
| Phạm vi | Một phiếu / một khối văn bản bàn giao |
| Đầu vào | `{text}` |
| Đầu ra | `{tinh_hinh, boi_canh, danh_gia, de_nghi, treo[], do_tin_cay}` |
| Mô hình | Replay từ khoá (CI). Live LLM chưa bật |
| Song song | Không |
| Điều kiện dừng | Trả 4 ô; nếu không tách được thì đánh dấu tin cậy thấp |
| Cấm | Ghi DB, gọi agent khác, tự đóng việc treo, tự chọn khi xung đột |
| Cổng | VF-SCHEMA, VF-TRACE, VF-CONF, VF-CONFLICT khi hai bản trích trái nhau |
