# AG-SOP — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Hỏi đáp quy trình chỉ từ YAML phiếu và luật đã duyệt |
| Phạm vi | Một câu hỏi của nhân viên |
| Đầu vào | `{question, buoc[], luat[]}` |
| Đầu ra | `{cau_tra_loi, trich_dan[], chua_co}` |
| Mô hình | Khớp từ khoá replay. Cấm kiến thức chung của LLM |
| Song song | Có thể |
| Điều kiện dừng | Có trích dẫn hoặc câu "chưa có trong cẩm nang" |
| Cấm | Trả lời không nguồn · ghi DB · gọi agent khác |
| Cổng | VF-TRACE (mọi câu phải có citation hoặc chua_co) |
