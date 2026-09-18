# Kế hoạch triển khai chi tiết — Tối ưu tính năng Ghi lại Cuộc họp (AG-MEETING)

> **Mục đích:** Triển khai tối ưu tính năng ghi lại cuộc họp (AI Meeting OS / AG-MEETING)
> theo báo cáo `260918-review-toi-uu-ag-meeting.md`, **ưu tiên giảm tải CPU/RAM server**
> và **ổn định với tài nguyên thấp nhất**, không làm mất các điểm mạnh hiện có
> (human-in-loop, rule-based fallback, chống hallucination, rollback).
>
> **Ngày lập:** 2026-09-18
> **Trạng thái:** ⏳ Kế hoạch — chờ chủ dự án review & duyệt từng giai đoạn
> **Phạm vi:** `packages/agents/.../ag_meeting/*`, `apps/api/.../http/meeting.py`, `apps/web/src/app/cuoc-hop/*`
> **Nguyên tắc:** Mỗi giai đoạn phải chạy test pass trước khi merge. Không đổi hành vi nghiệp vụ.

---

## 0. Bối cảnh & ngữ cảnh đầy đủ

### 0.1. Tính năng đang làm gì

AG-MEETING ghi lại cuộc họp giao ca / họp tuần / đào tạo qua 4 kênh (micro, Google Meet tab,
upload file, dán ghi chép), rồi:
1. **STT** (speech-to-text) bóc băng thoại → transcript có tách người nói.
2. **Trích xuất** transcript → biên bản có cấu trúc `CuocHop` (action items, đề xuất, điều chỉnh lịch, góp ý, audit SOP, bản tin ca).
3. **Làm rõ ngữ cảnh** — đối chiếu nhân viên + lịch ca thật.
4. **Duyệt** (chỉ Quản lý/Chủ quán) → ghi việc treo, đề xuất SOP, điều chỉnh lịch vào hệ thống.

### 0.2. Các file liên quan

| File | Dòng | Vai trò |
|---|---|---|
| `packages/agents/src/ca_agents/ag_meeting/stt.py` | 316 | STT: Gemini → Groq → Replay |
| `packages/agents/src/ca_agents/ag_meeting/extract.py` | 1055 | Trích xuất + rule-based fallback |
| `packages/agents/src/ca_agents/ag_meeting/clarify.py` | 262 | Làm rõ ngữ cảnh, gán ca |
| `packages/agents/src/ca_agents/prompts/ag_meeting/v2.md` | ~200 | Prompt LLM |
| `apps/api/src/ca_api/interfaces/http/meeting.py` | 771 | Router + apply + rollback + draft |
| `apps/web/src/app/cuoc-hop/page.tsx` | 1148 | Frontend ghi âm + UI |
| `apps/web/src/app/cuoc-hop/MeetingResults.tsx` | 957 | Hiển thị kết quả |
| `packages/contracts/src/ca_contracts/__init__.py` | — | Contract `CuocHop` |

### 0.3. ⚠️ Làm rõ về model Gemini & chi phí (quan trọng)

**Hiểu lầm phổ biến:** "Gemini Live không hạn mức nên không tốn chi phí" — **đúng cho Voice
Copilot, nhưng KHÔNG đúng cho tính năng ghi cuộc họp hiện tại.**

| Model | Dùng cho | Loại | Hạn mức |
|---|---|---|---|
| `gemini-3.8-live-extended-thinking` | **Voice Copilot** (chat thoại) | Live WebSocket | Không hạn mức free |
| `gemini-2.5-flash` (REST) | **STT ghi cuộc họp** (`stt.py`) | REST generateContent | **Có hạn mức** |
| `gemini-2.5-flash` (REST) | **Extract biên bản** (`llm.py` → `complete()`) | REST generateContent | **Có hạn mức** |

**Kết luận:** Tính năng **ghi cuộc họp (AG-MEETING) hiện KHÔNG dùng Gemini Live Transcribe**.
Nó dùng REST `gemini-2.5-flash` cho cả STT lẫn extract — **đều có hạn mức**. Vì vậy:
- Giả định "không tốn chi phí" **chưa đúng** cho tính năng này.
- Tối ưu giảm số lần gọi LLM (rule-based trước) **vẫn có giá trị** để giảm hạn mức tiêu thụ.

> **Lưu ý:** Nếu muốn tận dụng Gemini Live (không hạn mức) cho STT, cần **viết thêm module
> streaming STT** dùng WebSocket Live (giống `voice_session.py`). Đây là **hướng mới**, chưa có
> trong code hiện tại — cần nghiên cứu thêm trước khi quyết định (xem mục 9).

### 0.4. Giới hạn thời gian họp & ngữ cảnh (quan trọng)

**Giới hạn hiện tại:**
- **File audio:** tối đa **25MB** (chặn ở cổng `meeting.py`). Ở 32kbps, 25MB ≈ **~100 phút**.
- **Gemini REST inline audio:** ~20MB (giới hạn của Gemini).
- **Context window `gemini-2.5-flash`:** ~1M token, nhưng **audio dài chiếm nhiều token** —
  cuộc họp dài có thể vượt hoặc chậm.

**Kéo dài cuộc họp ảnh hưởng:**
- **RAM server tăng** theo độ dài (file lớn đọc vào RAM + base64 +33%).
- **Tốn token** (audio dài = nhiều token).
- **Chậm** (phải chờ hết cuộc họp mới xử lý).
- **Nguy cơ timeout** (Gemini REST timeout 60s).

**Về "quên ngữ cảnh":**
- **Hiện tại (REST, 1 lần gọi):** STT gửi toàn bộ audio 1 lần, extract gửi toàn bộ transcript
  1 lần → **không quên ngữ cảnh** (nhưng tốn RAM/token, vượt context nếu quá dài).
- **Sau tối ưu (chunking + giới hạn 8000 ký tự):** chia nhỏ → **có thể mất ngữ cảnh giữa các
  đoạn** (vd người nói đổi giữa đoạn, action item nằm ở phần bị cắt).

> **Đây là đánh đổi chính:** tối ưu tài nguyên ↔ giữ nguyên ngữ cảnh. Cần cân bằng bằng cách
> chỉ chunk khi thật cần (audio > 5MB), và giới hạn transcript chỉ cắt phần ít quan trọng.

### 0.5. Test hiện có (phải giữ pass)

- `apps/api/tests/unit/test_meeting_api.py`
- `apps/api/tests/unit/test_meeting_clarify.py`
- `apps/web/e2e/meeting-clarify.spec.ts`
- Golden data: `data/golden/meeting/meeting_01.json`

### 0.4. Vấn đề chính cần giải quyết

| # | Vấn đề | Tác động tài nguyên |
|---|---|---|
| P1 | Gửi toàn bộ audio lên server STT | RAM server 50-80MB/cuộc họp, băng thông 7-10MB |
| P2 | LLM gọi 1 lần cho cả cuộc họp dài | Tốn token, vượt context, chậm |
| P3 | `_levenshtein` O(n²) trên mọi từ | Điểm nóng CPU |
| P4 | `_get_roster_data()` đọc file mỗi lần | Tốn I/O + parse JSON |
| P5 | Frontend giữ toàn bộ audio trong RAM | Tốn RAM client |
| P6 | Không có tìm kiếm/hỏi đáp biên bản | Thiếu tính năng ông lớn có |
| P7 | Không tự gửi bản tin ca | Thiếu tự động hóa |

---

## 1. GIAI ĐOẠN 1 — Tối ưu CPU/RAM thuần (an toàn, không đổi hành vi)

> **Mục tiêu:** Giảm CPU/RAM ngay, **không thay đổi kết quả đầu ra**. Rủi ro thấp nhất.
> **Cổng ra:** Toàn bộ test `test_meeting_*.py` pass, không đổi golden data.

### Bước 1.1 — Tối ưu `_levenshtein` + fuzzy match (P3)

**File:** `packages/agents/src/ca_agents/ag_meeting/extract.py`

**Vấn đề:** `resolve_staff_id_with_meta()` gọi `_levenshtein()` cho từng từ trong transcript
để fuzzy-match tên nhân viên. Với transcript dài + nhiều nhân viên → O(từ × NV × n²).

**Cách làm:**
1. **Pre-filter bằng prefix:** trước khi tính Levenshtein, kiểm tra ký tự đầu tiên khớp
   (hoặc dùng `difflib.SequenceMatcher` nhanh để loại). Chỉ tính Levenshtein khi prefix khớp.
2. **Cache kết quả:** thêm `functools.lru_cache` hoặc dict `{từ_đã_chuẩn_hóa: nv_id}` —
   từ lặp lại không tính lại.
3. **Giới hạn độ dài:** tăng ngưỡng từ `< 3` lên `< 4` ký tự cho fuzzy (tên tiếng Việt ngắn
   dễ nhầm, ít giá trị).
4. **Chỉ fuzzy khi cần:** rà soát các chỗ gọi `allow_fuzzy_stt=True` — chỉ bật khi nguồn là
   STT thật (`audio_source != "ghi_chep_tay"`), không bật cho text gõ tay.

**Kiểm chứng:**
- Chạy `test_meeting_clarify.py` — các test TC-31, TC-37 (fuzzy match) vẫn pass.
- Benchmark: đo thời gian `extract_meeting` với transcript 1000 từ trước/sau.

### Bước 1.2 — Cache `_get_roster_data()` (P4)

**File:** `apps/api/src/ca_api/interfaces/http/meeting.py`

**Vấn đề:** `_get_roster_data()` đọc `data/seed/sample.json` + `data/out/lich_tuan.json`
mỗi lần gọi analyze/process-audio.

**Cách làm:**
1. Thêm module-level cache: `_roster_cache = {"mtime": 0, "data": None}`.
2. Trước khi đọc, kiểm tra `os.path.getmtime()` của 2 file. Chỉ đọc lại khi mtime đổi.
3. Cache tối đa 60s (tránh giữ dữ liệu cũ quá lâu).

**Kiểm chứng:**
- Gọi `/api/v1/meeting/analyze` 2 lần liên tiếp — lần 2 không đọc file (log hoặc debug).
- Test `test_meeting_api.py` pass.

### Bước 1.3 — Giảm bitrate audio (P5 một phần)

**File:** `apps/web/src/app/cuoc-hop/page.tsx`

**Vấn đề:** đang dùng `audioBitsPerSecond: 32000`. Giọng nói hội thoại đủ rõ ở 24kbps.

**Cách làm:**
1. Đổi `audioBitsPerSecond: 32000` → `24000` ở cả 2 chỗ (mic + meet).
2. Giữ nguyên mimeType `audio/webm;codecs=opus`.

**Kiểm chứng:**
- Build web, chạy E2E `meeting-clarify.spec.ts` pass.
- Ghi âm thử 1 phút, kiểm tra file nhỏ hơn ~25%.

---

## 2. GIAI ĐOẠN 2 — Giảm chi phí LLM & RAM server (đổi luồng, cần test kỹ)

> **Mục tiêu:** Giảm 50-70% số lần gọi LLM, giảm RAM server khi STT.
> **Cổng ra:** Test pass + E2E pass + không đổi contract `CuocHop`.

### Bước 2.1 — Ưu tiên `live_transcript` thay vì gửi audio (P1)

**File:** `apps/api/src/ca_api/interfaces/http/meeting.py`, `apps/web/src/app/cuoc-hop/page.tsx`

**Vấn đề:** Frontend ghi âm toàn bộ cuộc họp rồi gửi lên server STT. Web Speech API
(`live_transcript`) đã chạy **trên trình duyệt** (không tốn server) nhưng chỉ dùng làm fallback.

**Cách làm:**
1. **Backend:** trong `process_audio_upload`, nếu `live_transcript` không rỗng và đủ dài
   (vd > 50 ký tự), **ưu tiên dùng `live_transcript` làm nguồn chính**, KHÔNG gọi STT trên audio.
   Chỉ gọi STT khi live_transcript rỗng.
2. **Frontend:** khi dừng ghi âm, nếu `liveTranscriptRef.current` đã có nội dung, gửi kèm
   `live_transcript` và đánh dấu `use_live_transcript=true`. Vẫn gửi audio để dự phòng.
3. Thêm flag `prefer_live_transcript: bool = False` vào body.

**Kiểm chứng:**
- Test: gửi `process-audio` với `live_transcript` đầy đủ → không gọi STT (mock `transcribe_audio`).
- Test: gửi không có `live_transcript` → vẫn gọi STT như cũ.
- E2E pass.

### Bước 2.2 — Chunking audio khi phải STT (P1)

**File:** `apps/api/src/ca_api/interfaces/http/meeting.py`, `packages/agents/src/ca_agents/ag_meeting/stt.py`

**Vấn đề:** File audio 25MB đọc vào RAM + base64 (tăng 33%) gửi lên Gemini → RAM đỉnh cao.

**Cách làm:**
1. Trong `stt.py`, thêm hàm `transcribe_audio_chunked()`:
   - Nếu audio > ngưỡng (vd 5MB), chia thành các chunk 30-60s.
   - STT từng chunk, nối `raw_text` + `segments` lại (điều chỉnh `bat_dau_s`/`ket_thuc_s` offset).
   - Giữ thứ tự, gộp segment liền kề cùng người nói.
2. Trong `meeting.py`, gọi `transcribe_audio_chunked()` thay vì `transcribe_audio()`.
3. Giữ nguyên giới hạn 25MB ở cổng (chặn file quá lớn).

**Kiểm chứng:**
- Test chunking với audio giả 6MB → trả transcript đầy đủ, segment có offset đúng.
- Test audio nhỏ (< 5MB) → không chunk, hành vi cũ.
- Đo RAM đỉnh giảm.

### Bước 2.3 — Rule-based trước, LLM sau (P2)

**File:** `packages/agents/src/ca_agents/ag_meeting/extract.py`

**Vấn đề:** `extract_meeting()` luôn gọi LLM (trừ replay mode). Với transcript ngắn/rõ ràng,
rule-based đã đủ tốt, không cần LLM.

**Cách làm:**
1. Thêm hàm `_should_use_llm(text, meeting_type)`:
   - Nếu transcript < 200 ký tự → dùng rule-based (không gọi LLM).
   - Nếu transcript chứa toàn mẫu rõ ràng (giao việc, xin nghỉ, ghim ca) → rule-based.
   - Nếu transcript dài + mơ hồ → LLM.
2. Trong `extract_meeting()`, trước khi gọi `complete()`, kiểm tra `_should_use_llm()`.
   Nếu không cần LLM → gọi `_extract_rule_or_fixture()`.
3. Giữ nguyên `_normalize_output()` cho cả 2 path (đảm bảo contract giống nhau).

**Kiểm chứng:**
- Test transcript ngắn rõ ràng → không gọi LLM (mock `complete` không được gọi).
- Test transcript dài mơ hồ → vẫn gọi LLM.
- Golden data `meeting_01.json` vẫn khớp.

### Bước 2.4 — Giới hạn độ dài transcript vào LLM (P2)

**File:** `packages/agents/src/ca_agents/ag_meeting/extract.py`

**Vấn đề:** Transcript dài vượt context window → LLM cắt bớt, mất thông tin, tốn token.

**Cách làm:**
1. Trong `extract_meeting()`, trước khi build `user_prompt`, cắt transcript xuống tối đa
   `MAX_LLM_CHARS = 8000` ký tự (≈ 4000 từ tiếng Việt).
2. Nếu transcript dài hơn, **ưu tiên giữ phần có action cues** (giao việc, xin nghỉ, ghim ca)
   bằng cách quét keyword, giữ các dòng chứa cue trước, phần còn lại cắt.
3. Ghi chú vào `tom_tat` nếu bị cắt: "Transcript dài, đã phân tích phần trọng tâm".

**Kiểm chứng:**
- Test transcript 12000 ký tự → prompt ≤ 8000 ký tự, vẫn trích được action items chính.
- Test transcript ngắn → không cắt.

### Bước 2.5 — Cache kết quả extract (P2)

**File:** `packages/agents/src/ca_agents/ag_meeting/extract.py`

**Vấn đề:** Cuộc họp lặp lại (cùng transcript) gọi lại LLM vô ích.

**Cách làm:**
1. Thêm cache dict `_extract_cache: dict[str, dict]` với key = `hash(meeting_type + transcript)`.
2. Chỉ cache kết quả **LLM** (không cache rule-based — đã rẻ).
3. Cache tối đa 100 entry, TTL 1 giờ (tránh memory leak).
4. Dùng `functools.lru_cache` hoặc dict + `time.time()`.

**Kiểm chứng:**
- Gọi `extract_meeting` 2 lần cùng transcript → lần 2 không gọi LLM (mock `complete` 1 lần).
- Cache không phình (test 150 entry → entry cũ bị evict).

---

## 3. GIAI ĐOẠN 3 — Tính năng mới (chi phí thấp, tăng giá trị)

> **Mục tiêu:** Thêm tính năng ông lớn có, chi phí tài nguyên thấp.
> **Cổng ra:** Test pass + E2E pass + review nghiệp vụ.

### Bước 3.1 — Full-text search biên bản (P6)

**File:** `apps/api/src/ca_api/interfaces/http/meeting.py`, `apps/web/src/app/cuoc-hop/page.tsx`

**Vấn đề:** Không tìm kiếm được trong lịch sử cuộc họp.

**Cách làm:**
1. **Backend:** thêm `GET /api/v1/meetings/search?q=...`:
   - Dùng SQLite FTS5 nếu có, hoặc LIKE trên `tieu_de` + `tom_tat` + `action_items[].tieu_de`.
   - Trả về danh sách meeting khớp, kèm highlight.
2. **Frontend:** thêm ô tìm kiếm trong "Lịch sử cuộc họp", gọi API search khi gõ.

**Kiểm chứng:**
- Test search "máy pha" → trả meeting chứa từ đó.
- Test search không có kết quả → trả rỗng, không lỗi.

### Bước 3.2 — Tự gửi bản tin ca lên Telegram/Zalo (P7)

**File:** `apps/api/src/ca_api/interfaces/http/meeting.py`

**Vấn đề:** `ban_tin_ca.noi_dung_tin_nhan_gui_nhom` chỉ copy tay.

**Cách làm:**
1. Sau khi `apply_meeting_decisions()` thành công, nếu `ban_tin_ca.noi_dung_tin_nhan_gui_nhom`
   không rỗng → gọi kênh Telegram/Zalo (đã có trong `channels.py`) để gửi.
2. Thêm cờ `auto_send_broadcast: bool = False` trong body — mặc định tắt (an toàn).
3. Ghi audit trail `meeting.broadcast_sent`.

**Kiểm chứng:**
- Test với cờ bật + mock channel → gửi thành công, audit ghi.
- Test cờ tắt → không gửi.

### Bước 3.3 — Expand summary (tóm tắt mở rộng)

**File:** `apps/web/src/app/cuoc-hop/MeetingResults.tsx`, `apps/api/src/ca_api/interfaces/http/meeting.py`

**Vấn đề:** Tóm tắt ngắn, không mở rộng được chi tiết.

**Cách làm:**
1. **Backend:** thêm `POST /api/v1/meeting/expand-summary` nhận `{meeting_id, bullet}` →
   gọi LLM nhỏ mở rộng bullet đó thành đoạn chi tiết.
2. **Frontend:** thêm nút "Mở rộng" cạnh mỗi bullet tóm tắt, gọi API khi bấm.

**Kiểm chứng:**
- Test expand-summary với bullet → trả đoạn chi tiết.
- Test không có meeting_id → 404.

---

## 4. Lịch trình & thứ tự thực hiện

| Giai đoạn | Bước | Ước tính | Rủi ro | Phụ thuộc |
|---|---|---|---|---|
| **GĐ1** | 1.1 `_levenshtein` | 0.5 ngày | Thấp | — |
| **GĐ1** | 1.2 cache roster | 0.25 ngày | Thấp | — |
| **GĐ1** | 1.3 giảm bitrate | 0.25 ngày | Thấp | — |
| **GĐ2** | 2.1 live_transcript | 1 ngày | Trung bình | GĐ1 |
| **GĐ2** | 2.2 chunking | 1 ngày | Trung bình | GĐ1 |
| **GĐ2** | 2.3 rule-based trước | 1 ngày | Trung bình | GĐ1 |
| **GĐ2** | 2.4 giới hạn transcript | 0.5 ngày | Thấp | GĐ1 |
| **GĐ2** | 2.5 cache extract | 0.5 ngày | Thấp | GĐ1 |
| **GĐ3** | 3.1 search | 1 ngày | Thấp | GĐ2 |
| **GĐ3** | 3.2 gửi bản tin | 1 ngày | Trung bình | GĐ2 |
| **GĐ3** | 3.3 expand summary | 0.5 ngày | Thấp | GĐ2 |

**Tổng:** ~8 ngày làm việc (có thể song song hóa GĐ1).

---

## 5. Cổng chất lượng (mỗi giai đoạn phải đạt)

- [ ] `pytest apps/api/tests/unit/test_meeting_api.py` — pass
- [ ] `pytest apps/api/tests/unit/test_meeting_clarify.py` — pass
- [ ] `pytest packages/agents/tests/` (nếu có test ag_meeting) — pass
- [ ] Playwright E2E `meeting-clarify.spec.ts` — pass
- [ ] Golden data `meeting_01.json` không đổi (trừ khi cố ý)
- [ ] Contract `CuocHop` không đổi (trừ khi thêm field optional)
- [ ] Không ghi đè dữ liệu thật khi test (dùng seed/test env)

---

## 6. Rủi ro & cách giảm thiểu

| Rủi ro | Mức | Cách giảm thiểu |
|---|---|---|
| Đổi luồng làm sai kết quả extract | Trung bình | Giữ `_normalize_output()` chung, test golden data |
| Chunking làm mất ngữ cảnh STT | Trung bình | Gộp segment liền kề, giữ offset |
| Cache gây dữ liệu cũ | Thấp | TTL 60s (roster), TTL 1h (extract), evict LRU |
| Live_transcript kém chất lượng hơn STT | Trung bình | Chỉ ưu tiên khi đủ dài, vẫn gửi audio dự phòng |
| Gửi bản tin tự động gửi nhầm | Trung bình | Cờ `auto_send_broadcast` mặc định tắt |

---

## 7. Kết quả mong đợi sau khi hoàn thành

| Chỉ số | Hiện tại | Sau tối ưu | Giảm |
|---|---|---|---|
| RAM server khi STT | 50-80MB/cuộc họp | 10-20MB | **70-75%** |
| Băng thông upload | 7-10MB/cuộc họp | 1-2MB | **80%** |
| Số lần gọi LLM | 1/cuộc họp | 0.3-0.5/cuộc họp | **50-70%** |
| CPU rule-based | O(từ×NV×n²) | O(từ×NV×n) | **~90%** |
| Chi phí API | Cao | Thấp | **50-70%** |

---

## 8. Quyết định cần chủ dự án

Trước khi bắt đầu code, cần chốt:

1. **Phạm vi:** Làm toàn bộ 3 giai đoạn, hay chỉ GĐ1 (an toàn) trước?
2. **Ưu tiên:** Giảm RAM server là ưu tiên số 1 (đã chọn), hay cân bằng với chi phí LLM?
3. **Tính năng mới (GĐ3):** Có muốn thêm search + gửi bản tin + expand summary không?
4. **Cờ `auto_send_broadcast`:** Mặc định tắt hay bật?
5. **Thứ tự:** Làm tuần tự từng giai đoạn, hay song song GĐ1?
6. **Hướng Gemini Live (mục 9):** Có muốn nghiên cứu dùng Gemini Live (không hạn mức) cho
   STT ghi cuộc họp không? Đây là hướng mới, cần thêm thời gian nghiên cứu.

> ⚠️ **Nguyên tắc:** Không tự ý sửa code trước khi chủ dự án duyệt hướng. Mỗi giai đoạn
> hoàn thành phải chạy đủ test + E2E trước khi merge.

---

## 9. Hướng nghiên cứu thêm — Dùng Gemini Live cho STT ghi cuộc họp

> **Đây là hướng MỚI, chưa có trong code hiện tại.** Cần nghiên cứu thêm trước khi quyết định.

### 9.1. Vì sao đáng cân nhắc

Bạn đúng khi nhận định **Gemini Live không hạn mức**. Nếu dùng Gemini Live (WebSocket) cho
STT ghi cuộc họp thay vì REST `gemini-2.5-flash` (có hạn mức), sẽ:
- **Không tốn chi phí** (không hạn mức free).
- **Streaming real-time** — bóc băng theo từng đoạn, không đợi hết cuộc họp.
- **RAM server thấp** — không gửi toàn bộ audio lên server.

### 9.2. Kết quả test thật `gemini-3.5-transcribe-live` (260918) — ĐÃ HOẠT ĐỘNG

Đã viết module `stt_live.py` và test WebSocket thật với `data/Bài-1.mp3` (giọng nói tiếng Việt).
Kết quả:

| Hạng mục | Kết quả | Chi tiết |
|---|---|---|
| **Setup WebSocket** | 🟢 **THÀNH CÔNG** | `setupComplete: {}` với `inputAudioTranscription: {}`. |
| **Transcript thật** | 🟢 **HOẠT ĐỘNG** | Trả transcript "Bài 1..." từ file giọng nói tiếng Việt. |
| **Nguồn transcript** | ✅ | Model trả qua `interimInputTranscription` (KHÔNG phải `modelTurn.parts[].transcript`). |
| **Quota token/phút** | ⚠️ **20K** | Audio dài vượt 20K token/phút → 1011. **Đã fix bằng chunking 30s + cooldown 5s.** |
| **Keepalive timeout** | ⚠️ | Gửi file dài qua pacing → 1011 ping timeout. **Đã fix bằng gửi/nhận song song.** |
| **Decode audio** | ✅ | Dùng `imageio-ffmpeg` (decode webm/opus/mp3/ogg/wav → PCM16 16kHz). |

**Các lỗi đã fix trong `stt_live.py`:**
1. **`asyncio.run()` trong async context** → thêm `transcribe_audio_live_async`, `process_audio_upload` dùng `await`.
2. **Thiếu `imageio-ffmpeg` dependency** → thêm vào `pyproject.toml`.
3. **Không đọc `interimInputTranscription`** → transcript rỗng. Đã sửa đọc cả interim/final.
4. **Keepalive ping timeout** → gửi/nhận song song (2 task asyncio).
5. **Quota token/phút 20K** → chunking 30s + cooldown 5s.
6. **Transcript trùng lặp** (interim lặp) → dedupe.

**Kết luận:** `gemini-3.5-transcribe-live` **HOẠT ĐỘNG** cho STT cuộc họp. Module `stt_live.py`
đã hoàn thiện, test pass (55 test).

### 9.3. Nhưng có thách thức

| Thách thức | Chi tiết |
|---|---|
| **Chưa có code** | `voice_session.py` dùng Live cho chat thoại, nhưng **chưa có module Live cho STT cuộc họp**. Cần viết mới. |
| **Model khác nhau** | `gemini-3.8-live-extended-thinking` (chat thoại) ≠ `gemini-3.5-transcribe-live` (STT). Đã xác nhận model STT Live setup OK. |
| **Speaker diarization** | Live STT có thể không tách người nói tốt như REST. Cần kiểm chứng với audio thật. |
| **Độ phức tạp** | WebSocket streaming phức tạp hơn REST 1 lần gọi. Cần test kỹ. |
| **Frontend phải đổi** | Hiện ghi âm toàn bộ rồi gửi. Live STT cần streaming từ trình duyệt → server → Gemini. |

### 9.4. Đề xuất

- **Giai đoạn nghiên cứu (0.5-1 ngày):** Viết prototype nhỏ dùng `gemini-3.5-transcribe-live`
  qua WebSocket, test với audio thật, đo độ chính xác + RAM.
- **Nếu khả thi:** thêm làm **GĐ4** (sau GĐ1-3), thay thế REST STT bằng Live STT.
- **Nếu không khả thi:** giữ REST + tối ưu theo GĐ1-3 (vẫn giảm 50-70% chi phí).

> **Khuyến nghị:** Làm GĐ1-3 trước (an toàn, giảm chi phí ngay), song song nghiên cứu GĐ4
> (Gemini Live) như một hướng nâng cao. Không nên bỏ GĐ1-3 để chờ GĐ4 vì GĐ1-3 giảm chi phí
> ngay mà không cần viết module mới.