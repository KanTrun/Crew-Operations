# AG-QUANVERSE — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Một trạng thái quán, bốn bản chiếu theo vai trò + gợi ý khẩu vị + vòng đời chế độ quán |
| Phạm vi | Bản chiếu `LivingCafeSnapshot` (máy chủ cắt field theo quyền) · chấm điểm khẩu vị trên catalog đã duyệt · đề xuất/duyệt/tắt chế độ |
| Đầu vào | Bản chiếu: `{role}` · Khẩu vị: `{do_ngot, huong_tra, co_sua, dietary_allergy}` · Chế độ: `{mode}` |
| Đầu ra | `LivingCafeSnapshot` (đã lọc theo vai trò) · danh sách gợi ý kèm lý do · mã projection mà chế độ tác động |
| Mô hình | Tất định 100%. Không LLM trong lớp này — mọi con số và mọi lý do là kết quả tính |
| Song song | Có. Mỗi lượt gợi ý/chế độ độc lập, không giữ trạng thái chung |
| Điều kiện dừng | Trả bản chiếu, danh sách gợi ý, hoặc kết quả đề xuất chế độ |
| **Cấm** | Bịa dị ứng từ khẩu vị · tự kích hoạt chế độ khi chưa có người duyệt · trả dữ liệu vận hành cho vai khách · ghi DB · gọi agent khác |
| Cổng | VF-SCHEMA, VF-RULE |

## Vì sao tách khỏi lớp HTTP

`ag_quanverse` giữ luật nghiệp vụ thuần: cắt dữ liệu theo vai trò và chấm điểm
khẩu vị. Lớp HTTP chỉ lo xác thực, rate limit và quy đổi mốc thời gian. Nhờ vậy
kiểm thử được luật cắt quyền mà không cần dựng máy chủ, và không có đường nào để
một thay đổi giao diện vô tình mở dữ liệu vận hành cho khách.

## Dị ứng không bao giờ được suy đoán

Khẩu vị (`ít ngọt`, `thơm trà`) là sở thích; dị ứng là thông tin y tế. Hàm chấm
điểm chỉ loại món khi khách **tự khai** thành phần dị ứng, và trả `allergy_flag`
để lớp trình bày nói rõ lý do loại. Không có nhánh nào suy dị ứng từ khẩu vị.
