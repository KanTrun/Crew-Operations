# ADR-021 — LLM không bao giờ là nguồn số

## Status
Accepted (2026-09-26, nhánh `main`)

## Context

Năm trang `/quanverse` đã có endpoint trả dữ liệu thật, nhưng không chỗ nào nói
thành lời *"chuyện gì đang xảy ra, cái gì gấp, vì sao"* — người dùng phải tự đọc
số rồi tự suy ra. Thêm một trợ lý hỏi đáp là nhu cầu thật.

Nhưng đây là hệ thống vận hành quán: một câu trả lời SAII về mức tải quầy, về
người bù ca, hay về chi phí phương án sẽ khiến người trực ca ra quyết định sai.
ADR-002 đã chốt mọi tính toán là tất định; câu hỏi mới là **LLM được phép làm gì
khi nó đứng giữa người dùng và con số**.

Ba cách hỏng đã lường trước:

1. **Bịa số.** LLM sinh "quầy đang tải 92%" trong khi dữ liệu nói 72%.
2. **Nói quá dữ liệu.** Câu trả lời mượt mà khẳng định ("chắc chắn", "100%") khi
   hệ thống chỉ có một ký ức đã xác nhận.
3. **Bịa kết luận từ trang trống.** Không có bản ghi nào, nhưng LLM vẫn viết một
   đoạn văn nghe rất hợp lý — tệ hơn hẳn việc nói "chưa có dữ liệu".

## Decision

**Tách đôi trách nhiệm, và LLM không bao giờ giữ vế nào chạm tới số.**

1. **Tổng hợp tất định** — `ag_quanverse/brief.py::build_brief` gom số liệu hệ
   thống đã tính thành `QuanverseBrief` (facts/metrics/risks/next_actions/
   `grounded_refs`). Hàm này **không gọi LLM** và là điểm vào DUY NHẤT (cùng khuôn
   `ag_waste.tinh_tu_nguon`): bản tóm tắt trên màn hình và ngữ cảnh đưa cho LLM là
   **một khối**, nên không có đường nào để hai bên lệch số.

2. **Diễn đạt** — `ag_quanverse/assistant.py::answer_question`.
   - Chế độ `replay` (mặc định): câu trả lời dựng thẳng từ brief. **Không gọi
     mạng.** Vì vậy demo, CI và máy không có API key vẫn có câu trả lời đầy đủ, và
     câu trả lời đó **không thể sai số** vì nó chính là brief.
   - Chế độ `live`: `llm.complete()` chỉ nhận brief dưới dạng chữ — **không thấy
     bản ghi thô**. Sau khi sinh, câu trả lời phải qua **cổng grounding**
     `audit_answer()`: mọi con số trong câu trả lời phải có trong brief, và không
     được chứa từ tuyệt đối. Vi phạm → **bỏ lời LLM**, giữ bản tất định, ghi lý do
     vào `unsupported_claims`.

3. **Không có căn cứ thì phải NÓI RA.** `grounded = bool(citations)`. Khi
   `grounded` là `False`, câu trả lời bị ghi đè bằng câu nói rõ "chưa có bản ghi
   nào để dẫn chứng — không suy đoán nội dung", **kể cả khi brief có vài chỉ số
   bằng 0** (nếu không, người đọc tưởng "hệ thống đã kiểm tra và kết luận").

## Consequences

- **Được:** không thể có câu trả lời sai số ở chế độ replay — bất biến này kiểm
  được bằng máy (test chặn `llm.complete` rồi khẳng định nó không bị gọi). Ở chế
  độ live, LLM hỏng/hết quota là chuyện thường ngày: hệ rơi về bản tất định và
  **không báo lỗi cho người dùng**, vì câu trả lời tất định đã đầy đủ.
- **Mất:** câu trả lời ở chế độ live bị "chặn" khá dễ — một con số không có trong
  brief là đủ để bỏ lời LLM. Đây là đánh đổi CÓ CHỦ ĐÍCH: thà mất một câu văn mượt
  còn hơn trình bày một con số không có nguồn.
- **Route mới** `GET /experience/quanverse/brief/{page}` và
  `POST /experience/quanverse/ask` khai trong `EXCLUDED_ROUTES` theo khuôn
  "narration phụ trợ": chúng đọc lại dữ liệu của các route tất định đã có
  capability riêng, không điều phối hành động nào nên không phải capability mới.
- Trợ lý **không** tự đổi roster / mode / luật. Muốn đổi thì vẫn phải qua
  proposal → confirm của ADR-008. Trợ lý chỉ nói; người quyết.

## Links

- `packages/agents/src/ca_agents/ag_quanverse/brief.py` (`build_brief`)
- `packages/agents/src/ca_agents/ag_quanverse/assistant.py` (`answer_question`,
  `audit_answer`)
- `apps/web/src/ui/experience/quanverse/PageAssistant.tsx`
- `apps/api/tests/unit/test_quanverse_assistant.py` (bất biến số + grounding)
- `apps/web/e2e/quanverse-assistant.spec.ts` (5 trang + không bịa)
- ADR-002 (orchestration tất định), ADR-008 (con người quyết định),
  ADR-016 (ranh giới Grand AI Experience)
