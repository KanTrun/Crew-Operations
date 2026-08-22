# AG-RULE — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Từ mẫu ≥3 lần sửa, đề xuất đúng một luật tiếng Việt |
| Phạm vi | Một mẫu. Xem tối đa 10 lần sửa tương tự |
| Đầu vào | `{loai_quyet_dinh, n, bang_chung}` |
| Đầu ra | `{cau_luat_tieng_viet, dieu_kien, bang_chung, do_tin_cay}` hoặc rỗng |
| Mô hình | Nhận mẫu replay, không suy luận dài |
| Song song | Không. Hàng đợi một luật |
| Điều kiện dừng | Một luật hoặc rỗng nếu n < 3 |
| Cấm | Đề xuất khi <3 bằng chứng · luật về một con người · sửa/xoá luật đã có · ghi DB |
| Cổng | VF-SCHEMA, VF-TRACE, VF-CONF, VF-RULE |
