# RÀ SOÁT HOÀN THIỆN TÍCH HỢP JEV — KẾT QUẢ REVIEW CODE

> **Ngày:** 21/09/2026.
> **Phạm vi:** review toàn diện phần triển khai `SignalSensor` (Jev + Regex) tích hợp vào NHỊP QUÁN, đối chiếu với kế hoạch JEV v2 và docs chính thức TypeSafe API.
> **Trạng thái:** ĐÃ HOÀN THIỆN — đã sửa các vấn đề phát hiện, tất cả cổng xanh.

---

## 1. ĐỐI CHIẾU DOCS CHÍNH THỨC (xác minh trong quá trình review)

| Hạng mục | Kế hoạch v2 | Docs TypeSafe thật | Kết luận |
|---|---|---|---|
| Endpoint | `/v1/system-one/jev` (v1) | **`POST /v1/systemone`** | ✅ Đã sửa |
| Request | `{state, questions}` | `{state, model, questions}` | ✅ Đã sửa thêm `model` |
| Response | `{signals: {...}}` | `{model, answers: {id: {type, ...}}}` | ✅ Đã sửa sang `answers` |
| Noul | không có confidence | đúng — không có confidence | ✅ Giữ |
| Score | 0-based, có thể lẻ | đúng — `score` có thể giữa các mức | ✅ Giữ |
| Choice | trả `choice` + `probabilities` + `confidence` | đúng | ✅ Đã khớp |
| Giới hạn | 255 choice, 64k token | đúng | ✅ Trong biên |

## 2. CÁC VẤN ĐỀ PHÁT HIỆN TRONG REVIEW & ĐÃ SỬA

### 🔴 V1. Chưa nối vào pipeline thật (quan trọng nhất)
`JevSensor`/`RegexSensor`/`route_fb` chỉ tồn tại trong test/demo, **chưa được gọi từ luồng xử lý tin nhắn thật**.
→ **Đã sửa:** tích hợp vào `apps/api/src/ca_api/services/fb_moderation.py`:
- Gọi `_jev_flags()` trước `decide()` (L4) — đổ tín hiệu Jev vào `PolicyContext` qua các flag `jev_*`.
- `decide()` giữ nguyên là **bảng quyết định duy nhất** (đúng review A1).
- Thêm `_check_jev_injection()` (L3.5) — lớp lọc injection Jev bổ trợ regex, chỉ tăng leo thang.

### 🔴 V2. Hai bảng quyết định song song
`route_fb()` (trong sensors) và `decide()` (trong fb_policy) cùng tồn tại, dễ không nhất quán.
→ **Giải quyết:** pipeline thật dùng `decide()` (qua `ctx.jev_*`). `route_fb()` giữ làm module tách biệt, có test riêng, dùng cho mục đích thử nghiệm/minh họa bảng §4.2. Không trùng lặp trong luồng chính.

### 🟡 V3. Câu hỏi mơ hồ khi không truyền `questions`
`_call_api` tự dựng câu hỏi chung chung "Evaluate the state" — vô nghĩa.
→ **Đã sửa:** `evaluate()` **bắt buộc** có `questions`, thiếu → fail-closed (không gọi mạng).

### 🟡 V4. Thiếu ẩn danh hóa (kế hoạch §6)
Tên/SĐT gửi thẳng lên API bên thứ ba.
→ **Đã thêm:** `anonymize_state()` trong `fb_questions.py`:
- Mask SĐT Việt Nam → `KH_SDT`.
- Mask tên qua `name_map` (vd: `Lan` → `NV_02`) + heuristic chuỗi Capitalized 2 từ+.
- Có danh sách ngoại lệ (Quán, Menu, thứ trong tuần...) để tránh mask nhầm.
- Đệ quy vào dict/list lồng nhau.

### 🟡 V5. Thiếu lớp lọc injection/jailbreak (kế hoạch §4.3)
→ **Đã thêm:** `INJECTION_QUESTIONS` (2 câu: ghi đè chỉ dẫn, đòi dữ liệu nội bộ) + `_check_jev_injection()` trong pipeline. Fail-closed an toàn: Jev tắt/lỗi → không chặn vô tội vạ, không cấp thêm quyền.

### 🟡 V6. Circuit breaker đếm nhầm "thiếu key" là lỗi transient
`not api_key` → `_record_failure()` → bật breaker vĩnh viễn (không phải lỗi transient).
→ **Đã sửa:** thiếu key KHÔNG đếm vào breaker; chỉ lỗi mạng/5xx/429/timeout mới đếm. Có test riêng xác nhận.

### 🟡 V7. Test phụ thuộc env dev
Env có `JEV_ENABLED=true` + key → test gọi API thật (chậm, flaky, tốn token).
→ **Đã sửa:** ép tắt Jev trong cả 2 conftest:
- `apps/api/tests/conftest.py`
- `packages/agents/tests/conftest.py`
(`monkeypatch.delenv("JEV_ENABLED")` + `delenv("JEV_API_KEY")`).

### 🟢 V8. `urllib` blocking trong async FastAPI
→ **Ghi nhận cho sau:** hiện `_call_api()` dùng `urllib.request.urlopen` (blocking). Với FastAPI async, nên chuyển sang `httpx.AsyncClient` hoặc chạy trong thread pool khi đưa vào luồng async thật. Chưa chặn hiện tại vì `fb_moderation.moderate_fb_message` là sync function (chạy trong executor của framework).

## 3. CẤU TRÚC HOÀN CHỈNH

```
packages/agents/src/ca_agents/sensors/
├── port.py            # Signal/SensorResult/SignalSensor Protocol
├── regex_sensor.py    # RegexSensor (tất định, không I/O)
├── jev_sensor.py      # JevSensor (HTTP, circuit breaker, replay, kill-switch)
├── fb_route.py        # route_fb() — bảng quyết định §4.2 (minh họa/test)
└── fb_questions.py    # FB_QUESTIONS, INJECTION_QUESTIONS, anonymize_state

apps/api/src/ca_api/services/fb_moderation.py
├── _get_jev_sensor()      # lazy singleton, đọc env
├── _jev_flags()           # gọi Jev → PolicyContext(jev_*=...)
├── _check_jev_injection() # lọc injection Jev (đơn điệu)
└── moderate_fb_message()  # L1 → L3.5 (Jev injection) → L4 (Jev flags) → L5
```

## 4. KẾT QUẢ XÁC MINH (cập nhật 21/09)

| Cổng | Kết quả |
|---|---|
| ruff | ✅ sạch |
| mypy --strict | ✅ sạch (9 file) |
| pytest sensors + fb_policy + fb_questions + fb_policy_api | ✅ **107 passed** |
| pytest fb_moderation API | ✅ **48 passed** |
| API Jev thật (demo) | ✅ `ok=True`, nhận diện đúng 5 tín hiệu, `escalate_owner` |

## 5. CÒN LẠI (cập nhật 21/09 — đã hoàn thành 2 mục)

Trạng thái mới nhất:
- ~~3. Replay persist (ADR-007)~~ → ✅ **ĐÃ XONG**: `_jev_flags()` ghi `audit_add` (jev_success/jev_failed) với signals đã parse + latency + model, không text thô.
- ~~4. Kill-switch runtime~~ → ✅ **ĐÃ XONG**: `fb_jev_enabled()` đọc KV (`jev_enabled`) thắng env; `PUT /api/v1/page/fb-policy` nhận `jev_enabled`; sensor cache reset ngay.

Còn lại thực sự:
1. **Async HTTP** (V8) — `JevSensor._call_api` dùng `urllib` sync. Hiện `moderate_fb_message` là sync (chạy executor của FastAPI) nên **chấp nhận được**; cần chuyển `httpx.AsyncClient` nếu gọi từ handler async trực tiếp.
2. **Hiệu chỉnh ngưỡng trên tập vàng** (§7) — cần dữ liệu thực của quán (300–500 tin gán nhãn).
3. **Nhân viên thông báo** (kế hoạch §6) — quyết định kinh doanh (gửi khi nào/cho ai). Hạ tầng sẵn có: `thong_bao_ca_create()`.

## 6. UI & tài liệu (cập nhật 21/09 — ĐÃ HOÀN THIỆN)

- **UI `/page-quan/fb-inbox`**: thêm toggle **Jev** cho Chủ quán (riêng khỏi toggle auto-send) — bật/tắt không cần deploy, hiển thị trạng thái cảm biến. `tsc --noEmit` sạch.
- **E2E mock**: thêm `jev_enabled` vào mock `fb-policy` cho khớp API thật.
- **Runbook** `fb-chatbot-moderation.md`: thêm mục 2b (bật/tắt Jev, fail-closed khi lỗi, ẩn danh hóa).