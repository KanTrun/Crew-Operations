# PROMPT CHO CLAUDE WEB — TẠO DATABASE NHÂN VIÊN + LỊCH XẾP CA HOÀN CHỈNH

> **Mục tiêu:** Tính toán số nhân viên tối ưu → Sinh database đầy đủ (staff + shifts + assignments + availability + leave + fairness + swaps + handovers + channel bindings) → Xuất 1 file JSON duy nhất + script seed Python.

---

## 1. NGỮ CẢNH DOANH NGHIỆP

**Loại hình:** Quán cà phê Việt Nam (F&B), vận hành 7 ngày/tuần  
**Quy mô:** 1 chi nhánh (`store_id: "quan_01"`)  
**Mô hình nhân sự:** 3 vai trò — Chủ quán (Owner), Quản lý (Manager), Nhân viên (Staff)  
**Hợp đồng:** Full-time, Part-time cố định, Flexible/On-call, Weekend-only  
**Đặc thù:** Có sinh viên làm thêm, cần công bằng ca tối/ca cuối tuần, có chatbot Telegram/Zalo

---

## 2. CẤU TRÚC CA LÀM (SHIFT STRUCTURE) — BẮT BUỘC TUÂN THỦ

### 2.1 Khung giờ chuẩn (3 khung/ngày)

| Khung | Tên | Giờ bắt đầu | Giờ kết thúc | Độ dài |
|-------|-----|-------------|--------------|--------|
| `sang` | Ca sáng | 07:00 | 12:00 | 5h |
| `chieu` | Ca chiều | 12:00 | 17:00 | 5h |
| `toi` | Ca tối | 17:00 | 22:00 | 5h |

### 2.2 Tuần làm việc

- **7 ngày:** Thứ 2 → Chủ nhật (`thu: 1..7`, trong đó 1=T2, 7=CN)
- **Tổng ca/tuần:** 21 ca (3 khung × 7 ngày)
- **Mỗi ca có:** `id`, `thu`, `ngay` (ISO), `khung`, `bat_dau`, `ket_thuc`, `vi_tri`, `so_nguoi_toi_thieu`

### 2.3 Vị trí (Positions) — 5 loại, mỗi ca chỉ yêu cầu 1 vị trí chính

| Mã | Tên tiếng Việt | Kỹ năng bắt buộc |
|----|----------------|------------------|
| `pha_che` | Pha chế | `pha_che` |
| `thu_ngan` | Thu ngân | `thu_ngan` |
| `phuc_vu` | Phục vụ | `phuc_vu` |
| `kho` | Kho | `kho` |
| `chay_ban` | Chạy bàn | `chay_ban` |

### 2.4 Số người tối thiểu / ca

- **Mặc định:** `so_nguoi_toi_thieu = 2` (đảm bảo backup, giao ca an toàn)
- **Tổng assignment tối thiểu/tuần:** 21 ca × 2 = **42 assignments**

---

## 3. RÀNG BUỘC PHÁP LUẬT (HARD CONSTRAINTS) — KHÔNG ĐƯỢC VI PHẠM

*Nguồn: Bộ luật Lao động 2019 (Việt Nam) + Cấu hình quán*

| Mã | Ràng buộc | Giá trị | Điều luật / Nguồn |
|----|-----------|---------|-------------------|
| **C01** | Giờ làm việc tối đa / ngày | **8 giờ** | Điều 105 BLĐ 2019 |
| **C02** | Giờ làm việc tối đa / tuần | **48 giờ** | Điều 105 BLĐ 2019 |
| **C03** | Không chồng ca cùng ngày | Không overlap giờ | Logic nghiệp vụ |
| **C04** | Khoảng nghỉ giữa 2 ca liên tiếp | **≥ 12 giờ** | Điều 110 BLĐ 2019 |
| **C05** | Nghỉ giữa giờ trong ca | ≥ 30p nếu ca ≥ 6h; ≥ 45p ca đêm | Điều 109 BLĐ 2019 |
| **C06** | Số ngày làm liên tiếp tối đa | **6 ngày** | Cấu hình quán |

> **Lưu ý:** Ca chuẩn 5h → không vi phạm C01, C05. Nhưng nếu gán 2 ca liên tiếp (sáng+chiều = 10h) → vi phạm C01. Solver phải xử lý.

---

## 4. RÀNG BUỘC MỀM & CÔNG BẰNG (SOFT CONSTRAINTS & FAIRNESS)

### 4.1 4 trục công bằng (Fairness Axes) — Minimize Maximum Debt

| Trục | Mô tả | Cách tính điểm |
|------|-------|----------------|
| `cuoi_tuan` | Ca thứ 7 + Chủ nhật | +1 mỗi ca T7/CN |
| `dem` | Ca tối (khung `toi` HOẶC bắt đầu ≥ 17:00) | +1 mỗi ca đêm |
| `gio` | Tổng giờ làm thực tế | Cộng dồn giờ (float) |
| `vun` | Ca vụn (ngắn < 5h) | +1 mỗi ca < 5h |

**Mục tiêu tối ưu:** Minimize `max_debt` = max over all staff of (sum of 4 axes)  
→ Người "nợ" nhiều nhất càng ít càng tốt.

### 4.2 Ràng buộc sinh viên

- `la_sinh_vien: true` → Ưu tiên ca sáng, **tránh ca tối**
- `max_hours ≤ 20` giờ/tuần
- Có TKB block: `(thu, bat_dau, ket_thuc)` — solver KHÔNG gán ca trùng

---

## 5. KỸ NĂNG (SKILLS) — MA TRẬN KHẢ NĂNG

- Mỗi NV có **2-3 kỹ năng** (trừ Quản lý: 3-4)
- NV mới/Thử việc: 1-2 kỹ năng
- **Yêu cầu:** Mỗi vị trí trong 21 ca phải có đủ người cover
- **Ma trận kỹ năng → vị trí:** 1-1 mapping (pha_che→pha_che, thu_ngan→thu_ngan, ...)

---

## 6. LOẠI HỢP ĐỒNG & GIỜ LÀM (CONTRACT TYPES)

| Loại | Giờ/tuần | Ca/tuần | Đặc điểm | Ghi chú |
|------|----------|---------|----------|---------|
| **Full-time** | 40-48h | 5-6 ca | NV lõi, QL, lương cố định + thưởng | Core team |
| **Part-time cố định** | 24-32h | 3-4 ca | Sinh viên, lịch cố định (vd: T2-T4-T6 sáng) | Có TKB |
| **Flexible/On-call** | 12-20h | 2-3 ca | Thử việc, bù ca, cover vắng | Ít ràng buộc |
| **Weekend-only** | 8-16h | 1-2 ca | Chỉ T7/CN, ca tối | Bổ sung peak hours |

---

## 7. DỮ LIỆU LIÊN QUAN CẦN SINH KÈM (RELATED DATA)

Claude phải sinh **TẤT CẢ** các dữ liệu sau trong cùng 1 file JSON:

### 7.1 Staff (Nhân viên)
- `id`, `ten`, `username`, `display_name`, `role`, `ky_nang[]`, `la_sinh_vien`, `so_dien_thoai_hash`, `store_id`, `active`, `contract_type`, `max_hours_tuan`

### 7.2 Shifts (21 ca/tuần)
- `id`, `thu`, `ngay`, `khung`, `bat_dau`, `ket_thuc`, `vi_tri`, `so_nguoi_toi_thieu`

### 7.3 Assignments (Phân công)
- `ca_id` → `[staff_id, ...]` (≥ 2 người/ca, khớp skill)

### 7.4 Availability (Đăng ký làm)
- `staff_id`, `days[]` (thứ muốn làm), `max_hours`

### 7.5 Leave Requests (Xin nghỉ)
- `id`, `staff_id`, `date` (ISO), `reason`, `status` (`approved`/`pending`/`tu_choi`)

### 7.6 Swap Requests (Đổi ca)
- `id`, `staff_id_xin`, `shift_id`, `nhan_xin`, `ly_do`, `status`, `created_at`, `approved_by?`, `approved_at?`

### 7.7 Fairness Ledger (Sổ công bằng)
- `staff_id` → `{ca_toi_tich_luy, ca_cuoi_tuan_tich_luy, diem_bap_cong_bang}`

### 7.8 Handover Tasks (Việc treo / Ban giao ca)
- `id`, `ca_goc`, `nguoi_giao`, `nguoi_nhan`, `noi_dung`, `trang_thai`, `muc_do`

### 7.9 Channel Bindings (Kênh chatbot)
- `id`, `staff_id`, `channel` (`telegram`/`zalo`), `channel_user_id`, `display_name`, `status`, `bound_at`

### 7.10 Weekly Schedule Metadata
- `tuan_iso` (vd: `2026-W37`), `trang_thai`, `solver_run_id`, `nguon`

---

## 8. THUẬT TOÁN TÍNH TOÁN SỐ NHÂN VIÊN TỐI ƯU (CLAUDE TỰ TÍNH)

### Bước 1: Tính workload tổng
```
Tổng giờ ca/tuần = 21 ca × 5h = 105h
Tổng assignment slots = 21 ca × 2 người = 42 slots
```

### Bước 2: Tính capacity per nhân viên
```
Full-time: max 48h/tuần = 9-10 ca (nhưng thực tế 5-6 ca do C01, C04)
Part-time: max 32h/tuần = 6-7 ca
Flexible: max 20h/tuần = 4 ca
Weekend-only: max 16h/tuần = 3 ca
```

### Bước 3: Tính số NV tối thiểu theo skill coverage
- 5 vị trí × 21 ca = 105 position-slots
- Mỗi NV cover trung bình 2-3 skills
- Cần đủ người cho mỗi vị trí mỗi khung

### Bước 4: Tính theo fairness (ca tối + cuối tuần)
- Ca tối: 7 ca/tuần × 2 người = 14 slots tối
- Ca cuối tuần: 6 ca (T7+Cn) × 2 người = 12 slots
- Cần đủ người xoay vòng để chênh lệch ≤ 2 ca tối, ≤ 3 ca cuối tuần

### Bước 5: Tính theo sinh viên
- Sinh viên chỉ làm ca sáng/chiều, max 20h = 4 ca/tuần
- Cần đủ NV non-student cover ca tối

### Bước 6: Buffer & redundancy
- +15-20% buffer cho nghỉ ốm, nghỉ phép, turnover
- Có quản lý (không tính vào assignment thường)

---

## 9. OUTPUT YÊU CẦU (DELIVERABLES)

### 9.1 File JSON duy nhất: `staff_database_complete.json`

```json
{
  "metadata": {
    "generated_at": "2026-09-15T...",
    "generator": "Claude Web",
    "version": "1.0",
    "store_id": "quan_01",
    "tuan_iso": "2026-W37",
    "total_staff": 0,
    "total_shifts": 21,
    "total_assignments": 0,
    "fairness_axes": ["cuoi_tuan", "dem", "gio", "vun"]
  },
  "staff": [...],
  "shifts": [...],
  "assignments": {...},
  "availability": [...],
  "leave_requests": [...],
  "swap_requests": [...],
  "fairness_ledger": {...},
  "handover_tasks": [...],
  "channel_bindings": [...],
  "weekly_schedule": {
    "tuan_iso": "2026-W37",
    "trang_thai": "cho_duyet",
    "solver_run_id": "claude_gen_001",
    "nguon": "claude_web"
  }
}
```

### 9.2 Script Python: `seed_staff_complete.py`

- Idempotent (chạy nhiều lần không duplicate)
- Tạo SQLite users + KV store (lich_tuan, phan_cong, ngan_sach_cong_bang, de_xuat_doi_ca, viec_treo, kenh_bind)
- Password mặc định: `nhipquan`
- Có `--reset` flag

### 9.3 Validation Report: `validation_report.md`

- Kiểm tra tất cả hard constraints (C01-C06)
- Kiểm tra skill coverage
- Kiểm tra fairness spread
- Thống kê role distribution, contract distribution

---

## 10. QUY TẮC SINH DỮ LIỆU (GENERATION RULES)

### 10.1 Tên nhân viên
- Tiếng Việt có dấu, thực tế (vd: "Nguyễn Văn An", "Trần Thị Bình")
- Username: không dấu, lowercase (vd: `an_nguyen`, `binh_tran`)
- ID: `nv_XX` (sequential, 2 digits)

### 10.2 Phone hash
- Format: `hash_<8_chars>` (vd: `hash_a1b2c3d4`) — không lưu SĐT thật

### 10.3 Ngày tháng
- Tuần tham chiếu: **2026-W37** (08/09/2026 - 14/09/2026)
- `ngay` trong shifts: ISO format `YYYY-MM-DD`

### 10.4 Trạng thái
- `active: true` cho tất cả NV mới
- Leave requests: mix `approved`/`pending`
- Swap requests: mix `cho_duyet`/`approved`/`tu_choi`

### 10.5 Fairness ledger
- Tích lũy thực tế từ lịch sử (giả lập 4-8 tuần trước)
- `diem_bap_cong_bang`: âm = đang nợ, dương = dư
- Range: -5 đến +3

---

## 11. VALIDATION CHECKLIST (CLAUDE TỰ KIỂM TRA TRƯỚC KHI TRẢ VỀ)

### Hard Constraints (Phải PASS 100%)
- [ ] Không NV nào > 48h/tuần
- [ ] Không NV nào > 8h/ngày
- [ ] Không ca nào chồng giờ cho cùng 1 NV
- [ ] Khoảng nghỉ ≥ 12h giữa 2 ca liên tiếp của cùng NV
- [ ] Mỗi ca có ≥ 2 người, khớp skill với `vi_tri`
- [ ] Sinh viên không làm ca tối, max 20h/tuần
- [ ] Không NV nào làm > 6 ngày liên tiếp

### Soft Constraints (Đánh giá chất lượng)
- [ ] Fairness spread (max - min total debt) ≤ 5
- [ ] Ca tối chênh lệch ≤ 2 ca giữa người nhiều nhất/ít nhất
- [ ] Ca cuối tuần chênh lệch ≤ 3 ca
- [ ] Mỗi vị trí (5 loại) đều có cover đủ 21 ca

### Data Completeness
- [ ] Tất cả 10 bảng dữ liệu ở mục 7 đều có
- [ ] IDs unique, không duplicate
- [ ] Foreign keys khớp (staff_id trong assignments/availability/leave/swaps/fairness/handover/bindings đều tồn tại trong staff)
- [ ] Username unique

### Business Logic
- [ ] Có 1 Chủ quán, 2-3 Quản lý
- [ ] Quản lý có 3-4 kỹ năng, không làm ca tối thường xuyên
- [ ] Phân bố contract type hợp lý
- [ ] Có 3-5 channel bindings (Telegram/Zalo)
- [ ] Có 3-5 swap requests, 4-5 handover tasks

---

## 12. VÍ DỤ CẤU TRÚC RECORD (REFERENCE)

### Staff record
```json
{
  "id": "nv_01",
  "ten": "Nguyễn Thị Lan",
  "username": "lan_nguyen",
  "display_name": "Lan Nguyễn",
  "role": "quan_ly",
  "ky_nang": ["pha_che", "thu_ngan", "kho"],
  "la_sinh_vien": false,
  "so_dien_thoai_hash": "hash_a1b2c3d4",
  "store_id": "quan_01",
  "active": true,
  "contract_type": "full_time",
  "max_hours_tuan": 48
}
```

### Shift record
```json
{
  "id": "ca_01",
  "thu": 1,
  "ngay": "2026-09-08",
  "khung": "sang",
  "bat_dau": "07:00",
  "ket_thuc": "12:00",
  "vi_tri": "thu_ngan",
  "so_nguoi_toi_thieu": 2
}
```

### Assignment record (trong weekly_schedule.phan_cong)
```json
{
  "ca_01": ["nv_01", "nv_05"],
  "ca_02": ["nv_03", "nv_07"],
  ...
}
```

---

## 13. PROMPT CHO CLAUDE (COPY-PASTE NÀY)

> **Hãy đọc toàn bộ file này, tính toán số nhân viên tối ưu dựa trên workload, constraints, fairness, skill coverage → sinh database hoàn chỉnh theo spec ở mục 9. Trả về 3 file: `staff_database_complete.json`, `seed_staff_complete.py`, `validation_report.md`. Không hard-code số lượng nhân viên — hãy tính toán và giải thích reasoning trong validation report.**

---

## 14. GHI CHÚ QUAN TRỌNG

1. **Không hard-code số lượng NV** — Claude phải tính từ constraints
2. **Tất cả dữ liệu trong 1 JSON** — dễ import, dễ validate
3. **Script seed phải idempotent** — chạy lại không duplicate
4. **Validation report phải có bằng chứng** — show numbers, không chỉ nói "PASS"
5. **Fairness ledger phải có lịch sử giả lập** — không để trống
6. **Channel bindings chỉ 3-5** — demo chatbot, không phải tất cả NV
7. **Tuần tham chiếu cố định: 2026-W37** — để reproducible

---

*File này chứa toàn bộ ngữ cảnh cần thiết. Claude Web chỉ cần đọc file này là đủ để sinh database hoàn hảo.*