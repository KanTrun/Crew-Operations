# AG-BRIEF — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Viết bản tin sáng cho chủ quán, **tối đa 5 câu** |
| Phạm vi | Một ngày, một quán. Chỉ xếp và cắt dữ kiện đã có |
| Đầu vào | `Fact[] = {loai, cau, so_lieu, uu_tien?}` do lõi tất định cấp |
| Đầu ra | `{cac_cau, nguon_loai, so_lieu_dung, bi_loai, loai}` |
| Mô hình | Nhỏ là đủ. Xếp thứ tự và soạn câu |
| Song song | Không cần. Một lần mỗi sáng |
| Điều kiện dừng | Trả ≤5 câu, hoặc một câu "không có việc cần để ý" |
| **Cấm** | Tự tính con số · thêm số ngoài `so_lieu` của dữ kiện · nêu tên hoặc đánh giá nhân viên · kết luận ai gian · ghi DB · gọi agent khác · quyết định luồng |
| Cổng | VF-SCHEMA, **VF-NUM** |

## Thứ tự ưu tiên

Việc có hạn và dấu hiệu an toàn đứng trước thông tin nền:

| Loại | Ưu tiên |
|---|---|
| `viec_treo_qua_han` | 10 |
| `dau_hieu_bat_thuong` | 20 |
| `ton_duoi_nguong` | 30 |
| `ca_thieu_nguoi` | 40 |
| `doi_ca_cho_duyet` | 50 |
| `phieu_chua_xong` | 60 |
| `luat_cho_duyet` | 70 |

Sắp xếp là **tất định**: `(ưu tiên, loại, nội dung câu)`. Cùng đầu vào cho cùng
bản tin, nên `make replay` phát lại được.

## Tự loại câu trước cổng

Agent tự bỏ câu có số không truy được về `so_lieu` và ghi lý do vào `bi_loai`.
Cổng VF-NUM vẫn chạy sau đó — đây là phòng thủ hai lớp, không phải thay cổng.
