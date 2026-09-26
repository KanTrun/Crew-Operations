# RÀ SOÁT KẾ HOẠCH TÍCH HỢP JEV (SYSTEM ONE) — BẢN v2

> **Ngày rà soát:** 20/09/2026.
> **Đối tượng:** `KE_HOACH_TICH_HOP_JEV_V13_SYSTEM_ONE.md` (bản sửa đổi v2).
> **Phương pháp:** đối chiếu các tuyên bố trong kế hoạch với codebase thực tế của repo `d:\Crew-Operations` (đã đọc `fb_policy.py`, `router.py`, `ca_gates`, `FreeTierRouter`, các test liên quan).

---

## 0. TÓM TẮT ĐIỀU HÀNH

**Kết luận:** Bản v2 **tốt hơn hẳn v1** — các sửa đổi về `noul`/`confidence`, `score` 0-based, nguyên tắc đơn điệu, thoái lui về phía con người, và bỏ các tuyên bố không có bằng chứng đều đúng hướng và chặt chẽ. Đây là một kế hoạch tích hợp có chất lượng cao.

Tuy nhiên, sau khi đối chiếu với codebase thực tế, có **một số điểm chưa ổn** — một số là lỗi thực tế, một số là thiếu sót về mặt kỹ thuật. Cần sửa trước khi triển khai.

---

## A. LỖI THỰC TẾ SO VỚI CODEBASE (CẦN SỬA)

### A1. `fb_policy.py` đã có sẵn bảng quyết định tất định — kế hoạch đang "phát minh lại" một phần

Kế hoạch mục 4.2 đề xuất một `route_fb()` mới với `AUTO_REPLY_WHITELIST = {khen, hoi_thong_tin, dat_ban}` và ngưỡng `confidence >= 0.70`. Nhưng codebase **đã có** `fb_policy.py` với:

- `AUTO_THRESHOLD` theo từng intent (`chao_hoi: 0.90`, `hoi_gio_dia_chi: 0.85`, `hoi_menu_gia: 0.85`)
- `COMMENT_SAFE_INTENTS` (whitelist)
- `HEALTH_KEYWORDS`, `LEGAL_KEYWORDS`, `HOSTILE_KEYWORDS`, `ASK_HUMAN_KEYWORDS` — chính là các trục mà kế hoạch đề xuất tách ra
- `PolicyContext` với các flag `sensitive_post`, `price_above_limit`, `compensation_above_limit`, `booking_system_down`...

**Vấn đề:** Kế hoạch v2 viết `route_fb()` như thể đang xây từ đầu, không nói rõ nó **thay thế hay bổ sung** `fb_policy.decide()`. Nếu thay thế, bạn phá vỡ hàng loạt test (`test_fb_policy.py` — "mọi cạnh bảng §3.2"), `PolicyDecision` contract, và audit trace. Nếu bổ sung, cần nói rõ Jev nằm ở đâu trong pipeline hiện có (trước/trong/sau `decide()`).

> **Đề xuất:** Kế hoạch nên mô tả Jev như một **nguồn tín hiệu bổ sung** đưa vào `PolicyContext` (thêm flag `jev_health_risk`, `jev_legal_threat`, `jev_hostility_score`...), để `fb_policy.decide()` giữ nguyên làm bảng quyết định duy nhất. Điều này nhất quán với chính nguyên tắc "một bảng quyết định cho mỗi luồng" của bạn.

### A2. `FreeTierRouter` thực tế đã là `groq → openrouter → bai → ollama` (không có Gemini trong live text)

Kế hoạch mục 4.4 và bảng §8 nói "Tầng 2 (Groq/OpenRouter/Gemini)". Nhưng `router.py` ghi rõ: **Gemini CHỈ dùng cho model Live (Voice Copilot + STT Live)**, live text order là `groq → openrouter → bai → ollama`. Việc nhắc Gemini trong Tầng 2 text là sai lệch với thiết kế hiện tại.

> **Đề xuất:** Sửa thành "Groq/OpenRouter/Bai/Ollama" và ghi chú Gemini chỉ cho Voice.

### A3. `VF-SEMANTIC` (mục 9.1.1) — cổng mới này chưa tồn tại, và kế hoạch chưa nói rõ nó nằm trong `ca_gates` hay là một `SignalSensor` khác

Kế hoạch đề xuất `VF-SEMANTIC` "cùng họ `ca_gates`". Nhưng `ca_gates` hiện có `VF-SCHEMA/TRACE/CONF/CONFLICT/NUM/RULE/SCOPE/STALE` — tất cả đều **tất định, không I/O** (theo ADR-002). Một cổng gọi Jev (I/O mạng) sẽ **vi phạm ADR-002** nếu đặt trong `ca_gates`. Đây là mâu thuẫn nội tại.

> **Đề xuất:** Làm rõ `VF-SEMANTIC` là một **bước tiền-xử lý** (pre-gate) dùng `SignalSensor`, không phải một cổng `ca_gates` thuần code. Hoặc đổi tên để tránh nhầm lẫn với họ VF-* tất định.

---

## B. THIẾU SÓT KỸ THUẬT

### B1. Thiếu cơ chế "đồng thuận" giữa regex và Jev khi **mâu thuẫn ngược chiều**

Nguyên tắc đơn điệu `leo_thang = regex_hit OR jev_flag` xử lý tốt chiều "Jev thêm leo thang". Nhưng kế hoạch **không xử lý chiều ngược**: khi regex **không** trúng nhưng Jev báo `nguy_co_suc_khoe` cao → leo thang (đúng). Nhưng khi regex trúng `HEALTH_KEYWORDS` (ví dụ "đau bụng") mà Jev báo `nguy_co_suc_khoe` thấp → vẫn leo thang (đúng, vì regex thắng). Vậy thực ra không có mâu thuẫn.

**Tuy nhiên**, mục 4.2 có dòng "Nếu tín hiệu mâu thuẫn (y_dinh = khen nhưng nguy_co_suc_khoe cao) thì coi là leo thang" — đây là **mâu thuẫn giữa các câu hỏi Jev**, không phải giữa regex và Jev. Kế hoạch nên tách bạch hai loại mâu thuẫn này và định nghĩa rõ hành vi cho từng loại.

### B2. `noul` không có `confidence` — kế hoạch dùng `value >= 0.30` nhưng không nói cách xử lý độ tin cậy của chính `noul`

Mục 3.3 đúng khi nói "với `noul` dùng thẳng xác suất". Nhưng `noul` trả xác suất 0–1 mà **không kèm confidence**. Vậy ngưỡng `0.30` cho `nguy_co_suc_khoe` là ngưỡng trên **xác suất thô**, không có thông tin về độ chắc chắn của chính phán đoán đó. Điều này có nghĩa: một `noul` trả `0.31` (chỉ hơn ngưỡng 0.01) sẽ leo thang, trong khi `0.29` thì không — ranh giới rất nhạy.

> **Đề xuất:** Thêm **vùng xám** (ví dụ `0.25–0.35` → chuyển hàng đợi thay vì quyết định cứng) để tránh nhạy cảm với nhiễu.

### B3. Thiếu xử lý `choice` khi Jev trả nhãn không có trong `criteria`

Kế hoạch mục 4.1 có `nguoi_thay` với `criteria` gồm tên nhân viên + `khong_neu` + `khac`. Nhưng Jev "luôn trả giá trị hợp lệ theo schema" — nếu schema chỉ cho phép các nhãn trong `criteria`, thì `khac` là nhãn hợp lệ. Tuy nhiên kế hoạch **không nói** điều gì xảy ra nếu Jev trả `khac` cho `nguoi_thay` — có nên hỏi lại nhân viên không? Có nên chuyển Quản lý không? Cần định nghĩa hành vi cho mọi nhãn, kể cả `khac`/`khong_neu`.

### B4. `schema_version` — kế hoạch ghi phiên bản bộ câu hỏi nhưng không nói **ai quản lý** và **cách bump**

Mục 3.5 nói "Phiên bản hóa bộ câu hỏi (`schema_version`)". Nhưng không nói: bộ câu hỏi nằm ở đâu (file? DB? code?), ai bump khi đổi, và làm sao đảm bảo `schema_version` khớp với `model_version` khi replay. Đây là chi tiết vận hành quan trọng cho ADR-007.

### B5. Thiếu kế hoạch **rollback** và **kill-switch** cụ thể

Kế hoạch có circuit breaker cho Jev, nhưng không nói rõ **cách tắt Jev hoàn toàn** nếu phát hiện vấn đề nghiêm trọng (ví dụ lộ dữ liệu, chất lượng tệ). Cần một feature flag toàn cục (ví dụ `jev.enabled=false`) để tắt nhanh mà không cần deploy.

---

## C. ĐIỂM MẠNH CẦN GIỮ

- **Nguyên tắc đơn điệu** (mục 3.2) — chứng minh được, đúng đắn.
- **Thoái lui về phía con người** (mục 5) — đúng tinh thần ADR-008.
- **Ẩn danh hóa + tham vấn pháp lý** (mục 6) — xử lý tốt vấn đề dữ liệu cá nhân.
- **Chạy bóng trước khi bật** (mục 7) — đúng quy trình.
- **Bỏ các tuyên bố không có bằng chứng** (mục 0.1, hàng 9) — đúng đắn.
- **Tách `SignalSensor` khỏi `FreeTierRouter`** (mục 4.4) — đúng, vì hai việc khác nhau.

---

## D. CÂU HỎI PHẢN BIỆN (MỤC 11) — ĐÁNH GIÁ

Các câu hỏi đã được viết lại trung lập, tốt. Nhưng đề xuất **thêm 2 câu**:

6. *"`fb_policy.py` đã có bảng quyết định tất định với `PolicyContext` và `AUTO_THRESHOLD` theo intent. Jev nên được đưa vào như một flag trong `PolicyContext` (để `decide()` giữ nguyên là bảng quyết định duy nhất), hay nên tạo một `route_fb()` mới thay thế? Cách nào ít phá vỡ test/contract/audit hiện có?"*

7. *"`ca_gates` hiện là các cổng tất định, không I/O (ADR-002). Một `VF-SEMANTIC` gọi Jev (I/O mạng) có vi phạm ADR-002 không, và nên đặt nó ở đâu trong pipeline để không phá vỡ nguyên tắc này?"*

---

## E. KẾT LUẬN

Bản v2 là một kế hoạch **chất lượng cao, đúng hướng**. Các vấn đề nêu trên chủ yếu là:

1. **A1 (quan trọng nhất):** chưa làm rõ quan hệ giữa Jev và `fb_policy.py` hiện có — cần xác định Jev là nguồn tín hiệu bổ sung vào `PolicyContext`, không phải thay thế `decide()`.
2. **A2:** nhầm lẫn về Gemini trong Tầng 2 (thực tế không dùng cho text).
3. **A3:** `VF-SEMANTIC` mâu thuẫn với ADR-002 nếu đặt trong `ca_gates`.
4. **B2:** thiếu vùng xám cho ngưỡng `noul` (nhạy cảm với nhiễu).
5. **B5:** thiếu kill-switch toàn cục.

---

## F. NGUỒN ĐỐI CHIẾU TRONG REPO

- `packages/agents/src/ca_agents/fb_policy.py` — bảng quyết định tất định hiện có (`AUTO_THRESHOLD`, `COMMENT_SAFE_INTENTS`, `HEALTH_KEYWORDS`, `LEGAL_KEYWORDS`, `HOSTILE_KEYWORDS`, `ASK_HUMAN_KEYWORDS`, `PolicyContext`).
- `packages/agents/src/ca_agents/router.py` — `FreeTierRouter`: live text order `groq → openrouter → bai → ollama`; Gemini chỉ cho vision/Voice.
- `packages/gates/src/ca_gates/` — `VF-SCHEMA/TRACE/CONF/CONFLICT/NUM/RULE/SCOPE/STALE`, tất cả tất định, không I/O.
- `packages/agents/tests/test_fb_policy.py` — "mọi cạnh bảng §3.2" (rủi ro phá vỡ nếu thay `decide()`).
- `docs/adr/ADR-002` (điều phối tất định), `ADR-007` (replay), `ADR-008` (fail-closed).