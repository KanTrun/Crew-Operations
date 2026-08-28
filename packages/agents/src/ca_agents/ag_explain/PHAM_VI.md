# AG-EXPLAIN — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Dịch mã lý do của bộ giải thành **một** câu tiếng Việt |
| Phạm vi | Một phân công (một cặp ca × nhân viên). Tối đa 3 mệnh đề |
| Đầu vào | `{ma_list, cum_tu, so_lieu, so_lieu_cho_phep}` — cụm từ và số do lõi `ca_solver.explain` cấp |
| Đầu ra | `{cau, nguon_ma, so_lieu_dung, bi_loai, loai}` |
| Mô hình | Nhỏ là đủ. Soạn câu, không suy luận |
| Song song | Có. Mỗi phân công độc lập |
| Điều kiện dừng | Trả một câu, hoặc câu "chưa có căn cứ" nếu không mã nào dùng được |
| **Cấm** | Tự tính con số · thêm số ngoài `so_lieu_cho_phep` · nêu tên hay đánh giá con người · ghi DB · gọi agent khác · quyết định luồng |
| Cổng | VF-SCHEMA, **VF-NUM** |

## Vì sao agent không giữ từ điển mã lý do

Từ điển `MA_LY_DO` nằm ở `packages/solver` vì nó là **tri thức tất định của
lõi**. Nếu agent giữ bản sao, hai bản sẽ lệch nhau và VF-NUM không còn ý nghĩa.
Bộ điều phối đọc từ điển ở lõi rồi truyền vào agent.

## Cách VF-NUM luôn kiểm được

Cụm từ trong `MA_LY_DO` **không chứa chữ số**. Mọi số vào câu chỉ qua bảng
`DUOI_SO`, và chỉ khi số đó có trong `so_lieu_cho_phep`. Do đó tập số trong câu
luôn là tập con của dữ liệu đầu vào.
