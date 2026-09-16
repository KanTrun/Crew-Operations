# Validation Report v2 — Database Nhân viên & Lịch xếp ca (quan_01)
**Cập nhật theo cấu trúc ca MỚI: chỉ 2 khung/ngày**
- Ca sáng: 06:00–14:00 (8h)
- Ca chiều: 14:00–22:00 (8h)

Tuần tham chiếu: **2026-W37** (Thứ 2 07/09 → CN 13/09/2026) · Generated: 2026-09-15 (Claude Web), reviewed locally

---

## 0. THAY ĐỔI SO VỚI BẢN TRƯỚC (3 khung/ngày, 5h/ca)

| | Bản cũ (3 khung) | Bản mới (2 khung) |
|---|---|---|
| Số khung/ngày | 3 (sáng/chiều/tối) | **2 (sáng/chiều)** |
| Độ dài ca | 5h | **8h** |
| Tổng ca/tuần | 21 | **14** |
| Tổng assignment tối thiểu | 42-44 | **28-30** |
| Số NV tối ưu | 14 | **13** |
| Full-time "tuyến đầu" (NV, chưa tính CQ/QL) | 4 | **3** |

**Hệ quả quan trọng nhất**: với ca cố định 8h, **giới hạn "1 ca/ngày/người" theo C01 (≤8h/ngày) giờ khớp CHÍNH XÁC** — làm 1 ca đã chạm trần ngày, không còn phải giải thích/du di như bản 5h cũ. Đồng thời, **bội số 8h trùng khít với các mốc giờ/tuần trong bảng hợp đồng** (mục 6 của spec): Full-time 40-48h = 5-6 ca; Part-time cố định 24-32h = 3-4 ca; Flexible 12-20h = 2 ca (16h, không thể đạt 20h vì 3 ca=24h vượt trần); Weekend-only 8-16h = 1-2 ca. → **Không còn mâu thuẫn nội tại giữa bảng hợp đồng và cấu trúc ca** như bản báo cáo trước đã chỉ ra.

---

## 1. TÍNH LẠI SỐ NHÂN VIÊN TỐI ƯU

### Bước 1 — Workload tổng
- 14 ca/tuần × 8h = **112 giờ-ca**.
- `so_nguoi_toi_thieu` = 2 mặc định, nâng lên 3 cho 2 ca cao điểm (chiều Thứ 6 & chiều Thứ 7 — khung giờ ăn tối + đóng cửa cuối tuần) → **tổng nhu cầu = 12×2 + 2×3 = 30 assignment-slots/tuần**.

### Bước 2 — Capacity thực tế/nhân viên
Ca 8h = đúng trần C01 → **tuyệt đối không thể làm 2 ca/ngày** (dù liền kề hay cách nhau, vì 8h+8h=16h). Kết hợp C06 (≤6 ngày liên tiếp) → trần lý thuyết tối đa **6 ca/tuần = 48h**, đúng bằng trần C02. Bảng trần thực tế đã dùng:

| Loại hợp đồng | Trần ca/tuần | Giờ tương ứng |
|---|---|---|
| Full-time (NV tuyến đầu) | 6 | 48h |
| Full-time (Quản lý) | 3 | 24h (chủ động thấp hơn trần vì còn việc quản lý) |
| Full-time (Chủ quán) | 1 | 8h (vai trò giám sát, không vào vòng xoay) |
| Part-time cố định (không sinh viên) | 4 | 32h |
| Part-time cố định (sinh viên) | 2 | 16h (không thể chạm trần 20h với bội số 8h) |
| Flexible | 2 | 16h |
| Weekend-only | 2 | 16h (1 ca T7 + 1 ca CN) |

### Bước 3 — Skill coverage
5 vị trí phân bổ trên 14 ca:

| Vị trí | Số ca/tuần | Số NV có kỹ năng (trừ Chủ quán) |
|---|---|---|
| `thu_ngan` | 4 | 10 |
| `pha_che` | 4 | 6 |
| `phuc_vu` | 3 | 9 |
| `chay_ban` | 2 | 7 |
| `kho` | 1... còn lại | 3 |

*(`kho` chỉ xuất hiện 2 ca/tuần — sáng Thứ 4 & sáng CN — vẫn là vị trí mỏng nhân sự nhất, y như bản cũ; đã ưu tiên xếp bằng thuật toán "khan hiếm trước" để không thiếu người)*

### Bước 4 — Fairness (ca chiều "đêm" + cuối tuần)
- Tổng slot ca chiều/tuần: 5×2 + 2×3 = 16, trừ 1 ca do Quản lý đảm nhiệm → **15 slot chia cho nhóm luân phiên**.
- Do 1 ca 8h chiếm trọn "suất ca" duy nhất trong ngày của một người, áp lực ca chiều dồn nhiều hơn (tỷ lệ %) lên nhóm full-time/part-time-không-sinh-viên/flexible so với bản cũ — đây là lý do đội hình v2 cần **thêm 1 người linh hoạt (flexible) có kỹ năng `thu_ngan`/`phục_vụ`/`chạy bàn`** so với thiết kế ban đầu (12 người), nếu không chênh lệch ca chiều vượt mục tiêu ≤2 (đã kiểm chứng bằng thực nghiệm — xem mục 5).

### Bước 5 — Sinh viên
- 2/13 nhân viên là sinh viên (15%), chỉ làm ca sáng, ≤16h/tuần thực tế (dưới trần 20h vì giới hạn bội số 8h).

### Bước 6 — Buffer
- Tổng capacity nếu dùng hết trần: **41 slot-ca/tuần** (328h), nhu cầu thực tế **30 slot** → buffer ≈ **37%** — cao hơn khuyến nghị 15-20% vì đội hình giờ nhỏ hơn (13 người) nên mỗi người vắng mặt ảnh hưởng tỷ trọng lớn hơn; buffer rộng hơn giúp hấp thụ rủi ro nghỉ đột xuất tốt hơn khi đội hình mỏng.

### ➜ KẾT LUẬN: **13 nhân viên**, trong đó **6 thuộc diện "full-time" theo hợp đồng và 7 thuộc diện part-time/linh hoạt**.

---

## 2. TRẢ LỜI TRỰC TIẾP: CẦN BAO NHIÊU FULL-TIME, BAO NHIÊU PART-TIME?

| Nhóm | Số lượng | Giờ/tuần mỗi người |
|---|---|---|
| **Full-time (hợp đồng)** — gồm: | **6** | |
| — Chủ quán | 1 | ~8h (giám sát, không phải lao động chính) |
| — Quản lý | 2 | ~24h/người |
| — Nhân viên full-time tuyến đầu | 3 | 16–32h/người thực tế tuần này (trần 48h) |
| **Part-time / linh hoạt** — gồm: | **7** | |
| — Part-time cố định (sinh viên) | 2 | ≤16h/người |
| — Part-time cố định (không sinh viên) | 1 | ~24-32h |
| — Flexible/on-call | 2 | ~16h/người |
| — Weekend-only | 2 | 8–16h/người (chỉ T7+CN) |

**Tỷ lệ khuyến nghị: 6 Full-time : 7 Part-time/linh hoạt** (nếu chỉ tính "nhân viên tuyến đầu" thuần túy lao động thường xuyên, không tính Chủ quán/Quản lý: **3 Full-time NV : 7 Part-time/linh hoạt**).

- **Tối thiểu vận hành an toàn**: 11 người (rủi ro cao ở vị trí `kho` và dễ vượt chênh lệch ca chiều nếu có ai nghỉ).
- **Tối đa hợp lý**: ~15 người (thêm nữa khiến số ca/người quá thấp, nhất là nhóm part-time/flexible, khó giữ chân).
- **13 người là điểm cân bằng tốt nhất** đã kiểm chứng qua thực nghiệm xếp lịch + đo fairness thực tế.

---

## 3. HARD CONSTRAINTS (C01–C06) — KẾT QUẢ: **PASS 100%**

| Mã | Ràng buộc | Kết quả |
|---|---|---|
| C01 | ≤8h/ngày | PASS — mỗi ca đúng 8h, tối đa 1 ca/ngày/người (làm 2 ca = 16h, không thể xảy ra do thiết kế + solver chặn cứng) |
| C02 | ≤48h/tuần | PASS — cao nhất 32h/tuần (nv_04, nv_09), thấp hơn trần 48h |
| C03 | Không chồng ca cùng ngày | PASS — 0 vi phạm |
| C04 | Nghỉ ≥12h giữa 2 ca liên tiếp | PASS — solver loại trừ tổ hợp "ca chiều hôm nay (kết thúc 22h) → ca sáng hôm sau (bắt đầu 6h)" vì chỉ cách 8h < 12h; mọi tổ hợp còn lại ≥16h |
| C05 | Nghỉ giữa giờ trong ca | Ghi chú vận hành (ca 8h cần ≥45 phút nghỉ giữa ca theo luật) — không phải trường dữ liệu trong schema hiện tại |
| C06 | ≤6 ngày liên tiếp | PASS — cao nhất 4 ca/tuần đã dùng, dưới xa trần 6 |

**30/30 assignments đã tạo, 0 vi phạm** trong kiểm tra độc lập: ngày ISO, foreign key,
kỹ năng, đủ người và nghỉ phép đã duyệt. Seed reset và seed lặp lại cũng giữ đúng 13 users
và 22 KV records.

---

## 4. SKILL COVERAGE
100% 14/14 ca đạt ≥ `so_nguoi_toi_thieu`; 100% người được gán khớp kỹ năng với `vi_tri` của ca (kiểm tra 2 chiều). Vị trí mỏng nhất vẫn là `kho` (3 người biết, trừ Chủ quán) — khuyến nghị đào tạo chéo thêm 1 người nữa nếu muốn dự phòng tốt hơn.

---

## 5. FAIRNESS (SOFT CONSTRAINTS)

⚠️ Áp dụng cùng cách diễn giải đã thống nhất ở báo cáo trước: đo riêng trục "ca chiều/đêm" và "cuối tuần" theo đơn vị số ca (không cộng lẫn giờ, vì đơn vị khác nhau sẽ làm méo kết quả).

| Trục | Phạm vi so sánh | Kết quả | Mục tiêu | Đạt? |
|---|---|---|---|---|
| **Ca chiều (dem)** | 6 người: full-time NV + part-time cố định không sinh viên + flexible (loại Chủ quán/Quản lý/sinh viên/**weekend-only** — nhóm weekend-only bị loại vì chỉ có tối đa 2 ngày làm/tuần nên không thể so cùng thang với người làm cả tuần) | min=1 (nv_10) · max=3 (nv_04, nv_06, nv_09) → **spread=2** | ≤2 | ✅ PASS |
| **Cuối tuần** | 12 người (loại Chủ quán) | min=0 · max=2 → **spread=2** | ≤3 | ✅ PASS |
| **Ca vụn** | Toàn đội | 0 (mọi ca đều đúng 8h) | — | ✅ Trivial |
| **Giờ** | — | Dao động 8h–32h theo đúng hạng hợp đồng (chủ đích, không phải bất công) | N/A | — |

**Lưu ý quan trọng phát hiện qua thực nghiệm**: thiết kế ban đầu 12 người (như bản 3-khung cũ, chỉ scale xuống theo tỷ lệ) cho spread ca chiều = 3 (KHÔNG đạt mục tiêu ≤2), do ca 8h khiến mỗi người chỉ có "1 suất/ngày" duy nhất nên áp lực dồn ca chiều tập trung hơn vào vài người có kỹ năng `thu_ngan`/`phục_vụ`/`chạy bàn` trùng lặp. Đã khắc phục bằng cách **thêm 1 nhân viên flexible (nv_13)** với đúng bộ kỹ năng còn thiếu — đây là lý do con số cuối cùng là **13, không phải 12** người.

---

## 6. DATA COMPLETENESS
✅ Đủ 10/10 bảng dữ liệu · ✅ ID unique · ✅ Username unique (13/13) · ✅ Toàn bộ foreign keys hợp lệ (kiểm tra chéo tự động, 0 lỗi).

---

## 7. BUSINESS LOGIC

| Yêu cầu | Kết quả |
|---|---|
| 1 Chủ quán, 2-3 Quản lý | ✅ 1 Chủ quán, 2 Quản lý |
| Quản lý 3-4 kỹ năng, không làm ca chiều/tối thường xuyên | ✅ nv_02 (4 kỹ năng, 0 ca chiều), nv_03 (4 kỹ năng, 1 ca chiều/tuần) |
| Phân bố hợp đồng hợp lý | ✅ Full-time 6 (gồm CQ+QL+3 NV) · Part-time cố định 3 · Flexible 2 · Weekend-only 2 |
| 3-5 channel bindings | ✅ 4 |
| 3-5 swap requests | ✅ 5 |
| 4-5 handover tasks | ✅ 5 |

---

## 8. GIẢ ĐỊNH & THAY ĐỔI THIẾT KẾ

1. **Định nghĩa lại "ca đêm" (`dem`)**: schema mới không còn khung `toi` riêng, nên trục fairness "đêm" được ánh xạ sang khung `chieu` (kết thúc 22:00, tương đương giờ tối cũ). Dataset này giữ hợp đồng ca hiện tại để tương thích với solver/API.
2. **Sinh viên tránh khung `chieu`** (thay vì tránh `toi` như bản cũ) — vì `chieu` giờ là khung duy nhất kéo dài đến tối muộn (22h).
3. **13 người** (không phải scale tuyến tính từ 14→~9-10 như phép tính thô ban đầu gợi ý) — vì bội số 8h làm giảm tính linh hoạt chia nhỏ ca, cần dự phòng kỹ năng rộng hơn để đạt fairness thực chất, không chỉ đạt đủ số lượng tối thiểu.
4. Dữ liệu `fairness_ledger`, `leave_requests`, `swap_requests`, `handover_tasks`, `channel_bindings` là dữ liệu mô phỏng minh họa đầy đủ schema, độc lập với lịch tuần 2026-W37 vừa xếp.
5. **Giới hạn mô hình**: mỗi ca hiện có một `vi_tri` chính và assignment vẫn là danh sách
	staff ID để giữ tương thích với `Ca`, `LichTuan`, solver và UI hiện tại. Đây chưa phải mô hình
	nhu cầu đồng thời nhiều vị trí trong cùng một ca; không dùng báo cáo này để kết luận đã giải
	quyết đầy đủ staffing theo vị trí đồng thời.

---

## 9. FILES ĐÃ CẬP NHẬT
1. `staff_database_complete.json` — v2, 13 staff / 14 shifts / 30 assignments.
2. `seed_staff_complete.py` — có validate trước khi ghi và đồng bộ key cũ (đã test reset + chạy lặp không trùng lặp).
3. `validation_report.md` — file này.
