# Review & Đề xuất tối ưu — Tính năng Ghi lại Cuộc họp (AG-MEETING)

> **Mục đích:** Rà soát toàn diện tính năng ghi lại cuộc họp (AI Meeting OS / AG-MEETING),
> đối chiếu với các sản phẩm tương tự của ông lớn trên thị trường (Otter.ai, Fireflies.ai,
> tl;dv, Fathom, Zoom AI Companion, Google Meet Gemini), tìm điểm mạnh cần giữ và điểm yếu
> cần tối ưu — **ưu tiên giảm tải CPU/RAM server** và **ổn định với tài nguyên thấp nhất**.
>
> **Ngày lập:** 2026-09-18
> **Trạng thái:** ⏳ Đề xuất — chờ chủ dự án review & duyệt trước khi code
> **Phạm vi:** `packages/agents/.../ag_meeting/*`, `apps/api/.../http/meeting.py`, `apps/web/src/app/cuoc-hop/*`

---

## 1. Tóm tắt hiện trạng (đã đọc toàn bộ code)

### 1.1. Kiến trúc hiện tại

```
Frontend (apps/web/src/app/cuoc-hop/page.tsx)
  ├─ Mode 1: Micro giao ca  → getUserMedia + MediaRecorder (webm/opus 32kbps)
  ├─ Mode 2: Google Meet    → getDisplayMedia + AudioContext trộn tab+mic
  ├─ Mode 3: Tải audio      → upload file (.mp3/.m4a/.wav/.webm)
  └─ Mode 4: Dán ghi chép   → text thuần
        │  POST /api/v1/meeting/process-audio  (hoặc /transcribe + /analyze)
        ▼
Backend (apps/api/.../http/meeting.py)
  ① STT — transcribe_audio()  (ag_meeting/stt.py)
     • Gemini 2.5 Flash → Groq Whisper → Replay fixture
     • Speaker diarization → segments
  ② Trích xuất — extract_meeting()  (ag_meeting/extract.py, 1055 dòng)
     • LLM (prompt v2.md) → CuocHop contract
     • Fallback rule-based heuristic (không cần LLM)
  ③ Làm rõ — clarify_meeting_actions()  (ag_meeting/clarify.py)
     • Đối chiếu nhân viên + lịch ca thật
  ④ Duyệt — POST /api/v1/meeting/apply (chỉ Quản lý/Chủ quán)
     • Việc treo → opsengine, SOP → sop_de_xuat, lịch → inbox_rang_buoc
```

### 1.2. Kích thước code

| File | Dòng | Vai trò |
|---|---|---|
| `ag_meeting/extract.py` | 1055 | Trích xuất + rule-based fallback |
| `ag_meeting/clarify.py` | 262 | Làm rõ ngữ cảnh, gán ca |
| `ag_meeting/stt.py` | 316 | STT (Gemini/Groq/Replay) |
| `http/meeting.py` | 771 | Router + apply + rollback + draft |
| `cuoc-hop/page.tsx` | 1148 | Frontend ghi âm + UI |
| `cuoc-hop/MeetingResults.tsx` | 957 | Hiển thị kết quả |

---

## 2. Điểm mạnh hiện có (nên GIỮ)

So với các ông lớn, hệ thống đã có nhiều điểm tốt:

| # | Điểm mạnh | So với ông lớn |
|---|---|---|
| 1 | **4 cách ghi** (mic/Meet/upload/text) | Tương đương Otter/Fireflies (đa kênh capture) |
| 2 | **Live transcript** (Web Speech API) | Tương đương Otter "see words as spoken" |
| 3 | **Speaker diarization** | Tương đương Fireflies "Speaker Recognition" |
| 4 | **Human-in-the-loop duyệt** (ADR-008) | **VƯỢT TRỘI** — các ông lớn tự ghi task, hệ thống này an toàn hơn |
| 5 | **Rule-based fallback** không cần LLM | **VƯỢT TRỘI** — chạy được offline, chi phí 0 |
| 6 | **Chống trùng lặp xuyên cuộc họp** (TC-30) | Tốt hơn nhiều sản phẩm |
| 7 | **Rollback / recall** (TC-42) | Tương đương, hiếm có |
| 8 | **Optimistic concurrency** (TC-44) | Tốt, tránh mất dữ liệu |
| 9 | **Grounded guardrail** chống hallucination (TC-40) | **VƯỢT TRỘI** — các ông lớn hay bịa |
| 10 | **Audit trail** đầy đủ | Tốt |

---

## 3. Điểm yếu & cơ hội tối ưu (ưu tiên giảm CPU/RAM)

### 3.1. 🔴 VẤN ĐỀ LỚN NHẤT — STT gửi toàn bộ audio lên server

**Vấn đề:** Frontend ghi âm **toàn bộ** cuộc họp (có thể 30-60 phút) thành 1 blob webm,
rồi gửi lên server để STT. Điều này:
- **Tốn RAM server:** file 25MB đọc vào RAM, base64 hóa (tăng 33%), gửi lên Gemini.
- **Tốn băng thông:** mỗi cuộc họp 30 phút ≈ 7-10MB upload.
- **Chậm:** phải chờ hết cuộc họp mới xử lý.

**Cách ông lớn làm:** Otter/Fireflies **streaming STT** — bóc băng **theo từng đoạn nhỏ**
(real-time), không đợi hết cuộc họp. Kết quả: RAM thấp, phản hồi tức thì, có thể hủy giữa chừng.

**Đề xuất tối ưu (giảm RAM server):**
- **Ưu tiên dùng `live_transcript`** (Web Speech API chạy **trên trình duyệt**, không tốn server) làm nguồn chính. Chỉ gửi audio lên server khi live transcript rỗng.
- **Chunking:** nếu phải gửi audio, chia nhỏ thành từng đoạn 30-60s, STT từng phần, nối lại. Giảm RAM đỉnh, cho phép xử lý song song.
- **Giảm bitrate:** đang dùng 32kbps — có thể giảm xuống 24kbps (đủ cho giọng nói) để giảm dung lượng 25%.

### 3.2. 🟠 LLM extract gọi 1 lần cho cả cuộc họp dài

**Vấn đề:** `extract_meeting()` gửi **toàn bộ transcript** vào 1 prompt LLM. Với cuộc họp dài:
- **Tốn token** (chi phí cao).
- **Vượt context window** → LLM cắt bớt → mất thông tin.
- **Chậm** (LLM xử lý dài).

**Cách ông lớn làm:** tl;dv/Fireflies **chunk + map-reduce** — chia transcript thành đoạn,
tóm tắt từng đoạn, rồi tổng hợp. Hoặc **chỉ trích xuất action items** (không yêu cầu LLM tóm tắt toàn bộ).

**Đề xuất tối ưu (giảm CPU/RAM + chi phí):**
- **Giới hạn độ dài transcript** đưa vào LLM (vd 4000 từ). Phần dài hơn dùng rule-based.
- **Ưu tiên rule-based trước** cho các mẫu rõ ràng (giao việc, xin nghỉ, ghim ca) — chỉ gọi LLM cho phần mơ hồ. Giảm 50-70% số lần gọi LLM.
- **Cache kết quả** theo `(meeting_type, hash(transcript))` — cuộc họp lặp lại không gọi lại LLM.

### 3.3. 🟠 `_levenshtein` chạy O(n²) trên mọi từ

**Vấn đề:** `resolve_staff_id_with_meta()` gọi `_levenshtein()` cho **từng từ** trong transcript
để fuzzy-match tên nhân viên. Với transcript dài + nhiều nhân viên → **O(từ × nhân_viên × n²)**.
Đây là **điểm nóng CPU** lớn nhất trong rule-based path.

**Đề xuất tối ưu (giảm CPU):**
- **Pre-filter bằng prefix** trước khi tính Levenshtein (chỉ tính khi ký tự đầu khớp).
- **Giới hạn độ dài từ** (bỏ từ < 3 ký tự, đã có nhưng tăng ngưỡng).
- **Cache** kết quả match theo từ (dict) — từ lặp lại không tính lại.
- **Chỉ fuzzy-match khi cần** — hiện gọi `allow_fuzzy_stt=True` ở nhiều nơi không cần thiết.

### 3.4. 🟡 `_get_roster_data()` đọc file JSON mỗi lần

**Vấn đề:** `_get_roster_data()` đọc `data/seed/sample.json` + `data/out/lich_tuan.json`
**mỗi lần gọi** analyze/process-audio. Đọc file I/O + parse JSON tốn CPU/RAM.

**Đề xuất:** **Cache** kết quả theo thời gian (vd 60s) hoặc theo `mtime` file. Chỉ đọc lại khi file đổi.

### 3.5. 🟡 Frontend giữ toàn bộ audio trong RAM

**Vấn đề:** `audioChunksRef` giữ **toàn bộ** blob audio trong RAM trình duyệt trong suốt cuộc họp.
Với cuộc họp dài → tốn RAM client.

**Đề xuất:** **Streaming upload** — gửi từng chunk lên server khi `ondataavailable` (mỗi 1s),
không giữ toàn bộ. Server nối dần.

### 3.6. 🟡 Không có tìm kiếm / hỏi đáp trên biên bản

**Vấn đề:** Các ông lớn (Otter "Ask Otter", Fireflies "AskFred", tl;dv "AI Reports") cho phép
**hỏi đáp trên toàn bộ lịch sử cuộc họp**. Hệ thống hiện chỉ liệt kê biên bản, không tìm kiếm.

**Đề xuất (tính năng mới, chi phí thấp):**
- **Full-text search** trên `meetings` KV (SQLite FTS5 hoặc LIKE) — không cần LLM.
- **Tóm tắt mở rộng** (expand summary bullet) — gọi LLM nhỏ chỉ khi cần.

### 3.7. 🟡 Không có tự động gửi bản tin ca

**Vấn đề:** `ban_tin_ca.noi_dung_tin_nhan_gui_nhom` đã được tạo nhưng **chỉ copy tay**.
Các ông lớn tự động push lên Slack/Teams.

**Đề xuất:** Nối với kênh Telegram/Zalo đã có (item 20/21 trong audit) — tự gửi bản tin ca sau khi duyệt.

---

## 4. Bảng so sánh với ông lớn

| Tính năng | Nhịp Quán | Otter | Fireflies | tl;dv | Ghi chú |
|---|---|---|---|---|---|
| Đa kênh capture | ✅ 4 cách | ✅ | ✅ | ✅ | Tốt |
| Live transcript | ✅ (Web Speech) | ✅ | ✅ | ✅ | Tốt |
| Speaker diarization | ✅ | ✅ | ✅ | ✅ | Tốt |
| Action items tự động | ✅ | ✅ | ✅ | ✅ | Tốt |
| **Human-in-loop duyệt** | ✅ | ❌ | ❌ | ❌ | **Vượt trội** |
| **Rule-based fallback (0 LLM)** | ✅ | ❌ | ❌ | ❌ | **Vượt trội** |
| Chống hallucination | ✅ | ❌ | ❌ | ❌ | **Vượt trội** |
| Streaming STT (RAM thấp) | ❌ | ✅ | ✅ | ✅ | **Cần tối ưu** |
| Chunking LLM | ❌ | ✅ | ✅ | ✅ | **Cần tối ưu** |
| Tìm kiếm/hỏi đáp | ❌ | ✅ | ✅ | ✅ | **Cần thêm** |
| Tự gửi bản tin | ❌ | ✅ | ✅ | ✅ | **Cần thêm** |
| Rollback | ✅ | ❌ | ❌ | ❌ | Vượt trội |
| Optimistic concurrency | ✅ | ❌ | ❌ | ❌ | Vượt trội |

---

## 5. Đề xuất tối ưu theo thứ tự ưu tiên (giảm CPU/RAM)

### Nhóm A — Tối ưu tài nguyên (ưu tiên cao nhất, ít rủi ro)

| # | Đề xuất | Tác động CPU/RAM | File | Rủi ro |
|---|---|---|---|---|
| A1 | **Ưu tiên live_transcript** thay vì gửi audio lên server | Giảm RAM server + băng thông lớn | `meeting.py`, `page.tsx` | Thấp |
| A2 | **Chunking audio** (30-60s) khi phải STT | Giảm RAM đỉnh server | `meeting.py`, `stt.py` | Trung bình |
| A3 | **Tối ưu `_levenshtein`** (pre-filter + cache) | Giảm CPU lớn | `extract.py` | Thấp |
| A4 | **Cache `_get_roster_data()`** | Giảm I/O + parse JSON | `meeting.py` | Thấp |
| A5 | **Giảm bitrate** 32→24kbps | Giảm dung lượng 25% | `page.tsx` | Thấp |
| A6 | **Streaming upload** (không giữ toàn bộ audio client) | Giảm RAM client | `page.tsx` | Trung bình |

### Nhóm B — Giảm chi phí LLM

| # | Đề xuất | Tác động | File | Rủi ro |
|---|---|---|---|---|
| B1 | **Rule-based trước, LLM sau** cho mẫu rõ ràng | Giảm 50-70% gọi LLM | `extract.py` | Trung bình |
| B2 | **Giới hạn độ dài transcript** vào LLM (4000 từ) | Giảm token | `extract.py` | Thấp |
| B3 | **Cache kết quả** theo hash transcript | Tránh gọi lại | `extract.py` | Thấp |

### Nhóm C — Tính năng mới (chi phí thấp, tăng giá trị)

| # | Đề xuất | Tác động | File | Rủi ro |
|---|---|---|---|---|
| C1 | **Full-text search** biên bản (FTS5) | Không cần LLM | `meeting.py`, `page.tsx` | Thấp |
| C2 | **Tự gửi bản tin ca** lên Telegram/Zalo | Tự động hóa | `meeting.py` | Trung bình |
| C3 | **Expand summary** (tóm tắt mở rộng) | Gọi LLM nhỏ khi cần | `page.tsx` | Thấp |

---

## 6. Ước tính tác động

| Chỉ số | Hiện tại | Sau tối ưu (A+B) | Giảm |
|---|---|---|---|
| RAM server khi STT | ~50-80MB/cuộc họp | ~10-20MB | **70-75%** |
| Băng thông upload | 7-10MB/cuộc họp | ~1-2MB | **80%** |
| Số lần gọi LLM | 1/cuộc họp | 0.3-0.5/cuộc họp | **50-70%** |
| CPU rule-based | O(từ×NV×n²) | O(từ×NV×n) | **~90%** |
| Chi phí API | Cao | Thấp | **50-70%** |

---

## 7. Khuyến nghị triển khai

1. **Giai đoạn 1 (an toàn, ít rủi ro):** Nhóm A3, A4, A5 — tối ưu CPU/RAM thuần, không đổi hành vi.
2. **Giai đoạn 2 (giảm chi phí):** Nhóm A1, A2, B1, B2, B3 — đổi luồng xử lý, cần test kỹ.
3. **Giai đoạn 3 (tính năng mới):** Nhóm C1, C2, C3 — tăng giá trị, cần review nghiệp vụ.

> ⚠️ **Nguyên tắc:** Không tự ý sửa code trong giai đoạn nghiên cứu. Báo cáo này chỉ để review.
> Sau khi chủ dự án duyệt hướng, mới triển khai theo từng giai đoạn, mỗi giai đoạn chạy test
> (`test_meeting_api.py`, `test_meeting_clarify.py`, E2E `meeting-clarify.spec.ts`) trước khi merge.

---

## 8. Kết luận

Tính năng ghi cuộc họp của Nhịp Quán **đã rất mạnh** ở phần an toàn (human-in-loop, rule-based
fallback, chống hallucination, rollback) — **vượt trội** so với Otter/Fireflies/tl;dv. Điểm yếu
chính là **chưa tối ưu tài nguyên**: gửi toàn bộ audio lên server, gọi LLM 1 lần cho cả cuộc họp
dài, và `_levenshtein` O(n²). Tối ưu theo Nhóm A+B sẽ **giảm 70-80% RAM/băng thông và 50-70%
chi phí LLM** mà không mất đi các điểm mạnh hiện có.