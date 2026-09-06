# KẾ HOẠCH HOÀN CHỈNH: Hệ Thống Chat Nội Bộ Chuẩn Messenger
## Dự án: NHỊP QUÁN — Chat Nội Bộ Toàn Chi Nhánh (v2.0 — Bản Chuẩn Doanh Nghiệp)

> Bản kế hoạch này kế thừa toàn bộ ý tưởng UX từ bản gốc, đồng thời bổ sung các phần còn thiếu để đạt chuẩn doanh nghiệp: vòng đời tài khoản đầy đủ (bao gồm offboarding), bảo mật, khả năng mở rộng, vận hành sau triển khai, và tiêu chí nghiệm thu rõ ràng cho từng bước.

---

## 0. Tổng Quan & Mục Tiêu

| Hạng mục | Nội dung |
|---|---|
| Mục tiêu chính | Xây kênh liên lạc nội bộ real-time cho toàn bộ nhân sự 1 chi nhánh, trải nghiệm giống Messenger |
| Yêu cầu bắt buộc | Nhóm chung toàn quán, auto-join 100% khi có tài khoản mới, không thể rời/kick khỏi nhóm chung |
| Đối tượng dùng | Chủ quán (Owner), Quản lý (Manager), Nhân viên (Staff) |
| Nền tảng | Web app (PWA) — ưu tiên tối ưu di động vì nhân viên dùng khi đang làm ca |
| Ngoài phạm vi (Out of scope, giai đoạn 1) | Chat đa chi nhánh (cross-store), gọi video/voice call, chat với khách hàng bên ngoài |

**Giả định kỹ thuật** (điều chỉnh nếu khác thực tế dự án):
- Backend: Python (`ca_api/`), lưu trữ SQLite (dev) / PostgreSQL (production)
- Frontend: TypeScript, `apps/web/`, kiến trúc kiểu Next.js/React + WebSocket client
- Xác thực hiện có: JWT token cấp khi đăng nhập/đăng ký

---

## 1. Kiến Trúc Tổng Thể

```
┌─────────────┐      REST (CRUD)       ┌──────────────────┐
│  apps/web   │ ─────────────────────▶ │   ca_api (HTTP)   │
│  (React/TS) │                        │  chat.py router   │
│             │      WebSocket (WS)    │                    │
│  useChatClient ◀────────────────────▶│  chat_ws.py        │
└─────────────┘                        │  ConnectionManager │
                                        └─────────┬──────────┘
                                                  │
                                        ┌─────────▼──────────┐
                                        │  Postgres/SQLite    │
                                        │  chat_* tables      │
                                        │  + Redis (pub/sub)  │
                                        │    [khi scale >1    │
                                        │     instance]       │
                                        └─────────────────────┘
```

**Lưu ý khả năng mở rộng**: Nếu hệ thống chỉ chạy 1 process/1 chi nhánh, `ConnectionManager` in-memory là đủ. Nếu dự kiến scale ngang (nhiều instance backend, nhiều chi nhánh dùng chung hạ tầng), **bắt buộc** dùng Redis Pub/Sub hoặc tương đương để đồng bộ broadcast giữa các instance — ghi rõ quyết định này trước khi code Bước 2.

---

## 2. Mô Hình Dữ Liệu (Schema)

### 2.1. Các bảng chính

```sql
-- Cuộc trò chuyện (1-1, nhóm tự tạo, hoặc nhóm chung toàn quán)
CREATE TABLE chat_conversations (
    id              TEXT PRIMARY KEY,        -- vd: conv_general_quan_01
    store_id        TEXT NOT NULL,
    type            TEXT NOT NULL,           -- 'general' | 'direct' | 'group' | 'shift_auto'
    display_name    TEXT NOT NULL,
    avatar_url      TEXT,
    is_locked       BOOLEAN DEFAULT FALSE,   -- TRUE cho nhóm chung: không cho rời/kick
    created_at      TIMESTAMP DEFAULT now(),
    updated_at      TIMESTAMP DEFAULT now()
);

-- Thành viên trong từng cuộc trò chuyện
CREATE TABLE chat_participants (
    conversation_id TEXT NOT NULL REFERENCES chat_conversations(id),
    nv_id           TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'member',  -- 'admin' | 'member'
    status          TEXT NOT NULL DEFAULT 'active',  -- 'active' | 'archived' (dùng khi offboard)
    muted           BOOLEAN DEFAULT FALSE,
    last_read_at    TIMESTAMP,
    joined_at       TIMESTAMP DEFAULT now(),
    archived_at     TIMESTAMP,
    PRIMARY KEY (conversation_id, nv_id)
);

-- Tin nhắn
CREATE TABLE chat_messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES chat_conversations(id),
    sender_id       TEXT NOT NULL,           -- NULL/system cho tin nhắn hệ thống
    type            TEXT NOT NULL,           -- 'text' | 'image' | 'voice' | 'system' | 'ops_card'
    content         TEXT,                    -- text hoặc URL media, đã qua sanitize
    reply_to_id     TEXT REFERENCES chat_messages(id),
    is_unsent       BOOLEAN DEFAULT FALSE,
    edited_at       TIMESTAMP,
    metadata        JSONB,                   -- vd: waveform data, kích thước ảnh, ops_card payload
    created_at      TIMESTAMP DEFAULT now()
);

-- Reactions
CREATE TABLE chat_reactions (
    message_id      TEXT NOT NULL REFERENCES chat_messages(id),
    nv_id           TEXT NOT NULL,
    emoji           TEXT NOT NULL,           -- giới hạn 6 loại cố định
    created_at      TIMESTAMP DEFAULT now(),
    PRIMARY KEY (message_id, nv_id)
);

-- Trạng thái đã đọc (để hiện avatar Seen)
CREATE TABLE chat_read_receipts (
    conversation_id TEXT NOT NULL,
    nv_id           TEXT NOT NULL,
    last_read_message_id TEXT,
    read_at         TIMESTAMP,
    PRIMARY KEY (conversation_id, nv_id)
);
```

### 2.2. Chỉ mục (Index) bắt buộc
- `chat_messages(conversation_id, created_at DESC)` — phục vụ phân trang cuộn tin nhắn.
- `chat_participants(nv_id, status)` — phục vụ lấy nhanh danh sách hộp thư của 1 người.
- Full-text index trên `chat_messages.content` (Postgres `tsvector` hoặc SQLite FTS5) — phục vụ tìm kiếm tin nhắn (mục 4.9).

---

## 3. Vòng Đời Tài Khoản Trong Hệ Thống Chat (Bổ sung quan trọng)

Đây là phần **bị thiếu ở bản kế hoạch gốc** — bản gốc chỉ xử lý lúc gia nhập, không xử lý lúc rời đi.

### 3.1. Khi tạo tài khoản mới (Onboarding — giữ nguyên ý tưởng gốc)
1. `register()` tạo user → cấp `nv_id`.
2. Hook tự động: `chat_participant_add(conv_general_{store_id}, nv_id, role='member', status='active')`.
3. Tạo tin nhắn hệ thống chào mừng trong nhóm chung.
4. Broadcast qua WebSocket: `user:joined` cho toàn quán đang online.
5. Trả token đăng nhập, FE tự mở sẵn Nhóm Chung.

### 3.2. Khi nhân viên nghỉ việc / bị vô hiệu hóa (Offboarding — MỚI)
1. Khi admin/chủ quán set `user.status = 'inactive'` (hoặc xóa tài khoản):
   - Hook `chat_participant_deactivate(nv_id)`: set `status='archived'` cho **mọi** conversation mà người này tham gia (không xóa dữ liệu — giữ lịch sử để đối soát/tra cứu sau này).
   - Ngắt kết nối WebSocket hiện tại của `nv_id` ngay lập tức (force disconnect).
   - Vô hiệu hóa mọi token JWT cũ của người này (nếu hệ thống có blacklist/refresh token).
   - Nhóm chung và các nhóm khác **không hiển thị** người này trong danh sách online, không gửi thông báo mới cho họ.
2. Dữ liệu tin nhắn cũ do người này gửi **vẫn hiển thị bình thường** cho các thành viên còn lại (không xóa ngược lịch sử).
3. Ghi log sự kiện offboarding vào `audit_log` (ai thực hiện, thời điểm, lý do nếu có).

### 3.3. Chính sách dữ liệu cá nhân (tham chiếu Nghị định 13/2023/NĐ-CP)
- Ghi rõ trong tài liệu nội bộ: thời gian lưu trữ tin nhắn/voice note/ảnh (đề xuất mặc định 12 tháng, có thể cấu hình).
- Khi nhân viên nghỉ và yêu cầu xóa dữ liệu cá nhân theo quyền của họ, cần quy trình xử lý riêng (ngoài phạm vi code tự động, nhưng cần có endpoint admin hỗ trợ xóa/ẩn theo yêu cầu).

---

## 4. Bộ Tính Năng Đầy Đủ (Feature Set — đã bổ sung phần thiếu)

### A. Nhắn tin & Real-time
1. Chat 1-1, chat nhóm tự tạo, nhóm chung toàn quán (khóa cứng, không rời được), nhóm tự động theo ca.
2. Online/Offline indicator, Typing indicator, Seen receipts (avatar thu nhỏ).
3. **Trạng thái tin nhắn 3 cấp**: Sent → Delivered → Seen (bản gốc chỉ có Seen).
4. Reactions (6 loại cố định), Quote reply, Unsend (15 phút).
5. **Sửa tin nhắn (Edit)** trong 15 phút đầu, hiển thị nhãn "đã chỉnh sửa" *(bổ sung mới)*.
6. Ghim tin nhắn (Admin/Manager).
7. **@mention cá nhân** trong nhóm đông người, kèm thông báo riêng cho người được tag *(bổ sung mới)*.
8. **Tắt thông báo (Mute) theo từng cuộc trò chuyện** — quan trọng để nhân viên không bị làm phiền khi đang nghỉ ca *(bổ sung mới)*.
9. **Tìm kiếm tin nhắn (full-text search)** trong 1 cuộc trò chuyện hoặc toàn bộ *(bổ sung mới)*.

### B. Đa phương tiện
1. Voice note (MediaRecorder API, waveform, giới hạn thời lượng ví dụ 3 phút, giới hạn dung lượng).
2. Gửi ảnh (chụp trực tiếp / dán Ctrl+V), lightbox xem full màn hình.
3. Emoji picker.
4. **Giới hạn & validate file upload**: kiểm tra MIME type thực (magic bytes) chứ không chỉ đuôi file, giới hạn dung lượng (vd ảnh ≤10MB, voice ≤5 phút) *(bổ sung bảo mật)*.

### C. Nghiệp vụ quán cà phê
1. Ops Card đổi ca (Đồng ý/Từ chối ngay trong chat).
2. Báo hỏng thiết bị / tạo handover từ ảnh.
3. `@copilot` AI trợ lý trong chat.

### D. Giao diện
1. Trang `/chat` 3 cột, responsive PWA.
2. Floating Chat Head (widget nổi) trên toàn bộ AppShell.
3. Âm thanh "ting" khi có tin nhắn mới (chỉ hoạt động khi tab đang mở).
4. **Web Push Notification** cho PWA — bắn thông báo cả khi app không mở tab, dùng Service Worker + Push API *(bổ sung mới, quan trọng cho nhân viên không cầm điện thoại liên tục)*.

---

## 5. Bảo Mật & Kiểm Soát Rủi Ro (Phần bổ sung bắt buộc)

| Rủi ro | Biện pháp |
|---|---|
| Token lộ qua query string WebSocket (`?token=...` bị log ở proxy/CDN) | Gửi token qua WebSocket subprotocol header hoặc message xác thực đầu tiên sau khi mở kết nối, không đặt trên URL |
| Stored XSS qua nội dung tin nhắn | Sanitize input phía server trước khi lưu DB (loại bỏ HTML/script tag), escape khi render phía FE |
| Upload file độc hại (giả extension) | Kiểm tra magic bytes, giới hạn kích thước, quét virus cơ bản nếu có thể, lưu ngoài webroot |
| Spam / DoS nhẹ qua gửi tin liên tục | Rate limit theo `nv_id` (vd tối đa 20 tin/phút), giới hạn kết nối WebSocket đồng thời trên 1 tài khoản |
| Không truy vết được hành động Admin (xóa tin, đổi tên nhóm, kick...) | Bảng `audit_log` ghi ai/khi nào/hành động gì |
| Cựu nhân viên vẫn truy cập được chat sau khi nghỉ | Xử lý ở Mục 3.2 (offboarding hook) |
| Dữ liệu chat phình to vô hạn (`data/uploads/chat/`) | Cron job dọn file quá hạn lưu trữ (theo chính sách Mục 3.3), archive định kỳ |
| Broadcast không đồng bộ khi scale nhiều instance | Dùng Redis Pub/Sub cho `ConnectionManager` nếu có >1 backend instance |

---

## 6. Lộ Trình Triển Khai (7 Bước — đã thêm Bước 0 và Bước 6)

```
[Bước 0: Thiết kế & Chốt kỹ thuật trước khi code]
                       │
                       ▼
[Bước 1: DB Schema + Auto-join + Offboarding Hook]
                       │
                       ▼
[Bước 2: WebSocket Engine & REST APIs + Bảo mật cơ bản]
                       │
                       ▼
[Bước 3: Giao diện Chat Web & PWA (/chat)]
                       │
                       ▼
[Bước 4: Đa phương tiện & Tính năng nâng cao]
                       │
                       ▼
[Bước 5: Floating Widget & Tích hợp Nghiệp vụ Quán]
                       │
                       ▼
[Bước 6: Vận hành, Giám sát & Go-live]
```

### Bước 0 — Thiết kế & Chốt kỹ thuật (MỚI)
- [ ] Chốt schema DB cuối cùng (Mục 2), review với team.
- [ ] Chốt API contract (request/response mẫu cho từng endpoint).
- [ ] Quyết định: có cần Redis Pub/Sub ngay từ đầu hay để sau (dựa trên số chi nhánh dự kiến).
- [ ] Chốt chính sách lưu trữ dữ liệu (thời gian giữ tin nhắn/media).
- [ ] Chốt giới hạn: dung lượng file, thời lượng voice note, rate limit số tin/phút.
- **Nghiệm thu**: Tài liệu thiết kế được duyệt, không cần sửa schema giữa chừng ở các bước sau.

### Bước 1 — DB Schema + Auto-join + Offboarding
- [ ] Tạo migration cho 5 bảng (Mục 2.1) + index (Mục 2.2).
- [ ] Hàm `_seed_chat_neu_trong()`: tạo `conv_general_{store_id}`, add toàn bộ user hiện có.
- [ ] Sửa `register()`: tự động `chat_participant_add(...)` + tin nhắn chào mừng + broadcast `user:joined`.
- [ ] **MỚI**: Hàm `chat_participant_deactivate(nv_id)` gọi khi tài khoản bị vô hiệu hóa — set `status='archived'` toàn bộ conversation liên quan.
- [ ] Unit test: tạo tài khoản mới → có trong nhóm chung; vô hiệu hóa tài khoản → status chuyển `archived`, không nhận tin mới.
- **Nghiệm thu**: 100% test pass, coverage cho cả 2 chiều vòng đời (join + leave).

### Bước 2 — WebSocket Engine & REST APIs
- [ ] `ChatConnectionManager`: quản lý kết nối theo `nv_id`, hỗ trợ force-disconnect (dùng cho offboarding).
- [ ] Xác thực WebSocket qua header/message đầu, KHÔNG qua query string.
- [ ] Endpoint REST: conversations, messages (phân trang), tạo hội thoại, upload (có validate magic bytes + giới hạn dung lượng).
- [ ] Rate limiting theo `nv_id` cho gửi tin nhắn.
- [ ] Sanitize nội dung tin nhắn trước khi lưu DB.
- [ ] Bảng `audit_log` + ghi log cho hành động Admin (xóa tin, đổi tên nhóm).
- [ ] Unit test: gửi/nhận 2 chiều, test rate limit, test upload file sai định dạng bị từ chối.
- **Nghiệm thu**: Không endpoint nào lộ token qua log; test bảo mật cơ bản pass.

### Bước 3 — Giao diện `/chat`
- [ ] `useChatClient.ts`: kết nối WS, heartbeat, reconnect exponential backoff, optimistic UI.
- [ ] Sidebar (ghim Nhóm Chung đầu danh sách), ChatBox, InputBar.
- [ ] Typing indicator, Seen ngay khi mở khung chat.
- [ ] **MỚI**: Ô tìm kiếm tin nhắn (full-text) trong sidebar hoặc trong từng hội thoại.
- **Nghiệm thu**: Test tay 2 tài khoản nhắn qua lại mượt, không giật/lag khi mạng chập chờn (throttle network trong DevTools).

### Bước 4 — Đa phương tiện & Nâng cao
- [ ] Voice note (MediaRecorder, waveform, giới hạn thời lượng theo Bước 0).
- [ ] Gửi ảnh + lightbox.
- [ ] Reactions, Unsend, **Edit tin nhắn** (mới).
- [ ] **@mention cá nhân** + thông báo riêng (mới).
- [ ] **Mute theo hội thoại** (mới).
- [ ] Âm thanh "ting" + badge số tin chưa đọc trên AppShell.
- **Nghiệm thu**: Voice note ghi/phát đúng trên cả Android/iOS Safari (test thực tế, không chỉ giả lập).

### Bước 5 — Floating Widget & Nghiệp vụ Quán
- [ ] Floating Chat Head trong `AppShell.tsx`, popup 380x560px.
- [ ] Ops Card đổi ca (Đồng ý/Từ chối).
- [ ] `@copilot` tích hợp AI hỏi đáp trong chat.
- [ ] **Web Push Notification** (Service Worker) cho thông báo khi app không mở tab (mới).
- **Nghiệm thu**: Test kịch bản thực tế trên điện thoại tại quầy — vuốt chạm mượt, widget không che nút thao tác nghiệp vụ chính.

### Bước 6 — Vận hành, Giám sát & Go-live (MỚI — bổ sung bắt buộc)
- [ ] Thiết lập logging tập trung cho lỗi WebSocket/API (vd Sentry hoặc log file có cấu trúc).
- [ ] Alert khi tỷ lệ rớt kết nối WebSocket bất thường tăng cao.
- [ ] Cron job dọn dẹp file upload quá hạn lưu trữ (theo chính sách Bước 0).
- [ ] Kế hoạch backup riêng cho các bảng `chat_*` (tần suất, nơi lưu).
- [ ] Kế hoạch rollback: nếu go-live lỗi nghiêm trọng, có script tắt tính năng chat (feature flag) mà không ảnh hưởng các module khác (POS, lịch ca...).
- [ ] Load test: mô phỏng toàn bộ nhân viên 1 chi nhánh (~15-30 người) kết nối WebSocket đồng thời giờ cao điểm.
- **Nghiệm thu**: Hệ thống chạy ổn định 1 tuần thử nghiệm thật với toàn bộ nhân viên trước khi công bố chính thức "go-live".

---

## 7. Kế Hoạch Kiểm Thử Toàn Diện

### 7.1. Tự động (Automated)
- Unit test từng hook (auto-join, offboarding, rate limit, sanitize).
- Integration test REST + WebSocket 2 chiều.
- `npm run typecheck` không lỗi trong `apps/web`.
- **Test bảo mật cơ bản**: thử upload file giả mạo extension, thử gửi script trong tin nhắn, thử gửi >20 tin/phút để kiểm tra rate limit.

### 7.2. Thủ công (Manual)
- Kịch bản 2 tài khoản (Quản lý `lan`, Nhân viên `minh`) nhắn qua lại real-time.
- Kịch bản tạo tài khoản mới `hoang` → xác nhận vào nhóm chung + nhận tin chào mừng.
- **MỚI**: Kịch bản vô hiệu hóa tài khoản `hoang` → xác nhận không còn nhận tin mới, không xuất hiện trong danh sách online, nhưng lịch sử tin nhắn cũ vẫn hiển thị cho người khác.
- Test voice note, gửi ảnh, mở widget nổi tại `/quay`.
- **MỚI**: Test throttle mạng (giả lập 3G chậm/rớt mạng) để kiểm tra reconnect.
- **MỚI**: Test Web Push khi tắt hẳn tab trình duyệt.

### 7.3. Trước Go-live
- Load test với số lượng kết nối tương đương toàn bộ nhân viên 1 ca cao điểm.
- Chạy thử 1 tuần song song (chat thật + kênh liên lạc cũ) trước khi tắt hẳn kênh cũ.

---

## 8. Rủi Ro & Phương Án Giảm Thiểu (Tổng hợp)

| Rủi ro | Mức độ | Giảm thiểu |
|---|---|---|
| Cựu nhân viên còn quyền truy cập | Cao | Hook offboarding (Mục 3.2) |
| Lộ token qua log | Cao | Auth qua header, không qua query string |
| Nhóm chung bị spam làm phiền nhân viên đang nghỉ | Trung bình | Tính năng Mute (Mục 4.9) |
| Hệ thống sập khi đông người dùng cùng lúc | Trung bình | Load test Bước 6, cân nhắc Redis pub/sub sớm |
| Dữ liệu chat phình to, tốn ổ đĩa | Thấp | Cron dọn dẹp định kỳ |
| Nhân viên không nhận được thông báo khi không mở app | Trung bình | Web Push Notification (Mục 4.D.4) |

---

## 9. Tóm Tắt Thay Đổi So Với Bản Gốc

1. ➕ Thêm cơ chế offboarding đầy đủ (Mục 3.2) — điểm thiếu nghiêm trọng nhất của bản gốc.
2. ➕ Thêm Bước 0 (thiết kế trước khi code) và Bước 6 (vận hành sau go-live).
3. ➕ Thêm các biện pháp bảo mật cụ thể: auth WebSocket an toàn, sanitize input, validate upload, rate limit, audit log.
4. ➕ Thêm tính năng còn thiếu: tìm kiếm tin nhắn, @mention, mute, edit tin nhắn, Web Push.
5. ➕ Thêm lưu ý khả năng mở rộng (Redis pub/sub) và tham chiếu quy định pháp lý về dữ liệu cá nhân.
6. ➕ Thêm kế hoạch kiểm thử tải, kiểm thử mạng chập chờn, và giai đoạn chạy thử song song trước go-live.
