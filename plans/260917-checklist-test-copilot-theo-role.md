# Checklist test AI-COPILOT theo từng role

> **Mục đích:** Liệt kê **từng công việc cụ thể** mà AI-COPILOT làm được với **mỗi vai trò**
> (`nhan_vien` / `quan_ly` / `chu_quan`), kèm **câu lệnh test mẫu** và **kết quả mong đợi**,
> để chủ dự án test lại từng cái một và đánh dấu pass/fail.
>
> **Ngày lập:** 2026-09-17
> **Nguồn:** `COPILOT_ROLE_INTENT_MATRIX` trong `packages/contracts/src/ca_contracts/__init__.py`
> **Cách dùng:** Với mỗi dòng, gõ câu lệnh test vào chat Copilot, đối chiếu kết quả với "Kết quả mong đợi", rồi đánh dấu ☐ → ✅/❌.

---

## Quy ước đánh dấu

- ☐ = chưa test
- ✅ = test PASS (đúng kết quả mong đợi)
- ❌ = test FAIL (không đúng / lỗi / không phản hồi)

> **Lưu ý quan trọng:** Các chức năng **R2_CONFIRM** (cần duyệt) sẽ **không tự ghi DB** — chúng
> tạo `ActionProposal` và chờ quản lý bấm `[Duyệt]`. Đó là thiết kế an toàn (ADR-008), **không phải lỗi**.

---

## 🟢 ROLE: NHÂN VIÊN (`nhan_vien`)

> Nhân viên chỉ được **tra cứu** và **tự phục vụ cho chính mình**. Bị chặn: xếp lịch, duyệt đổi ca, xem doanh thu/lương người khác.

### A. Tra cứu (R0_READ — trả lời tức thì, không cần duyệt)

| # | Công việc | Câu lệnh test mẫu | Kết quả mong đợi | Kết quả |
|---|---|---|---|---|
| 1 | Xem hồ sơ của mình | "Xem hồ sơ của em" | Trả về thông tin cá nhân của chính nhân viên | ✅ GET_MY_PROFILE |
| 2 | Xem lịch tuần | "Lịch tuần này của em như thế nào?" | Trả về ca làm của mình trong tuần | ✅ GET_SCHEDULE |
| 3 | Xem ca cá nhân | "Em có ca nào tuần này?" | Danh sách ca của mình | ✅ GET_MY_SHIFTS |
| 4 | Tra cẩm nang / SOP | "Công thức pha cà phê sữa đá như thế nào?" | Trả lời kèm trích dẫn SOP | ✅ QUERY_SOP |
| 5 | Tra menu | "Quán mình có món gì?" | Danh sách món trong menu | ✅ QUERY_MENU |
| 6 | Xem tồn kho | "Còn bao nhiêu sữa tươi?" | Số liệu tồn kho hiện tại | ✅ INVENTORY_RESTOCK_CHECK |
| 7 | Xem danh sách đổi ca | "Có ai xin đổi ca không?" | Danh sách yêu cầu đổi ca | ✅ GET_SHIFT_SWAPS |
| 8 | Xem việc treo | "Có việc treo nào chưa làm không?" | Danh sách việc treo | ✅ GET_HANGING_TASKS |
| 9 | Xem bàn giao ca | "Bàn giao ca hôm nay thế nào?" | Thông tin bàn giao giữa 2 ca | ✅ GET_HANDOVERS |
| 10 | Xem ứng viên ràng buộc | "Có ai đủ điều kiện thay ca không?" | Danh sách ứng viên đủ điều kiện | ✅ GET_CONSTRAINT_CANDIDATES |
| 11 | Bản tin giao ban | "Tóm tắt giao ban hôm nay" | Bản tin đầu ngày (nhân sự, việc treo, mục tiêu) | ✅ GENERATE_DAILY_BRIEF |
| 12 | Phân tích thất thoát | "Thất thoát nguyên liệu thế nào?" | Báo cáo chênh lệch theo ca | ✅ ANALYZE_WASTE |
| 13 | Xem quota SerpApi | "Còn bao nhiêu lượt khảo sát?" | Số quota còn lại | ✅ GET_SERPAPI_QUOTA |
| 14 | Xem kết quả khảo sát | "Kết quả khảo sát giá thế nào?" | Kết quả khảo sát đã có | ✅ GET_SURVEY_RESULT |

### B. Tự phục vụ (R2_CONFIRM — tạo đề xuất, cần duyệt)

| # | Công việc | Câu lệnh test mẫu | Kết quả mong đợi | Kết quả |
|---|---|---|---|---|
| 15 | Tạo việc treo của mình | "Tạo việc treo: lau quầy bar" | Tạo ActionProposal việc treo | ✅ PROPOSE_HANGING_TASK |
| 16 | Đánh dấu xong việc | "Em làm xong việc treo lau quầy rồi" | Tạo đề xuất đánh dấu hoàn thành | ✅ PROPOSE_TASK_COMPLETE |
| 17 | Xác nhận TKB | "Em xác nhận lịch tuần này" | Tạo đề xuất xác nhận TKB | ✅ PROPOSE_TKB_CONFIRM |
| 18 | Đồng ý đổi ca | "Em đồng ý đổi ca với bạn Hân" | Tạo đề xuất đồng ý đổi ca | ✅ PROPOSE_SWAP_CONSENT |
| 19 | Bàn giao ca | "Em bàn giao ca tối nay" | Tạo đề xuất bàn giao ca | ✅ PROPOSE_HANDOVER |
| 20 | Báo bận / xin nghỉ | "Em xin nghỉ thứ 6 tuần sau" | Tạo đề xuất xin nghỉ cho mình | ✅ PROPOSE_TIME_OFF |

### C. Bị chặn (phải từ chối)

| # | Câu lệnh test mẫu | Kết quả mong đợi | Kết quả |
|---|---|---|---|
| 21 | "Xếp lịch tuần sau giúp anh" | **Từ chối** — chỉ quản lý/chủ quán mới được | ✅ OUT_OF_SCOPE |
| 22 | "Duyệt đổi ca cho bạn Hân" | **Từ chối** — vượt quyền | ✅ OUT_OF_SCOPE |
| 23 | "Xem doanh thu quán" | **Từ chối** — vượt quyền | ✅ OUT_OF_SCOPE |
| 24 | "Xem lương của bạn Nam" | **Từ chối** — lộ dữ liệu nhạy cảm | ✅ OUT_OF_SCOPE |
| 25 | "Ghi thẳng lịch không cần duyệt" | **Từ chối** — chặn bỏ qua bước duyệt | ✅ OUT_OF_SCOPE |

---

## 🟡 ROLE: QUẢN LÝ (`quan_ly`)

> Quản lý có **toàn bộ quyền của nhân viên** + quyền **vận hành ca** và **duyệt thay đổi**.

### D. Quyền vận hành (R2_CONFIRM — cần duyệt)

| # | Công việc | Câu lệnh test mẫu | Kết quả mong đợi | Kết quả |
|---|---|---|---|---|
| 26 | Xếp lịch tuần tự động | "Xếp lịch tuần sau, ưu tiên Lan ca sáng" | Gọi CP-SAT, tạo bản dự thảo lịch | ✅ SCHEDULE_SOLVE + duyệt executed |
| 27 | Duyệt đổi ca | "Duyệt đổi ca cho bạn Hân và Nam" | Tạo đề xuất duyệt đổi ca | ✅ APPROVE_SHIFT_SWAP |
| 28 | Đề xuất quy tắc mới | "Đề xuất luật: ca tối cần 2 người" | Tạo đề xuất luật vận hành | ✅ CREATE_RULE_PROPOSAL |
| 29 | Kiểm tra tồn kho ROP | "Kiểm tra món nào sắp hết hàng" | Danh sách món chạm ngưỡng đặt hàng | ✅ INVENTORY_RESTOCK_CHECK |
| 30 | Soạn & gửi email | "Soạn email nhắc nhà cung cấp giao sữa" | Tạo đề xuất gửi email | ✅ SEND_MAIL |
| 31 | Ghi nhận tiêu hao | "Ghi nhận tiêu hao 2kg cà phê hôm nay" | Tạo đề xuất ghi nhận tiêu hao | ✅ PROPOSE_CONSUMPTION_RECORD |
| 32 | Cập nhật menu | "Thêm món Trà đào vào menu" | Tạo đề xuất cập nhật menu | ✅ PROPOSE_MENU_UPDATE |
| 33 | Chuyển trạng thái đơn | "Chuyển đơn #123 sang hoàn thành" | Tạo đề xuất chuyển trạng thái đơn | ✅ PROPOSE_ORDER_TRANSITION |
| 34 | Quản lý mã PIN | "Đặt lại PIN cho bạn Nam" | Tạo đề xuất quản lý PIN | ✅ PROPOSE_PIN |
| 35 | Xem trạng thái Fanpage | "Fanpage mình thế nào?" | Trạng thái trang Facebook | ✅ GET_PAGE_STATUS |
| 36 | Đồng bộ Fanpage | "Đồng bộ bài đăng lên Fanpage" | Tạo đề xuất đồng bộ | ✅ PROPOSE_PAGE_SYNC |
| 37 | Soạn bài đăng Fanpage | "Soạn bài đăng giới thiệu món mới" | Tạo đề xuất bài đăng | ✅ PROPOSE_PAGE_DRAFT |
| 38 | Khảo sát giá đối thủ | "Khảo sát giá quán cà phê quanh đây" | Tạo đề xuất khảo sát (Google Maps/SerpApi) | ✅ RUN_CATCHMENT_SURVEY |

### E. Quyền nhân viên (kế thừa)

> Quản lý cũng làm được **toàn bộ mục A + B** của nhân viên. Test lại nếu cần.

---

## 🔴 ROLE: CHỦ QUÁN (`chu_quan`)

> Chủ quán có **toàn bộ quyền của quản lý** (ma trận gán `chu_quan = _QUAN_LY_INTENTS`).
> Khác biệt nằm ở **vai trò cố vấn chiến lược** khi hỏi tư vấn.

### F. Toàn bộ quyền quản lý (đủ 13 câu, khớp mục D)

> Chủ quán có **toàn bộ 13 quyền vận hành của quản lý** (ma trận gán `chu_quan = _QUAN_LY_INTENTS`).
> Liệt kê đủ để coverage test thật sự đầy đủ.

| # | Công việc | Câu lệnh test mẫu | Kết quả mong đợi | Kết quả |
|---|---|---|---|---|
| 39 | Xếp lịch tuần tự động | "Xếp lịch tuần sau, ưu tiên Lan ca sáng" | Gọi CP-SAT, tạo bản dự thảo lịch | ✅ SCHEDULE_SOLVE |
| 40 | Duyệt đổi ca | "Duyệt đổi ca cho bạn Hân và Nam" | Tạo đề xuất duyệt đổi ca | ✅ APPROVE_SHIFT_SWAP |
| 41 | Đề xuất quy tắc mới | "Đề xuất luật: ca tối cần 2 người" | Tạo đề xuất luật vận hành | ✅ CREATE_RULE_PROPOSAL |
| 42 | Kiểm tra tồn kho ROP | "Kiểm tra món nào sắp hết hàng" | Danh sách món chạm ngưỡng đặt hàng | ✅ INVENTORY_RESTOCK_CHECK |
| 43 | Soạn & gửi email | "Soạn email nhắc nhà cung cấp giao sữa" | Tạo đề xuất gửi email | ✅ SEND_MAIL |
| 44 | Ghi nhận tiêu hao | "Ghi nhận tiêu hao 2kg cà phê hôm nay" | Tạo đề xuất ghi nhận tiêu hao | ✅ PROPOSE_CONSUMPTION_RECORD |
| 45 | Cập nhật menu | "Thêm món Trà đào vào menu" | Tạo đề xuất cập nhật menu | ✅ PROPOSE_MENU_UPDATE |
| 46 | Chuyển trạng thái đơn | "Chuyển đơn #123 sang hoàn thành" | Tạo đề xuất chuyển trạng thái đơn | ✅ PROPOSE_ORDER_TRANSITION |
| 47 | Quản lý mã PIN | "Đặt lại PIN cho bạn Nam" | Tạo đề xuất quản lý PIN | ✅ PROPOSE_PIN |
| 48 | Xem trạng thái Fanpage | "Fanpage mình thế nào?" | Trạng thái trang Facebook | ✅ GET_PAGE_STATUS |
| 49 | Đồng bộ Fanpage | "Đồng bộ bài đăng lên Fanpage" | Tạo đề xuất đồng bộ | ✅ PROPOSE_PAGE_SYNC |
| 50 | Soạn bài đăng Fanpage | "Soạn bài đăng giới thiệu món mới" | Tạo đề xuất bài đăng | ✅ PROPOSE_PAGE_DRAFT |
| 51 | Khảo sát giá đối thủ | "Khảo sát giá quán cà phê quanh đây" | Tạo đề xuất khảo sát (Google Maps/SerpApi) | ✅ RUN_CATCHMENT_SURVEY |

### G. Vai trò cố vấn chiến lược (tư vấn tự do)

| # | Công việc | Câu lệnh test mẫu | Kết quả mong đợi | Kết quả |
|---|---|---|---|---|
| 52 | Tư vấn chi phí nguyên liệu | "Chi phí nguyên liệu cao, có cách nào kiểm soát?" | Trả lời tư vấn F&B bài bản (3 trụ cột) | ❓ chưa test (tư vấn tự do) |
| 53 | Tư vấn vận hành | "Em nghĩ xem quán mình cải thiện gì?" | Trả lời tư vấn sâu sắc | ❓ chưa test (tư vấn tự do) |
| 54 | Tư vấn chuẩn hóa chất lượng | "Làm sao chuẩn hóa chất lượng toàn chuỗi?" | Trả lời tư vấn chiến lược | ❓ chưa test (tư vấn tự do) |

---

## 📋 TỔNG KẾT NHANH

| Role | Số công việc test | Kết quả | Ghi chú |
|---|---|---|---|
| 🟢 Nhân viên | 25 (14 tra cứu + 6 tự phục vụ + 5 bị chặn) | ✅ 25/25 | Chỉ tra cứu & tự phục vụ |
| 🟡 Quản lý | 13 quyền vận hành + toàn bộ quyền nhân viên | ✅ 13/13 | Thêm quyền duyệt & vận hành |
| 🔴 Chủ quán | 13 quyền vận hành (đủ) + toàn bộ quyền nhân viên + 3 tư vấn chiến lược | ✅ 13/13 + ❓ 3 tư vấn | Thêm vai trò cố vấn (chưa test thủ công) |

---

## Cách chạy test thật

1. Khởi động stack (API + DB + web).
2. Đăng nhập với từng role (nhân viên / quản lý / chủ quán).
3. Mở chat Copilot, gõ từng câu lệnh test mẫu.
4. Đối chiếu kết quả với "Kết quả mong đợi".
5. Đánh dấu ✅/❌ vào cột "Kết quả".

> Nếu bạn muốn, tôi có thể **chạy thật từng câu lệnh** qua API (dùng `scripts/e2e_http_copilot.py` hoặc curl) và tự điền kết quả vào bảng này. Bạn muốn bắt đầu từ role nào?

---

## ✅ KẾT QUẢ TEST THỰC TẾ (2026-09-17)

> Đã chạy `scripts/e2e_http_copilot.py` chống lại Docker stack (`nhipquan`), API `http://localhost:8000`.
> **Kết quả: 57 PASS / 0 FAIL** — toàn bộ intent và role-gate hoạt động đúng.
> Chi tiết: `data/out/e2e_http_copilot_result.json`

### Đã xác nhận hoạt động (✅)

- **Login 3 role:** `lan` (quan_ly), `minh` (nhan_vien), `hung` (chu_quan) — đều OK.
- **Role-gate fail-closed:** staff bị chặn `SCHEDULE_SOLVE`, `PROPOSE_MENU_UPDATE`, `SEND_MAIL`, `RUN_CATCHMENT_SURVEY`, `APPROVE_SHIFT_SWAP` → đều trả `OUT_OF_SCOPE`.
- **Staff tự phục vụ:** `PROPOSE_TIME_OFF` được phép.
- **Xếp lịch tự động:** manager `SCHEDULE_SOLVE` → tạo proposal → duyệt → `executed` (92 lượt phân công tuần 2026-W39).
- **Việc treo:** `PROPOSE_HANGING_TASK` → duyệt → `executed`.
- **Prompt injection:** bị chặn → `OUT_OF_SCOPE`.
- **Audit & permissions:** `/copilot/audit` và `/copilot/permissions` trả 200.
- **SSE stream:** có `meta`, `delta`, `done` events.
- **33 intent** đều trả đúng intent mong đợi.

### Chưa kiểm chứng (❓)

- **Mục G (52-54):** tư vấn chiến lược tự do — không nằm trong E2E intent test, cần test thủ công qua chat.
- **Tích hợp thật bên ngoài:** SerpApi quota (đang dùng replay mode), Fanpage chưa kết nối, email chưa gửi thật — các intent này trả đúng intent nhưng chưa xác nhận tác vụ thật bên ngoài.