# AG-WASTE — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | (1) Gom ghi chú hao hụt theo ngày trong tuần. (2) Tính hao hụt theo nguyên liệu: lý thuyết ↔ thực tế, mức độ, xếp hạng nguyên nhân |
| Phạm vi | Một lô ghi chú + một kỳ kiểm kê, không phải một người |
| Đầu vào | (1) `[(thu, text), ...]`. (2) `ly_thuyet: {mat_hang: số}`, `thuc_te: {mat_hang: số}`, `notes: [dict]` |
| Đầu ra | (1) `{cau, thu, n, loai=hao_hut}[]`. (2) `LossLine[]`, `LossCauseRank[]`, `LossSummary` |
| Mô hình | Đếm replay + toán tất định — **không LLM** |
| Song song | Không bắt buộc |
| Điều kiện dừng | (1) Trả cụm n≥2 hoặc rỗng. (2) Trả đủ dòng cho mọi mặt hàng có ở một trong hai vế |
| Cấm | Luật về thái độ người · ghi DB · đặt hàng nhà cung cấp · gọi mạng · đọc/ghi DB · tự sinh số |
| Cổng | VF-SCHEMA, VF-RULE nếu đề xuất luật hao_hut |

## Quy ước số (bắt buộc)

`None` = **chưa có dữ liệu** cho vế đó. `0.0` = có dữ liệu và số bằng không.

Một mặt hàng chỉ có ở một vế thì dòng hao hụt mang `muc_do = thieu_du_lieu` và
`thieu_ve` nêu rõ vế nào còn thiếu. **Không** được suy ra "đạt" từ chỗ trống —
không có bằng chứng không phải là bằng chứng đạt.

## Ranh giới module

`ag_waste` là hàm thuần: nhận dict/list đã đọc sẵn, trả model hợp đồng. Không đọc
`kv`, không đọc SQLite, không gọi agent khác, không gọi provider AI.

Tầng đọc dữ liệu nằm ở API (`apps/api/src/ca_api/interfaces/http/hao_hut.py`):
đọc `kv kiem_ke` + `menu_mon` + `kv waste_notes` rồi truyền vào các hàm ở đây.

Đường agent mẹ: AG-COPILOT nhận `ANALYZE_LOSS`, gọi hàm thuần qua
`configure_data_sources()` — mẹ **không** tự tính số.

## Nguồn dữ liệu

| Vế | Nguồn | Ghi chú |
|---|---|---|
| Lý thuyết | `menu_mon.bom` × `don_quay` đơn `xong` | Số ước lượng từ quầy nội bộ, không phải số sàn giao hàng |
| Thực tế | `kv kiem_ke` | Công thức §4.3: `dau_ca + nhap_trong_ca − cuoi_ca − hao_hut_ghi` |
| Nguyên nhân | `kv waste_notes` | Trường `nguyen_nhan`, dự phòng `ly_do` |

## Công thức

Lấy đúng công thức đã kiểm chứng ở
`skills/repositories/repo-skills/barista-waste-audit/scripts/audit_recipe_waste.py`
— không phát minh công thức mới:

```text
lý thuyết = Σ (định mức nguyên liệu × số phần đã bán)
thực tế   = Σ (đầu ca + nhập trong ca − cuối ca − hao hụt đã ghi)
lệch      = thực tế − lý thuyết        (âm hợp lệ: dùng ít hơn lý thuyết)
tỷ lệ %   = lệch / lý thuyết × 100
```

Ngưỡng đọc từ `config/nguong-hao-hut.yaml`, không hard-code trong mã.

## Bí danh tên mặt hàng

Ba nguồn gọi tên nguyên liệu khác nhau (`cafe_g` ở công thức, `ca_phe_hat` ở kho,
`ca_phe` ở ghi chú). `BI_DANH` trong `loss.py` là ánh xạ **tường minh** để quy về
một mã.

Cố ý **không** fuzzy-match: ghép gần đúng sẽ nối sai hai mặt hàng khác nhau trong
im lặng, và sai kiểu đó khó phát hiện hơn nhiều so với một dòng "chưa đủ dữ liệu"
hiện ra trước mắt.
