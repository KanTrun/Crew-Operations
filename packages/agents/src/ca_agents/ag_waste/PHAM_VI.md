# AG-WASTE — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Gom ghi chú hao hụt theo ngày trong tuần |
| Phạm vi | Một lô ghi chú, không phải một người |
| Đầu vào | `[(thu, text), ...]` |
| Đầu ra | `{cau, thu, n, loai=hao_hut}[]` |
| Mô hình | Đếm replay |
| Song song | Không bắt buộc |
| Điều kiện dừng | Trả cụm n≥2 hoặc rỗng |
| Cấm | Luật về thái độ người · ghi DB · đặt hàng nhà cung cấp |
| Cổng | VF-SCHEMA, VF-RULE nếu đề xuất luật hao_hut |
