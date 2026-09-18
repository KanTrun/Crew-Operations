# AG-PREDICT — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Phát hiện mẫu thành công & đề xuất luật tích cực từ dữ liệu vận hành |
| Phạm vi | Phân tích dữ liệu lịch sử, tính toán định giá & đề xuất luật cẩm nang |
| Đầu vào | Dữ liệu doanh thu, chi phí, nhân sự, lịch sử thành công |
| Đầu ra | `{pattern_id, loai, do_tin_cay, bang_chung, nguon}` / đề xuất luật |
| Mô hình | Math Layer thuần (ADR-002) — không I/O, không bất định |
| Song song | Có. Mỗi mẫu độc lập |
| Điều kiện dừng | Trả danh sách mẫu/đề xuất, hoặc rỗng nếu không đủ bằng chứng |
| **Cấm** | Ghi DB · gọi agent khác · I/O mạng · nguồn bất định (random/time) · quyết định luồng |
| Cổng | VF-SCHEMA, VF-NUM |

## Vì sao Math Layer là hàm thuần

Mọi con số phải tái lập được và audit được. `math_layer.py` không được chạm
I/O hay nguồn bất định — dữ liệu do tầng ngoài truyền vào (ADR-002).