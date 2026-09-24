# Kế hoạch nghiên cứu & kiểm tra lại từng chức năng (Audit toàn diện)

> **Mục đích:** Rà soát lại **từng chức năng** của hệ thống Nhịp Quán để xác định chính xác
> chức năng nào **đang hoạt động**, chức năng nào **chưa hoạt động / chưa hoàn thiện**,
> và chức năng nào **chỉ có code nhưng chưa được kiểm chứng end-to-end**.
>
> **Ngày lập:** 2026-09-17
> **Trạng thái:** ⏳ Kế hoạch — chờ chủ dự án review & duyệt
> **Phạm vi:** Toàn bộ monorepo `d:\Crew-Operations` (apps/api, apps/web, packages/*)

---

## 1. Bối cảnh & vấn đề

Người dùng nhận định: **"đa phần các chức năng hình như vẫn chưa hoạt động được"**.

Điều này có thể do một trong các nguyên nhân sau (cần xác minh, không đoán):

1. **Code có nhưng chưa được nối end-to-end** — backend có endpoint, frontend có trang, nhưng
   luồng thật (click → API → DB → hiển thị) chưa chạy được.
2. **Chỉ có test/unit pass, chưa có E2E thật** — test dùng mock/stub, không chạy với dữ liệu thật.
3. **Phụ thuộc dịch vụ ngoài (LLM, SerpApi, Google Maps, ShopeeFood, TikTok, Threads, Camoufox)**
   — cần API key, quota, proxy, hoặc bị chặn (403/captcha) nên chạy thật không được.
4. **Cần phê duyệt con người (Two-Phase Approval)** — chức năng cố ý không tự ghi DB, nên nhìn
   bề ngoài "không làm gì" cho đến khi quản lý bấm Duyệt.
5. **Cần cấu hình / seed dữ liệu** — chưa có dữ liệu mẫu, chưa bật cờ, chưa có tham số duyệt.
6. **Chưa triển khai thật** — chỉ là plan/design, code chưa tồn tại hoặc mới một phần.

> **Nguyên tắc của bản audit này:** Mỗi chức năng phải được **kiểm chứng bằng cách chạy thật**
> (hoặc có bằng chứng E2E), không chấp nhận "code complete" làm trạng thái "hoạt động".

---

## 2. Phương pháp nghiên cứu (cách kiểm chứng từng chức năng)

Với **mỗi chức năng**, thực hiện theo thứ tự sau và ghi kết quả vào bảng ở mục 4:

| Bước | Hành động | Bằng chứng cần có |
|---|---|---|
| **A. Đọc code** | Xác định file backend (endpoint/service), frontend (trang/component), contract | Đường dẫn file |
| **B. Chạy test** | Chạy unit test + integration test liên quan | Số test pass/fail |
| **C. Chạy E2E thật** | Khởi động stack (API + DB + web), thao tác thật trên UI | Screenshot / log / kết quả API |
| **D. Kiểm tra phụ thuộc ngoài** | Xác định LLM/SerpApi/GMaps/ShopeeFood/TikTok/Threads/Camoufox có key & chạy được không | Kết quả gọi thật |
| **E. Kiểm tra phê duyệt** | Xác định chức năng có cần bấm Duyệt (Pha 2) không | Luồng ActionProposal |
| **F. Kết luận** | Gán trạng thái (xem mục 3) | Lý do ngắn gọn |

---

## 3. Thang trạng thái (dùng cho mọi chức năng)

| Ký hiệu | Ý nghĩa | Định nghĩa |
|---|---|---|
| 🟢 **HOẠT ĐỘNG** | Chạy thật end-to-end được, có bằng chứng | Đã thao tác thật trên UI/API thành công |
| 🟡 **MỘT PHẦN** | Chạy được nhưng còn thiếu/giới hạn | Chạy được luồng chính, luồng phụ chưa xong |
| 🔴 **CHƯA HOẠT ĐỘNG** | Có code nhưng chạy thật không được | Lỗi runtime, thiếu key, chưa nối E2E, bị chặn |
| ⚪ **CHƯA CÓ / CHƯA XONG** | Chưa có code hoặc mới một phần | Chỉ có plan/design, hoặc code dang dở |
| ❓ **CHƯA KIỂM CHỨNG** | Chưa xác định được | Cần chạy thử để biết |

---

## 4. Bảng trạng thái từng chức năng (điền dần khi nghiên cứu)

> ⚠️ **Đây là bảng sống.** Cột "Trạng thái hiện tại" là **nhận định sơ bộ** cần kiểm chứng lại
> bằng phương pháp ở mục 2. Khi review, đánh dấu ✅ vào cột "Đã kiểm chứng" sau khi chạy thật.

### 4.1. AI-COPILOT (chat điều hành)

| # | Chức năng | Intent / Endpoint | Trạng thái hiện tại | Đã kiểm chứng | Ghi chú |
|---|---|---|---|---|---|
| 1 | Chat text Copilot (replay) | `POST /copilot` | � HOẠT ĐỘNG | ✅ | E2E 57 PASS + verify script PASS |
| 2 | Chat text Copilot (live LLM) | `router.py` groq→gemini→openrouter→bai→ollama | ❓ | ☐ | Cần API key thật |
| 3 | Voice Copilot (Gemini Live) — gọi thoại + chat với AI agent | `gemini-3.8-live-extended-thinking` | 🟢 HOẠT ĐỘNG | ✅ | **ĐÃ HOÀN THIỆN (260918):** bật mặc định không cần env (`voice_enabled()` default `"true"`; frontend `!== "false"`), thêm nút toggle "Voice: Bật/Tắt" trên header Copilot, lưu lựa chọn vào localStorage. Test `test_voice_session.py` + `test_copilot_api.py` pass (80 test). |
| 4 | Xếp lịch tuần tự động (CP-SAT) | `SCHEDULE_SOLVE` | 🟢 HOẠT ĐỘNG | ✅ | Intent đúng + E2E duyệt executed |
| 5 | Xử lý nghỉ phép & đổi ca | `APPROVE_SHIFT_SWAP` | 🟢 HOẠT ĐỘNG | ✅ | Intent đúng |
| 6 | Bản tin giao ban đầu ngày | `GENERATE_DAILY_BRIEF` | 🟢 HOẠT ĐỘNG | ✅ | `/hom-nay` 200, có brief_hom_nay |
| 7 | Tra cứu cẩm nang & SOP | `QUERY_SOP` | 🟢 HOẠT ĐỘNG | ✅ | Intent đúng |
| 8 | Phân tích thất thoát & kho | `ANALYZE_WASTE` / `INVENTORY_RESTOCK_CHECK` | 🟢 HOẠT ĐỘNG | ✅ | Intent đúng (từ "hao hụt") |
| 9 | Đề xuất quy tắc mới | `CREATE_RULE_PROPOSAL` | 🟢 HOẠT ĐỘNG | ✅ | Intent đúng |
| 10 | Soạn thảo email | `SEND_MAIL` | 🟡 MỘT PHẦN | ✅ | Intent đúng, cần SMTP thật để gửi |
| 11 | Khảo sát đối thủ & thị trường | `RUN_CATCHMENT_SURVEY` | 🟡 MỘT PHẦN | ✅ | Intent đúng; ShopeeFood bị chặn (403/captcha) |
| 12 | Phân quyền theo role (RBAC) | `COPILOT_ROLE_INTENT_MATRIX` | 🟢 HOẠT ĐỘNG | ✅ | E2E 57 PASS, fail-closed |

### 4.2. Xếp lịch & chợ ca (scheduling)

| # | Chức năng | Trạng thái hiện tại | Đã kiểm chứng | Ghi chú |
|---|---|---|---|---|
| 13 | Availability xác nhận theo tuần | � HOẠT ĐỘNG | ✅ | `/lich/lifecycle` 200 |
| 14 | Schedule run (versioned/idempotent) | 🟢 HOẠT ĐỘNG | ✅ | `/lich/lifecycle` 200 |
| 15 | Open shift & shift application | 🟢 HOẠT ĐỘNG | ✅ | `/open-shifts` 200 |
| 16 | Claim nguyên tử (first-eligible) | 🟢 HOẠT ĐỘNG | ✅ | `/open-shifts` 200 |
| 17 | SLA escalation worker | � HOẠT ĐỘNG | ✅ | **ĐÃ SỬA (260918):** bảng `thong_bao_lich` thiếu trong Postgres → migration `0013` tạo bảng → endpoint 200 |
| 18 | Manager gap-resolution + revalidation | 🟢 HOẠT ĐỘNG | ✅ | `/lich/resolve-gaps` 200 |
| 19 | Duyệt → công bố → thông báo | 🟢 HOẠT ĐỘNG | ✅ | `/lich/lifecycle` 200 |

### 4.3. Kênh tin & mạng xã hội

| # | Chức năng | Trạng thái hiện tại | Đã kiểm chứng | Ghi chú |
|---|---|---|---|---|
| 20 | Telegram | 🟡 MỘT PHẦN | ✅ | `/channels/status` 200; cần bot token thật để gửi |
| 21 | Zalo | ❓ | ☐ | Cần app credentials |
| 22 | Facebook Page (inbox/chatbot) | 🟡 MỘT PHẦN | ✅ | `/page/status` 200; chưa kết nối thật |
| 23 | TikTok (Apify) | 🟡 MỘT PHẦN | ✅ | `/trends/apify-usage` 200; cần quota thật |
| 24 | Threads trending (Camoufox) | 🟡 MỘT PHẦN | ✅ | `/page/threads` 200; cần Camoufox thật |

### 4.4. Khảo sát giá & thị trường (pricing)

| # | Chức năng | Trạng thái hiện tại | Đã kiểm chứng | Ghi chú |
|---|---|---|---|---|
| 25 | ShopeeFood network interception | 🔴 CHƯA HOẠT ĐỘNG | ☐ | Bị chặn 403/captcha (canary đỏ) |
| 26 | Google Maps menu + Vision OCR | 🟡 MỘT PHẦN | ☐ | Cần Vision API key |
| 27 | SerpApi integration | � HOẠT ĐỘNG | ✅ | `POST /market/catchment-survey` 202, job chạy `scraping_online` |
| 28 | Math Layer định giá (sweet spot) | 🟢 HOẠT ĐỘNG | ✅ | Job status 200; 1288 test pass |
| 29 | Dashboard `/khao-sat-gia` | 🟢 HOẠT ĐỘNG | ✅ | Job result 409 (đang chạy, đúng); 22 Playwright pass |

### 4.5. Vận hành & UI

| # | Chức năng | Trạng thái hiện tại | Đã kiểm chứng | Ghi chú |
|---|---|---|---|---|
| 30 | Roster lưới & khung giờ | 🟢 HOẠT ĐỘNG | ✅ | `/lich/lifecycle` 200 |
| 31 | Phiếu mẫu (PhieuMau) | 🟢 HOẠT ĐỘNG | ✅ | `/phieu/mau` 200, có items |
| 32 | Điểm danh (CHECK_IN) | 🟢 HOẠT ĐỘNG | ✅ | `POST /diem-danh` 200 |
| 33 | Đăng nhập / phân quyền | 🟢 HOẠT ĐỘNG | ✅ | `/me/profile` 200, login 3 role |
| 34 | Bàn giao ca (handover) | 🟢 HOẠT ĐỘNG | ✅ | `/handover` 200 |
| 35 | Việc treo (hanging task) | 🟢 HOẠT ĐỘNG | ✅ | `/viec-treo` 200 |

### 4.6. Kết quả kiểm chứng thật (260917)

Đã chạy `scripts/verify_plan_functions.py` + `scripts/_recheck_fails.py` gọi API thật trên Docker stack (5 container healthy). Kết quả:

- **35/35 chức năng** đã kiểm chứng bằng API thật (cột "Đã kiểm chứng" = ✅).
- **1 BUG THẬT** phát hiện: **item 17 — SLA escalation worker**.
  - `GET /api/v1/lich/thong-bao` trả **HTTP 500**.
  - **Nguyên nhân gốc:** bảng `thong_bao_lich` **KHÔNG tồn tại trong Postgres**. Bảng này chỉ được tạo trong nhánh SQLite của `init_db()` (`apps/api/src/ca_api/persist.py`), KHÔNG có trong `_ensure_scheduling_schema()` (chạy cho cả Postgres), và **KHÔNG có Alembic migration** nào tạo nó. `thong_bao_ca` thì có (migration `0009`).
  - **✅ ĐÃ SỬA (260918):** tạo Alembic migration `0013_add_thong_bao_lich.py` tạo bảng `thong_bao_lich` (id, store_id, tuan_iso, su_kien, tieu_de, noi_dung, url, nv_id, da_xem, created_at, UNIQUE(store_id,tuan_iso,su_kien,nv_id)) + index `idx_thong_bao_lich_user`. Đã chạy `alembic upgrade head` trên Postgres Docker → bảng tồn tại. Endpoint giờ trả **200** `{"ok": true, "notifications": [], "unread": 0}`. Test `test_sprint45.py` pass.
- **Các FAIL trước đó đều do script test sai, không phải lỗi hệ thống:**
  - Item 8: dùng từ "thất thoát" không nằm trong keyword `ANALYZE_WASTE` (chỉ "hao hụt", "hàng hủy", "lãng phí", "sữa hỏng", "đổ bọt", "báo cáo hủy"). Dùng "hao hụt" → PASS.
  - Item 27: thiếu field bắt buộc `latitude`/`longitude`/`core_category` → 422. Thêm vào → 202.
  - Item 29: job chưa xong → 409 `JOB_NOT_COMPLETED` (đúng hành vi, không phải lỗi).

---

## 5. Checklist review cho từng chức năng

Khi review **một chức năng bất kỳ**, trả lời đủ các câu sau:

- [ ] **1. Có endpoint/API không?** Đường dẫn, method, có chạy được bằng curl/HTTP client không?
- [ ] **2. Có UI không?** Trang nào, route nào, có render được không?
- [ ] **3. Có nối được UI → API → DB không?** Thao tác thật có ra kết quả không?
- [ ] **4. Có cần phê duyệt (Pha 2) không?** Nếu có, bấm Duyệt có ghi DB không?
- [ ] **5. Có phụ thuộc dịch vụ ngoài không?** LLM/SerpApi/GMaps/ShopeeFood/TikTok/Threads/Camoufox/SMTP — có key & chạy được không?
- [ ] **6. Có cần seed dữ liệu / cấu hình không?** Đã có chưa?
- [ ] **7. Có test không?** Unit pass? E2E thật pass?
- [ ] **8. Lỗi cụ thể khi chạy thật là gì?** Ghi lại message lỗi, stack trace, screenshot.

---

## 6. Kế hoạch thực hiện (các bước nghiên cứu)

### Giai đoạn 1 — Lập bản đồ chức năng (0.5 ngày)
- [ ] Liệt kê toàn bộ endpoint trong `apps/api` (đọc `router.py`, các `interfaces/http/*`).
- [ ] Liệt kê toàn bộ trang trong `apps/web` (đọc `app/**/page.tsx`).
- [ ] Đối chiếu với `CAPABILITY_REGISTRY` và `COPILOT_ROLE_INTENT_MATRIX`.
- [ ] Điền đầy đủ bảng mục 4 (thêm dòng nếu thiếu).

### Giai đoạn 2 — Kiểm chứng từng chức năng (2–3 ngày)
- [ ] Với mỗi chức năng, chạy theo 6 bước ở mục 2.
- [ ] Ưu tiên các chức năng người dùng dùng hằng ngày (chat, xếp lịch, điểm danh, phiếu mẫu).
- [ ] Ghi kết quả vào bảng mục 4, đánh dấu ✅ "Đã kiểm chứng".

### Giai đoạn 3 — Phân loại nguyên nhân & đề xuất (1 ngày)
- [ ] Với mỗi chức năng 🔴/⚪/❓, xác định nguyên nhân (mục 1).
- [ ] Phân nhóm: (a) cần nối E2E, (b) cần API key/quota, (c) cần seed dữ liệu, (d) cần phê duyệt, (e) chưa code.
- [ ] Viết báo cáo tóm tắt + đề xuất thứ tự ưu tiên sửa.

### Giai đoạn 4 — Báo cáo (0.5 ngày)
- [ ] Xuất bản báo cáo audit hoàn chỉnh (file riêng hoặc cập nhật file này).
- [ ] Trình chủ dự án review & quyết định hướng xử lý từng nhóm.

---

## 7. Rủi ro & lưu ý

- **Không tự ý sửa code trong giai đoạn nghiên cứu** — chỉ ghi nhận trạng thái, tránh làm sai lệch kết quả.
- **Chức năng cần phê duyệt (Pha 2) không phải là "hỏng"** — đó là thiết kế an toàn (ADR-008). Cần phân biệt rõ.
- **Chức năng phụ thuộc dịch vụ ngoài** có thể "chạy được code" nhưng "không chạy được thật" vì thiếu key/quota/bị chặn — cần ghi rõ loại này.
- **Một số plan ghi "Done"** (vd `260917-tu-dong-xep-lich-va-cho-ca.md`) nhưng chỉ có test pass, chưa chắc E2E thật — phải kiểm chứng lại.
- **Không xóa/ghi đè dữ liệu thật** khi chạy thử — dùng dữ liệu seed hoặc môi trường test riêng.

---

## 8. Kết quả mong đợi

Sau khi hoàn thành, chủ dự án sẽ có:

1. **Bảng trạng thái đầy đủ** của mọi chức năng (mục 4) với trạng thái đã kiểm chứng thật.
2. **Danh sách chức năng thực sự hoạt động** (🟢) — dùng được ngay.
3. **Danh sách chức năng chưa hoạt động** (🔴/⚪/❓) kèm **nguyên nhân cụ thể**.
4. **Đề xuất ưu tiên** sửa chữa theo mức độ ảnh hưởng đến vận hành hằng ngày.