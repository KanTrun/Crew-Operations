# QA ĐỢT 3 — Kiểm thử sau deploy production (2026-09-26)

> **Môi trường:** https://nhipquan.duckdns.org (production, đã deploy PR #74 + #76)
> **Vai kiểm thử:** `hung` (chu_quan) và `minh` (nhan_vien)
> **Mục đích:** demo lại toàn hệ thống sau khi fix 10 lỗi + tìm lỗi mới

---

## 1. Kiểm chứng các fix đã deploy — TẤT CẢ PASS ✅

| Fix | Kiểm tra | Kết quả |
|-----|----------|---------|
| #7 Shadow API `/skills` | `GET /api/v1/skills` | ✅ 200 · JSON · 13 skill |
| #4 Quyền `/skills` | Trang `/skills` với chu_quan | ✅ 200 · "13/13 KỸ NĂNG SẴN SÀNG" |
| #4 Quyền `/skills` với nhân viên | `/skills` với `minh` | ✅ Mở (đúng — STAFF_ACCESS) |
| #6 Security headers | `GET /health` | ✅ `nosniff` · `DENY` · `no-referrer` · `Permissions-Policy` · CSP |
| #8 Redact tên | `GET /api/v1/contracts` | ✅ `"Lan N."` + `la_du_lieu_mo_phong: true` |
| #5 WebSocket 502 | `wss://.../ws/chat` | ✅ **OPEN-OK** (Caddy reload hoạt động) |
| #1/#2 Dedupe mẫu/luật | `/api/v1/ops/predict/suggestions` | ✅ **3 mẫu / 3 luật** (trước 21, chỉ 3 unique) |
| #3 Lệch số bàn giao | `POST /api/v1/handover` với 2 mức tiền | ✅ trả `co_lech_so` + `vf_number_conflict` (test đơn vị) |

---

## 2. RBAC đợt 3 — 100% ĐÚNG ✅

Đăng nhập `minh` (nhan_vien), thử 9 route:

| Route | Kết quả | Đánh giá |
|-------|---------|----------|
| `/quanverse/war-room` | 🔒 BLOCKED | ✅ |
| `/quanverse/rules` | 🔒 BLOCKED | ✅ |
| `/quanverse/shift-rescue` | 🔒 BLOCKED | ✅ |
| `/vet` | 🔒 BLOCKED | ✅ |
| `/roster` | 🔒 BLOCKED | ✅ |
| `/inbox` | 🔒 BLOCKED | ✅ |
| `/khao-sat-gia` | 🔒 BLOCKED | ✅ |
| `/cam-nang` | 🔓 Mở | ✅ (STAFF_ACCESS — NV xem được luật) |
| `/skills` | 🔓 Mở | ✅ (STAFF_ACCESS — sau fix #4) |

**Sidebar cũng đúng:** với nhân viên, menu ẩn hết mục quản lý (Roster, Inbox, Vết, Khảo sát giá) — chỉ hiện 20 mục dành cho nhân viên.

---

## 3. Lỗi/vấn đề MỚI phát hiện trong đợt 3

### ⚠️ #11 (P3) — `/api/v1/experience/shift-rescue/options` dùng ID nhân viên khác định dạng

- **Hiện tượng:** response API trả `nv_id: "nv_1"`, `"nv_absent_quan"` — trong khi toàn hệ thống dùng `nv_01`..`nv_19` (xem `GET /api/v1/nguoi`).
- **Mức ảnh hưởng thực tế: THẤP** — đã kiểm trên UI `/quanverse/shift-rescue`: giao diện hiển thị **tên người** ("Quân", "Lan"), KHÔNG lộ ID ra màn hình. Chỉ khi gọi API trực tiếp mới thấy ID khác định dạng.
- **Nguyên nhân:** endpoint đọc thuần fixture `data/fixtures/grand_experience/shift-rescue.json` (ID tự đặt), không map sang NV thật trong DB.
- **Ghi chú:** comment trong `shift_rescue.py:74` giải thích đây là **chủ đích** cho bề mặt Grand Experience (ADR-016, sản phẩm riêng, không điều phối qua chat).
- **Rủi ro tiềm ẩn:** nếu sau này nối Shift Rescue với lịch thật (gửi lời mời tới NV), ID sẽ không khớp.
- **Đề xuất:** map `nv_1`→`nv_01`, `nv_absent_quan`→`nv_09` khi đọc fixture — hoặc để nguyên vì hiện là fixture demo.
- **Kết luận:** **KHÔNG chặn demo**, không cần sửa trước cuộc thi.

### ⚠️ #12 (P3) — 4 endpoint "chẩn đoán nội bộ" public không cần token

`GET /api/v1/ab` · `GET /api/v1/vf/conflict` · `GET /api/v1/vf/conflict-demo` · `GET /api/v1/reservations-metrics` — đều trả 200 khi không có token.

- **Đánh giá:** **không lộ dữ liệu nhạy cảm** — đã kiểm nội dung: chỉ số liệu demo/fixture ("chưa đo live", claim mẫu `nv_03`, đếm reservation = 0).
- **Ghi chú:** các endpoint này **có chủ đích** nằm trong `EXCLUDED_ROUTES` của coverage test với lý do "chẩn đoán nội bộ". Điểm chưa nhất quán: gọi là "nội bộ" nhưng không đòi đăng nhập.
- **Đề xuất:** thêm `_require_role()` nếu muốn siết — ưu tiên thấp, xử lý sau cuộc thi.
- **Xếp loại:** **KHÔNG chặn demo**, không rò dữ liệu.

### ✅ #13 (không phải lỗi) — Chấp nhận được

| Kiểm tra | Kết quả | Kết luận |
|----------|---------|----------|
| `POST /api/v1/tkb/confirm` với `khoang_ban: []` | 400 `khoang_rong` | ✅ validation đúng |
| `GET /api/v1/experience/war-room/scenarios/x` (id sai) | 404 `simulation_not_found` | ✅ fail-closed đúng |
| `GET /api/v1/users/emails` | `{"emails":{}}` | ✅ không rò email khi chưa đăng ký |

---

## 4. Bề mặt đã test đợt 3 (mở rộng so với đợt 1-2)

| Trang | Vai | Trạng thái | Ghi chú |
|-------|-----|-----------|---------|
| `/quanverse` | chu_quan | ✅ render | "Một trạng thái quán, bốn bản chiếu theo vai trò" |
| `/quanverse/spatial-memory` | chu_quan | ✅ render | "HỒN QUÁN — Không gian ký ức" |
| `/quanverse/war-room` | chu_quan | ✅ render | "So sánh phương án nếu…thì…" |
| `/quanverse/shift-rescue` | chu_quan | ✅ render | "Báo vắng đột xuất → danh sách người thay" |
| `/quanverse/rules` | chu_quan | ✅ render | "Quán tự viết luật" |
| `/pha` | chu_quan | ✅ render | "Màn hình pha chế — ba cột chờ/đang/xong" |
| `/them` | chu_quan | ✅ render | "Tất cả lối vào" nav overflow |
| `/contracts` | chu_quan | ✅ render | 5 hợp đồng dữ liệu ADR-012 |
| `/huong-dan` | chu_quan | ✅ render | Bản đồ hệ thống |
| `/hao-hut` (API) | chu_quan | ✅ 200 | sổ hao hụt + ngưỡng theo mặt hàng |
| `/api/v1/experience/*` | chu_quan | ✅ 200 | capabilities theo vai (`experience.confirm`…) |

---

## 6. Bề mặt CHƯA test (ghi nhận để minh bạch)

| Bề mặt | Lý do chưa test | Rủi ro |
|--------|-----------------|--------|
| Luồng Facebook Page (duyệt/đăng phản hồi) | `NHIPQUAN_FB_AUTO_SEND=1` → sợ đăng thật lên Page công khai | 🟡 cần quyết định trước demo |
| Khảo sát giá (tạo job) | Tốn quota SerpApi thật | 🟢 có job cache sẵn để demo |
| Gửi mail thật (SMTP) | Cần kiểm soát hộp thư | 🟢 proposal vẫn minh bạch nếu dừng |
| Voice (Gemini Live) | Cần Chrome + mic ổn định | 🟢 dự phòng chat text |
| Telegram/Zalo live | Chưa nạp token vào stack | 🟢 replay vẫn demo được |

---

## 7. Khuyến nghị trước demo

| Ưu tiên | Việc | Ghi chú |
|---------|------|---------|
| **P0** | Quyết định `NHIPQUAN_FB_AUTO_SEND` (0 hay 1) | Nếu demo luồng Page: đặt `0` để không đăng thật |
| **P1** | Rehearse lại script 13 STEP (Mục 12 của `DEMO_PLAN.md`) | Đảm bảo khớp dữ liệu hiện tại sau deploy |
| **P2** | Quay video dự phòng bản 10 phút | Bảo hiểm mạng hội trường |
| **P3** | Xử lý #11 (map ID fixture) + #12 (siết endpoint chẩn đoán) | Sau cuộc thi |

---

## 8. Kết luận đợt 3

| Hạng mục | Kết quả |
|----------|---------|
| Fix đã deploy (8 mục kiểm chứng) | ✅ **8/8 PASS** |
| RBAC (9 route × vai nhân viên) | ✅ **9/9 ĐÚNG** |
| Bề mặt mới test (11 trang/API) | ✅ tất cả render/hoạt động |
| **Lỗi mới phát hiện** | **2** (1×P3 ID fixture khác định dạng — UI không lộ, 1×P3 public endpoint chẩn đoán) |
| Lỗi chặn demo | **0** |
| Rò dữ liệu nhạy cảm | **0** |

**Đánh giá tổng:** hệ thống **sẵn sàng demo**. Cả 2 vấn đề mới đều ở bề mặt phụ (Grand Experience fixture + endpoint chẩn đoán), **không ảnh hưởng luồng chính, không chặn cuộc thi**. Ghi nhận để xử lý sau.
