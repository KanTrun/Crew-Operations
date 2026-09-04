# KẾ HOẠCH CHI TIẾT HOÀN THIỆN 2 TÍNH NĂNG AI AGENT

> Phạm vi: hoàn thiện đồng thời AG-FBPAGE và AG-MAILWRITER trong hệ thống NHỊP QUÁN.
>
> Hai năng lực cần đạt:
> 1. Sinh nội dung tự nhiên, đúng ngữ cảnh, có cá nhân hóa.
> 2. Tự đánh giá chất lượng, học từ phản hồi và cải thiện qua thời gian.
>
> Ngày lập kế hoạch: 2026-09-04

---

## 1. Hiện trạng và mục tiêu

### 1.1. Facebook AG-FBPAGE

Đã có:

- Nhận diện intent và tâm lý khách hàng.
- Soạn câu trả lời bằng LLM hoặc replay fallback.
- Guardrail đầu vào và supervisor đầu ra.
- Phân loại auto-send, review, escalate và block.
- Bộ nhớ khách hàng và golden examples.
- Review queue, audit và reflection thủ công.

Cần hoàn thiện:

- Lưu đầy đủ generation, context, quyết định policy và kết quả sau gửi.
- Nhớ ngữ cảnh nhiều lượt trong cùng một cuộc hội thoại.
- Nạp các playbook rule đã được duyệt trở lại prompt của agent.
- Đánh giá chất lượng dựa trên chỉnh sửa của quản lý và phản hồi tiếp theo của khách.
- Tự tạo proposal cải thiện có evidence.
- Có version, approval và rollback cho rule.
- Có scheduler và dashboard vận hành.

### 1.2. Gmail AG-MAILWRITER

Đã có:

- Draft email bằng LLM và deterministic fallback.
- Compound Context cho ca làm, tồn kho và báo cáo.
- Tone Memory học lời chào, chữ ký, độ dài và mẫu email.
- Học từ bản email được quản lý chỉnh sửa khi duyệt `SEND_MAIL`.
- Gửi SMTP Gmail thật hoặc fallback replay.
- 14 test riêng cho mailwriter và mail service đang pass.

Cần hoàn thiện:

- Tách rõ dữ liệu sự thật, phong cách và yêu cầu nghiệp vụ trong prompt.
- Kiểm tra tất định trước khi duyệt/gửi.
- Lưu diff giữa draft và email cuối cùng, thay vì chỉ lưu sample.
- Đo edit rate, reject rate, lỗi context và lỗi gửi.
- Có Gmail Reflection riêng.
- Sinh và duyệt proposal phong cách/cấu trúc email.
- Áp dụng rule đã duyệt vào draft sau đó.
- Theo dõi chất lượng sau khi gửi.

### 1.3. Mục tiêu cuối cùng

```text
Generation
  -> Deterministic Quality Gate
  -> Human Approval hoặc Auto-send Policy
  -> Feedback Event
  -> Evaluation
  -> Reflection
  -> Rule Proposal
  -> Human Approval
  -> Versioned Memory / Rules
  -> Generation lần sau
```

Agent không tự ghi database, không tự đổi policy và không tự áp dụng rule chưa được duyệt. Agent chỉ sinh nội dung và đề xuất; API/orchestration chịu trách nhiệm lưu, duyệt, áp dụng và audit.

---

## 2. Nguyên tắc kỹ thuật bắt buộc

1. **Contracts-first:** DTO và schema được thêm vào `packages/contracts` trước khi triển khai API.
2. **Deterministic policy:** quyết định gửi, review, escalate và block không do LLM quyết định.
3. **Fail closed:** thiếu context, sai số liệu, vi phạm safety hoặc confidence thấp thì không auto-send.
4. **Human-in-the-loop:** mọi rule mới, policy mới và nội dung nhạy cảm phải qua quản lý/chủ quán.
5. **Replay-safe:** `CA_AGENT_MODE=replay` phải chạy tất định, không cần mạng hoặc credential thật.
6. **Version hóa:** mỗi generation phải có agent version, prompt version, rule version và context snapshot.
7. **Audit đầy đủ:** phải truy ngược được từ rule/proposal đến các draft và feedback tạo ra nó.
8. **Không bịa dữ liệu:** dữ liệu vận hành phải đến từ nguồn xác thực; không có dữ liệu thì nói rõ là thiếu dữ liệu.
9. **Rollback được:** mọi memory/rule đã active phải có trạng thái pause hoặc rollback.
10. **Bảo vệ bí mật:** không ghi token, App Password hoặc dữ liệu nhạy cảm vào log, fixture hay tài liệu.

---

## 3. Kiến trúc dữ liệu dùng chung

### 3.1. Các contract cần thêm

Đề xuất thêm:

```text
packages/contracts/
  ai_generation_record.schema.json
  ai_feedback_event.schema.json
  ai_evaluation.schema.json
  ai_rule_proposal.schema.json
```

### 3.2. Generation record

```json
{
  "id": "gen_123",
  "store_id": "quan_01",
  "channel": "gmail",
  "conversation_id": null,
  "request": "Nhắc Minh ngày mai đi ca sáng",
  "draft": {
    "subject": "...",
    "body": "..."
  },
  "context_snapshot": {},
  "agent_version": "mailwriter-v1",
  "prompt_version": "mail-v1",
  "rule_version": "style-v3",
  "policy_action": "queue_review",
  "created_at": "2026-09-04T10:00:00Z"
}
```

### 3.3. Feedback event

```json
{
  "id": "feedback_123",
  "store_id": "quan_01",
  "generation_id": "gen_123",
  "channel": "gmail",
  "type": "manager_edit",
  "original": {
    "subject": "...",
    "body": "..."
  },
  "final": {
    "subject": "...",
    "body": "..."
  },
  "edited_fields": ["body"],
  "actor_role": "chu_quan",
  "created_at": "2026-09-04T10:05:00Z"
}
```

Các loại feedback tối thiểu:

```text
manager_approve
manager_edit
manager_reject
customer_positive
customer_negative
customer_followup
send_success
send_failure
manual_rating
```

### 3.4. Evaluation record

```json
{
  "id": "eval_123",
  "store_id": "quan_01",
  "generation_id": "gen_123",
  "scores": {
    "accuracy": 1.0,
    "naturalness": 0.8,
    "tone": 1.0,
    "safety": 1.0,
    "personalization": 0.7,
    "completeness": 0.9
  },
  "passed": true,
  "flags": [],
  "evaluator": "deterministic-v1",
  "created_at": "2026-09-04T10:05:01Z"
}
```

### 3.5. Rule proposal

```json
{
  "id": "proposal_123",
  "store_id": "quan_01",
  "channel": "gmail",
  "rule_type": "style",
  "rule": "Email nội bộ cho nhân viên ưu tiên mở đầu bằng 'Chào em'.",
  "evidence_count": 6,
  "evidence_ids": ["feedback_1", "feedback_2"],
  "confidence": 0.88,
  "status": "pending",
  "created_at": "2026-09-04T23:00:00Z"
}
```

Vòng đời proposal/rule:

```text
pending -> approved -> active -> paused -> rolled_back
pending -> rejected
```

### 3.6. Multi-tenant và cô lập dữ liệu

`store_id` là trường **bắt buộc** trong cả bốn contract: generation, feedback,
evaluation và rule proposal. Có thể dùng tên `tenant_id` ở tầng hạ tầng nếu cần,
nhưng phải có mapping rõ ràng và không được để một record thiếu định danh cửa hàng.

Mọi rule active cũng phải có scope:

```json
{
  "store_id": "quan_01",
  "channel": "gmail",
  "intent_scope": ["notify_shift"],
  "audience_scope": ["employee"],
  "status": "active"
}
```

Quy tắc cô lập:

- API lấy `store_id` từ session/authorization, không tin `store_id` do client tự gửi.
- Mọi query generation, feedback, evaluation, proposal, memory và rule đều bắt buộc lọc theo `store_id`.
- Không cho phép manager của cửa hàng A xem, duyệt, áp dụng hoặc suy luận từ dữ liệu cửa hàng B.
- Cache key phải chứa `store_id`; không dùng cache chỉ theo `channel` hoặc `intent`.
- Evidence trong proposal chỉ được tham chiếu record cùng `store_id`.
- Test bắt buộc có case cross-tenant access phải trả `403` hoặc danh sách rỗng phù hợp.
- Background job phải chạy theo từng cửa hàng, không gom dữ liệu các cửa hàng vào một reflection report.

Nghiệm thu: tạo hai cửa hàng có cùng `channel` và `intent`, sau đó chứng minh generation,
memory, rule, metrics và proposal của cửa hàng này không xuất hiện ở cửa hàng kia.

---

## 4. Giai đoạn 0 - Chuẩn hóa nền tảng

### Mục tiêu

Có một nơi lưu generation, feedback, evaluation và proposal cho cả hai channel.

### Công việc

1. Thêm JSON schema và Python/TypeScript DTO tương ứng.
2. Tạo lớp persistence dùng SQLite/KV hiện có.
3. Tạo key hoặc bảng riêng theo channel, tránh trộn dữ liệu Facebook và Gmail.
4. Thêm idempotency key để một event không bị lưu trùng.
5. Thêm redaction cho email, số điện thoại, token và dữ liệu riêng tư trong log.
6. Gắn version vào mọi generation.
7. Viết test round-trip: ghi, đọc, cập nhật trạng thái và truy vết evidence.
8. Với Facebook, tạo khóa dedupe từ `store_id + page_id + event_type + message_id`
   hoặc `store_id + page_id + event_type + comment_id`; không dùng timestamp làm khóa chính.
9. Lưu raw event tối thiểu cần thiết và trạng thái `received/processing/processed/ignored_duplicate/failed`.
10. Tạo unique constraint hoặc atomic `put-if-absent`; nếu event đã tồn tại thì trả HTTP 200
  và không gọi classifier, LLM hoặc Graph API lần thứ hai.

### Đầu ra

```text
packages/contracts/ai_*.schema.json
apps/api/src/ca_api/ai_learning/
packages/agents/src/ca_agents/learning/
```

### Tiêu chí nghiệm thu

- Có thể truy từ feedback đến generation ban đầu.
- Có thể truy từ rule proposal đến tối thiểu các evidence tương ứng.
- Event gửi lại không tạo bản ghi trùng.
- Test replay không cần SMTP, Facebook token hoặc LLM thật.

---

## 5. Giai đoạn 1 - Hoàn thiện nội dung tự nhiên và cá nhân hóa

## 5.1. Gmail AG-MAILWRITER

### A. Chuẩn hóa prompt thành ba phần

```text
FACTS
  Dữ liệu vận hành xác thực, không được thay đổi.

STYLE
  Tone Memory, cách xưng hô, độ dài, chữ ký và mẫu đã duyệt.

TASK
  Mục tiêu email, người nhận và yêu cầu phản hồi.
```

LLM phải ưu tiên `FACTS` và không được tự thêm số liệu, thời gian, nhân sự hoặc cam kết ngoài context.

### B. Mở rộng recipient memory

Đề xuất key:

```text
mail_recipient_memory:<store_id>:<recipient_id>
```

Chỉ lưu thông tin cần thiết:

```json
{
  "preferred_name": "Minh",
  "role": "Pha chế",
  "formality": "than_thien",
  "last_interaction_at": "..."
}
```

Không suy đoán hoặc lưu thuộc tính nhạy cảm không cần cho việc gửi mail.

### C. Cải thiện trích xuất request

Thay việc chỉ dò từ khóa bằng pipeline:

```text
raw_request
  -> intent
  -> entities
  -> verified context lookup
  -> draft
```

Entity cần trích xuất:

- Người nhận.
- Ngày và giờ.
- Ca làm.
- Mặt hàng.
- Số lượng.
- Hạn phản hồi.
- Mức độ khẩn cấp.

Nếu không tìm thấy dữ liệu thật, trả `missing_context` và đưa vào review.

### D. Hoàn thiện deterministic fallback

Fallback cần:

- Giữ nguyên số liệu xác thực.
- Áp dụng Tone Memory.
- Không dùng dữ liệu mặc định giả như dữ liệu thật.
- Gắn cờ nếu request cần thông tin chưa có.
- Không tự đưa ra lời hứa tài chính hoặc pháp lý.

### E. Recipient và email safety

Kiểm tra:

- Email hợp lệ.
- Đúng người nhận dự kiến.
- Không gửi nhầm danh sách.
- Không để lộ địa chỉ email của nhân viên khác.
- Nội dung nhạy cảm cần cấp duyệt phù hợp.

## 5.2. Facebook AG-FBPAGE

### A. Bộ nhớ hội thoại nhiều lượt

Lưu state ngắn hạn theo PSID/thread:

```json
{
  "last_intent": "dat_ban",
  "pending_question": "so_nguoi",
  "collected_slots": {
    "date": "2026-09-06",
    "time": "19:00"
  },
  "turn_count": 3,
  "expires_at": "..."
}
```

Agent không hỏi lại thông tin đã có và tự chuyển review khi khách hỏi lại quá nhiều lần.

### B. Prompt hội thoại

Prompt cần có:

- Tên khách nếu khách đã cung cấp.
- Intent hiện tại.
- Lịch sử hội thoại giới hạn trong số lượt cần thiết.
- Cảm xúc khách hàng.
- Slots đã thu thập.
- Câu hỏi còn thiếu.
- Active policy/playbook rules.

### C. Nạp rule đã duyệt

Tạo provider lấy các rule `active` theo channel và intent:

```text
active_rules = get_active_rules(channel="facebook", intent=intent)
```

Đưa rule vào `build_fb_system_prompt()` và ghi `rule_version` vào generation record.

Rule chưa được duyệt không được đưa vào prompt.

### D. Phân biệt Messenger và comment

Comment công khai:

- Chỉ trả lời câu ngắn và thông tin công khai.
- Không nhắc dữ liệu riêng tư.
- Không hỏi số điện thoại trên comment.
- Ngưỡng auto-send cao hơn Messenger.
- Khi cần chi tiết thì mời khách chuyển sang inbox.

---

## 6. Giai đoạn 2 - Quality Gate trước khi gửi

## 6.1. Gmail Quality Gate

Tạo module:

```text
packages/agents/src/ca_agents/ag_mailwriter/quality_gate.py
```

Các kiểm tra:

| Kiểm tra | Hành động |
|---|---|
| Thiếu subject hoặc body | Block |
| Email người nhận không hợp lệ | Block |
| Subject không có tiền tố quán | Flag hoặc sửa tất định |
| Subject vượt giới hạn | Flag |
| Có placeholder | Queue |
| Số liệu không khớp context | Block |
| Có lời hứa hoàn tiền/đền bù | Queue hoặc escalate |
| Lộ dữ liệu nội bộ | Block |
| Không có lời chào/chữ ký | Flag |
| Draft dài bất thường | Flag |

Output:

```python
QualityGateResult(
    passed=True,
    action="queue_review",
    score=0.92,
    flags=[],
)
```

## 6.2. Facebook Quality Gate

Chuẩn hóa supervisor output thành kết quả có cấu trúc:

```python
SupervisorResult(
    passed=False,
    action="queue_review",
    score=0.41,
    flags=["financial_commitment"],
)
```

Các dimension:

- Đúng intent.
- Đúng dữ liệu.
- Đúng policy.
- Tự nhiên.
- Phù hợp cảm xúc.
- Không hứa tài chính.
- Không lộ dữ liệu nội bộ.
- Không lộ thân phận AI.

Nếu supervisor fail, quyết định phải hạ xuống review dù policy trước đó là auto-send.

### 6.3. Công thức score và threshold deterministic

Mỗi dimension được chuẩn hóa trong đoạn $[0, 1]$. Với channel Gmail, score tổng hợp là:

```text
mail_score =
  0.30 * accuracy
  + 0.20 * safety
  + 0.15 * completeness
  + 0.15 * tone
  + 0.10 * actionability
  + 0.10 * personalization
```

Với Facebook:

```text
fb_score =
  0.30 * policy_compliance
  + 0.20 * accuracy
  + 0.15 * intent_fit
  + 0.15 * emotional_fit
  + 0.10 * resolution_likelihood
  + 0.10 * naturalness
```

Điều kiện `passed` là:

```text
passed =
  score >= 0.80
  AND safety >= 0.90
  AND accuracy >= 0.90
  AND no_hard_fail_flag
```

Trong đó `no_hard_fail_flag` bao gồm sai số liệu, hứa hoàn tiền trái quyền,
lộ dữ liệu nội bộ, prompt injection lọt qua, thiếu người nhận hoặc recipient không hợp lệ.
Không được dùng trung bình để che một dimension quan trọng bị điểm thấp.

Confidence của classifier phải là xác suất đã calibration trên golden set, không phải số do LLM tự khai.
Với mỗi intent, tính:

```text
confidence = correct_predictions / evaluated_predictions
```

theo từng bucket confidence. Dùng `isotonic` hoặc `Platt calibration` offline khi có đủ dữ liệu;
MVP dùng bảng calibration versioned. Confidence dưới ngưỡng policy tương ứng sẽ vào review.
Các số như `0.88` hoặc `0.91` trong report chỉ hợp lệ khi kèm `sample_count`, `window`
và `calibration_version`.

Threshold phải có version, channel và store scope. Không tự thay threshold dựa trên một event đơn lẻ.

### 6.4. Phát hiện xung đột rule

Trước khi một rule chuyển sang `active`, chạy conflict checker theo:

```text
store_id + channel + intent_scope + audience_scope
```

Conflict checker bắt buộc xử lý ba lớp:

1. **Exact key conflict:** cùng scope và cùng thuộc tính nhưng khác value, ví dụ `than_mật`
   và `trang_trọng` cho cùng intent.
2. **Priority conflict:** hai rule cùng scope nhưng priority bằng nhau và hành động khác nhau.
3. **Prompt contradiction:** rule có cụm từ phủ định lẫn nhau, ví dụ `luôn hỏi số điện thoại`
   và `không hỏi thông tin liên hệ công khai`.

Nếu conflict:

- Không activate rule mới.
- Tạo trạng thái `conflict_pending` và hiển thị hai rule cùng evidence cho chủ quán.
- Chỉ cho phép activate sau khi người có quyền chọn rule thắng, chỉnh scope hoặc vô hiệu hóa rule cũ.
- Không giải quyết xung đột bằng thứ tự list hoặc bằng LLM.

Khi inject prompt, provider phải trả rule đã resolve conflict, sắp xếp theo
`priority DESC, created_at DESC`, đồng thời ghi lại danh sách rule IDs đã dùng.

---

## 7. Giai đoạn 3 - Ghi nhận feedback và kết quả

## 7.1. Gmail

Khi xử lý `SEND_MAIL`, lưu đầy đủ:

- Draft ban đầu.
- Subject cuối.
- Body cuối.
- Field nào bị sửa.
- Diff nội dung.
- Người duyệt và vai trò.
- Trạng thái gửi SMTP.
- Lỗi nếu gửi thất bại.

Phải phân biệt:

```text
approved_without_edit
approved_with_edit
rejected
sent
send_failed
```

`mail_style_memory` tiếp tục được duy trì để tương thích, nhưng dữ liệu học mới phải tham chiếu tới feedback event.

## 7.2. Facebook

Mỗi message/comment cần ghi:

- Input đã sanitize.
- Thread và PSID đã ẩn danh hóa nếu có thể.
- Intent và confidence.
- Context được dùng.
- Draft.
- Policy decision.
- Supervisor flags.
- Bản quản lý sửa.
- Kết quả gửi.
- Tin nhắn tiếp theo của khách.
- Sentiment trước/sau.
- Resolved, escalated hoặc reopened.
- Thời gian phản hồi.

Sự kiện khách gửi tin tiếp theo trong thời gian ngắn phải được dùng làm tín hiệu: câu trả lời trước có thể chưa giải quyết yêu cầu.

---

## 8. Giai đoạn 4 - Evaluation Engine

### 8.1. Evaluator chung

Tạo interface:

```python
class AIEvaluator(Protocol):
    def evaluate(self, generation, feedback, context) -> EvaluationResult:
        ...
```

### 8.2. Gmail evaluator

Chấm:

- Accuracy: số liệu có đúng không.
- Completeness: có đủ mục tiêu email không.
- Tone: có đúng gu không.
- Naturalness: có câu robot hoặc lặp không.
- Actionability: người nhận có biết cần làm gì không.
- Safety: có cam kết ngoài thẩm quyền không.
- Personalization: có dùng đúng người nhận và vai trò không.

Các tín hiệu:

- Có bị sửa subject không.
- Có bị sửa body không.
- Tỷ lệ số từ thay đổi.
- Có bị từ chối không.
- SMTP có thành công không.

### 8.3. Facebook evaluator

Chấm:

- Intent accuracy.
- Policy compliance.
- Emotional fit.
- Resolution rate.
- Duplicate question rate.
- Time to first response.
- Manager edit rate.
- Escalation correctness.
- Customer follow-up rate.
- Public comment safety.

### 8.4. Không dùng LLM cho policy gate

LLM có thể hỗ trợ phân tích văn phong hoặc gom nhóm lỗi trong reflection, nhưng kết quả không được tự thay đổi quyết định gửi hoặc quyền duyệt.

---

## 9. Giai đoạn 5 - Reflection và self-improvement

## 9.1. Gmail Reflection

Tạo:

```text
packages/agents/src/ca_agents/ag_mailwriter/reflection.py
```

Reflection chạy hàng ngày hoặc sau khi đủ số lượng email, ví dụ 20 email.

Phân tích:

- Tổng số email.
- Tỷ lệ bị sửa.
- Tỷ lệ bị từ chối.
- Subject edit rate.
- Body edit rate.
- Các cụm từ bị xóa hoặc thay nhiều nhất.
- Lời chào thường bị thay.
- Chữ ký thường bị thay.
- Loại request thường thiếu context.
- Email thường quá dài hoặc quá ngắn.
- Lỗi SMTP.
- Thời gian chờ duyệt.

Ví dụ finding:

```json
{
  "type": "too_formal_greeting",
  "count": 11,
  "evidence_ids": ["gen_1", "gen_2", "gen_3"],
  "confidence": 0.91
}
```

Chỉ tạo proposal khi:

- Có tối thiểu số evidence cấu hình được.
- Mẫu lặp xuất hiện trên nhiều ngày hoặc nhiều email.
- Không mâu thuẫn với rule đang active.
- Có thể giải thích bằng evidence cụ thể.

## 9.2. Facebook Reflection

Mở rộng `run_nightly_cskh_reflection()` thành quy trình:

1. Đọc các thread đã xử lý trong kỳ.
2. Ghép input, draft, policy, supervisor và kết quả gửi.
3. Ghép feedback quản lý.
4. Đọc customer follow-up và sentiment sau trả lời.
5. Phân loại lỗi.
6. Tính điểm theo intent/channel.
7. Tìm pattern lặp.
8. Tạo rule proposal.
9. Gửi proposal vào hàng chờ duyệt.

Nhóm lỗi:

```text
wrong_intent
too_robotic
too_long
missed_customer_emotion
asked_redundant_question
unsupported_promise
missing_escalation
incorrect_public_reply
missing_context
```

## 9.3. Approval và application

Không auto-apply proposal trong giai đoạn đầu.

Luồng bắt buộc:

```text
Reflection
  -> Proposal pending
  -> Manager review
  -> Approved
  -> Active version
  -> Prompt/policy provider đọc rule
```

Mỗi rule active phải có:

- ID.
- Version.
- Channel.
- Intent scope.
- Người duyệt.
- Thời điểm hiệu lực.
- Evidence.
- Rollback target.

---

## 10. Giai đoạn 6 - API và UI quản trị

### 10.1. API đề xuất

```text
GET  /api/v1/ai/generations
GET  /api/v1/ai/generations/{id}

POST /api/v1/ai/feedback
GET  /api/v1/ai/feedback

POST /api/v1/ai/evaluations/run
GET  /api/v1/ai/evaluations/summary

POST /api/v1/ai/reflection/run
GET  /api/v1/ai/reflection/reports

GET  /api/v1/ai/rules/proposals
POST /api/v1/ai/rules/proposals/{id}/approve
POST /api/v1/ai/rules/proposals/{id}/reject
POST /api/v1/ai/rules/{id}/pause
POST /api/v1/ai/rules/{id}/rollback
```

API phải kiểm tra role:

- Quản lý được xem và duyệt nội dung thuộc phạm vi.
- Chủ quán được duyệt rule nhạy cảm và escalation.
- Nhân viên không được xem dữ liệu học hoặc nội dung của người khác nếu không cần.

### 10.2. UI Gmail

Cần có:

- Danh sách draft và trạng thái.
- Draft gốc và bản cuối cùng cạnh nhau.
- Highlight diff.
- Lý do quality gate flag.
- Nút approve, edit, reject.
- Tone Memory hiện tại.
- Edit rate theo tuần.
- Reflection findings.
- Rule proposals pending.
- Lịch sử version và rollback.

### 10.3. UI Facebook

Cần có:

- Inbox khách hàng riêng.
- Timeline hội thoại.
- Intent và confidence.
- Policy decision.
- Supervisor flags.
- SLA và mức ưu tiên.
- Draft và bản quản lý sửa.
- Nút gửi, sửa, chuyển chủ quán.
- Reflection findings.
- Rule proposals và version đang active.

---

## 11. Giai đoạn 7 - Scheduler và vận hành

### MVP

Ban đầu cho phép chạy thủ công:

```text
POST /api/v1/ai/reflection/run?channel=gmail
POST /api/v1/ai/reflection/run?channel=facebook
```

Mục đích là kiểm tra output trước khi tự động hóa.

### Production schedule

| Tác vụ | Tần suất |
|---|---:|
| Ghi generation/feedback | Ngay lập tức |
| Quality evaluation | Trước khi gửi |
| Tổng hợp metrics | Mỗi giờ |
| Gmail reflection | Hàng ngày |
| Facebook reflection | Hàng ngày |
| Báo cáo chất lượng | Hàng tuần |
| Dọn dữ liệu cũ | Hàng tuần |

Mỗi job cần:

- Idempotency key.
- Start/end log.
- Số record đọc và xử lý.
- Số evaluation tạo.
- Số proposal tạo.
- Error count.
- Duration.
- Retry có giới hạn.
- Không tạo proposal trùng.

### 11.1. Chính sách retention và xóa dữ liệu

Áp dụng mặc định theo từng cửa hàng. Có thể cấu hình ngắn hơn nhưng không dài hơn nếu chưa
được chủ quán phê duyệt:

| Loại dữ liệu | Retention mặc định | Cách xử lý hết hạn |
|---|---:|---|
| Raw Facebook webhook/event | 7 ngày | Xóa vĩnh viễn sau khi dedupe và xử lý |
| Nội dung hội thoại Facebook chứa PII | 90 ngày | Xóa body/PII, giữ aggregate metrics đã ẩn danh |
| Email draft/body và bản chỉnh sửa | 180 ngày | Xóa nội dung, giữ score và metadata tối thiểu |
| Generation/feedback/evaluation metadata | 365 ngày | Xóa hoặc anonymize sau khi hết hạn |
| Audit quyết định gửi, rule approval/rollback | 730 ngày | Giữ metadata audit, không giữ secret/body nếu không cần |
| Rule active và version hiện hành | Trong thời gian hiệu lực | Giữ đến khi rollback + 730 ngày |
| Backup mã hóa | 35 ngày | Rotation tự động; backup hết hạn bị xóa |

Nguyên tắc:

- PII gồm tên, email, số điện thoại, PSID mapping và nội dung khách gửi.
- Khi xóa nội dung, giữ hash/ID, channel, `store_id`, thời điểm, action và score để duy trì metrics.
- Xóa theo `store_id`, có dry-run, số lượng record và audit log.
- Có endpoint yêu cầu xóa dữ liệu của một khách hoặc một cửa hàng theo quyền chủ quán.
- Legal hold hoặc sự cố đang điều tra được đánh dấu để tạm dừng xóa, có thời hạn rõ ràng.
- Không log raw body, access token, App Password hoặc full recipient list.

### 11.2. Circuit breaker tự động

Circuit breaker áp dụng độc lập theo `store_id + channel + traffic_class`, tối thiểu gồm
`facebook_auto_send` và `gmail_auto_approve`. Các trạng thái:

```text
closed -> tripped -> half_open -> closed
```

MVP dùng các cửa sổ và ngưỡng sau:

| Điều kiện trong 15 phút gần nhất | Hành động |
|---|---|
| Có ít nhất 20 auto actions và reject/edit bất thường >= 25% | Pause auto-send |
| Có ít nhất 20 auto actions và hard safety violation >= 1 | Pause ngay |
| Có ít nhất 20 auto actions và false auto-send >= 2 | Pause ngay |
| Có ít nhất 10 lần gửi và send failure >= 30% | Pause channel |
| LLM/schema failure >= 5 lần trong 5 phút | Pause LLM path, dùng replay/review |

`false_auto_send` là sự kiện được manager đánh dấu là auto-send sai hoặc vi phạm policy;
không suy ra từ một tín hiệu mơ hồ. `reject/edit rate` được tính:

```text
(rejected + materially_edited) / (approved + rejected + materially_edited)
```

Sau khi trip:

1. Chuyển traffic mới sang `queue_review` hoặc fallback an toàn.
2. Ghi lý do, metric snapshot, `store_id`, rule/model version và thời điểm.
3. Gửi cảnh báo cho on-call và chủ quán.
4. Sau tối thiểu 30 phút, người có quyền xác nhận nguyên nhân và chuyển `half_open`.
5. Half-open chỉ cho 5 event hoặc 10% traffic, tùy giá trị nhỏ hơn; không có hard fail và score đạt ngưỡng mới đóng breaker.

Có nút disable khẩn cấp toàn hệ thống và riêng từng cửa hàng/channel. Disable thủ công có ưu tiên
cao hơn mọi cấu hình auto-send.

### 11.3. Backup và khôi phục

Audit trail và learning data phải được backup vì mất dữ liệu sẽ làm mất khả năng truy vết:

- SQLite/KV: backup snapshot nhất quán mỗi ngày và incremental WAL mỗi giờ khi production.
- Giữ ít nhất 35 ngày backup online và 2 snapshot cuối tháng trong 12 tháng.
- Backup mã hóa khi lưu và khi truyền; key tách khỏi file backup.
- Mỗi backup có checksum, timestamp, `store_id` coverage và schema version.
- Hàng tuần restore test vào database tạm, kiểm tra số record và truy vấn mẫu.
- Khi khôi phục, dừng writer, restore snapshot, replay WAL, chạy migration/checksum rồi mới mở traffic.
- Ghi incident và khoảng thời gian dữ liệu có thể mất: RPO <= 1 giờ, RTO <= 4 giờ.
- Không đưa secret production vào backup test hoặc fixture.

### 11.4. RACI và incident response

| Hoạt động | A - Accountable | R - Responsible | C - Consulted | I - Informed |
|---|---|---|---|---|
| Duyệt Facebook message nhạy cảm | Chủ quán | Quản lý ca | AG Supervisor | Nhân viên liên quan |
| Duyệt Gmail draft | Quản lý/chủ quán | Người ra lệnh | AG-MAILWRITER | Người nhận |
| Review reflection hàng ngày | Quản lý vận hành | AI/ops engineer | Chủ quán | Team |
| Review report hàng tuần | Chủ quán | Quản lý vận hành | Product/engineering | Team |
| Approve rule hoặc model release | Chủ quán | Engineering | Quản lý vận hành | Team |
| Disable auto-send khẩn cấp | On-call hoặc chủ quán | Người phát hiện sự cố | Engineering | Quản lý vận hành |
| Backup/restore và retention | Engineering lead | Ops engineer | Security/data owner | Chủ quán |

Khi phát hiện auto-send sai:

1. Disable riêng channel/store; nếu chưa rõ phạm vi thì disable toàn hệ thống.
2. Lưu generation ID, event ID, `store_id`, model/prompt/rule version và nội dung trong thời hạn retention.
3. Dừng rule canary/model release liên quan và chuyển traffic sang review/fallback.
4. Phân loại P0: an toàn/pháp lý/tiền; P1: khách hàng nghiêm trọng; P2: văn phong/lỗi vận hành.
5. Với P0/P1, người thật đính chính hoặc liên hệ khách; agent không tự xử lý thay.
6. Trong 24 giờ xác định nguyên nhân, phạm vi ảnh hưởng và biện pháp ngăn lặp.
7. Chỉ mở lại sau regression test, xác nhận owner và postmortem ngắn.

SLA nội bộ: acknowledge P0 trong 15 phút, P1 trong 30 phút; cập nhật mỗi 30 phút tới khi an toàn.
Mọi disable, rollback và re-enable đều phải có actor, lý do và timestamp.

---

## 12. Lộ trình triển khai theo PR

## 12.0. Quản lý phiên bản model và prompt

Mỗi generation phải ghi:

```text
provider
model_id
model_revision hoặc release_date
prompt_version
temperature
tool_context_hash
```

Khi đổi model, provider, system prompt hoặc schema output:

1. Tạo một `model release candidate` có version riêng; không ghi đè version cũ.
2. Chạy toàn bộ golden set Facebook và Gmail ở replay/live mock, gồm cả hard-negative,
   PII, policy, số liệu sai và prompt injection.
3. So sánh với baseline: pass rate, hard-fail count, factual accuracy, safety score,
   edit rate dự đoán và latency.
4. Không rollout nếu có bất kỳ hard safety regression nào, factual accuracy giảm hơn 1%,
   hoặc golden pass rate giảm hơn 3% so với baseline nếu chưa có phê duyệt ngoại lệ.
5. Lưu report cùng model/prompt version và yêu cầu owner phê duyệt.
6. Chạy canary model trên traffic shadow trước; chỉ promote khi metrics trong ngưỡng.
7. Giữ model cũ đủ thời gian rollback và ghi rõ migration/rollback command trong runbook.

Nếu model live lỗi hoặc JSON không hợp lệ, quality gate phải chuyển sang deterministic fallback
hoặc review; không tự retry vô hạn.

## 12.0.1. Canary rollout cho rule mới

Rule sau khi được duyệt không mặc nhiên nhận 100% traffic. Rule có các trường:

```json
{
  "rollout": {
    "mode": "canary",
    "percentage": 10,
    "start_at": "...",
    "end_at": "...",
    "min_sample": 20
  }
}
```

Luồng rollout:

```text
approved -> canary_10 -> canary_50 -> active_100
```

- Giai đoạn đầu: 10% traffic hoặc tối thiểu 20 event, tùy điều kiện nào đến sau.
- Giai đoạn hai: 50% traffic sau khi không có hard fail, safety violation hoặc conflict.
- Full rollout chỉ khi edit/reject rate không xấu hơn baseline quá 5 điểm phần trăm
  và score không giảm quá 3 điểm phần trăm.
- Phân bổ canary ổn định theo hash của `store_id + conversation_id/recipient_id`,
  tránh cùng một cuộc hội thoại đổi rule giữa các lượt.
- Gắn `rule_version` và `rollout_bucket` vào generation record.
- Nếu metric vượt breaker hoặc có hard fail, tự rollback về rule version trước.
- Rule canary không được dùng cho intent nhạy cảm nếu chưa có owner phê duyệt riêng.

### PR 1 - Contracts và persistence

Phạm vi:

- Schema và DTO.
- Generation/feedback/evaluation/proposal storage.
- Version và audit.
- `store_id` bắt buộc, tenant filter và cross-tenant access test.
- Facebook `message_id/comment_id` dedupe atomic.
- Backup snapshot/checksum cho learning store.
- Unit test round-trip.

Nghiệm thu:

- Lưu/đọc/truy vết được toàn bộ event.
- Không thay đổi behavior hiện tại của Facebook/Gmail.

### PR 2 - Gmail Quality Gate và feedback diff

Phạm vi:

- `quality_gate.py`.
- Ghi generation trước khi gửi.
- Ghi approve/edit/reject/send result.
- Diff subject/body.
- Giữ tương thích `mail_style_memory`.
- Công thức score, hard-fail và threshold version.

Nghiệm thu:

- Email sai số liệu bị chặn.
- Email có dữ liệu thiếu được đưa vào review.
- Draft sửa được truy ra chính xác.
- Test Gmail hiện tại vẫn pass.

### PR 3 - Gmail Reflection

Phạm vi:

- Gmail evaluator.
- Edit/reject metrics.
- Reflection report.
- Style rule proposal.
- Approval/rejection API.
- Nạp active style rule vào mailwriter.
- Conflict checker và canary rollout cho style rule.

Nghiệm thu:

- Tạo được finding từ dữ liệu thật.
- Proposal có evidence.
- Rule rejected không ảnh hưởng draft.
- Rule approved ảnh hưởng draft kế tiếp.

### PR 4 - Facebook rule injection

Phạm vi:

- Provider active playbook rules.
- Nạp rule vào prompt AG-FBPAGE.
- Rule version trong audit.
- Pause/rollback.
- Conflict checker, rule scope theo `store_id` và canary bucket ổn định theo thread.

Nghiệm thu:

- Rule approved thực sự thay đổi behavior liên quan.
- Rule pending không ảnh hưởng output.
- Rollback trả behavior về version trước.

### PR 5 - Facebook Reflection nâng cấp

Phạm vi:

- Conversation evaluator.
- Customer follow-up signal.
- Complaint/escalation metrics.
- Error pattern và proposal.
- Reflection report.

Nghiệm thu:

- Phân biệt được lỗi intent, cảm xúc, policy và context.
- Khiếu nại nặng luôn escalate.
- Không tự thay đổi policy.

### PR 6 - UI, scheduler và rollout

Phạm vi:

- Màn hình diff và proposal.
- Dashboard metrics.
- Job định kỳ.
- Feature flags.
- Runbook và alert.
- Circuit breaker tự động, disable khẩn cấp, RACI, incident response và restore test.

Nghiệm thu:

- Job chạy lặp không duplicate.
- Có audit và log đủ để điều tra.
- Có thể tắt riêng Facebook learning, Gmail learning và auto-send.

---

## 13. Bộ test và đánh giá

### 13.1. Gmail unit tests

- Draft replay cơ bản.
- Draft có shift context.
- Draft có inventory context.
- Draft có daily summary context.
- Tone Memory greeting/signoff/brevity.
- Live LLM JSON hợp lệ.
- LLM JSON lỗi và fallback.
- Thiếu context.
- Số liệu mâu thuẫn context.
- Placeholder.
- Cam kết tài chính.
- Email sai recipient.
- SMTP thành công.
- SMTP thất bại.
- Feedback không sửa.
- Feedback sửa subject.
- Feedback sửa body.
- Reflection tạo finding và proposal.
- Rule approved được áp dụng.
- Rule rejected không được áp dụng.

### 13.2. Facebook unit tests

- Chào hỏi.
- Hỏi giờ/địa chỉ.
- Hỏi menu.
- Tư vấn món.
- Đặt bàn nhiều lượt.
- Khiếu nại nhẹ.
- Khiếu nại nặng.
- Prompt injection.
- Spam và rate limit.
- Comment công khai.
- Supervisor block.
- Rule active được inject.
- Rule pending không được inject.
- Rule rollback.
- Customer follow-up tạo tín hiệu chất lượng.
- Reflection tạo proposal.

### 13.3. Golden evaluation

Tạo fixture:

```text
data/golden/gmail/
data/golden/facebook/
```

Mỗi case nên có:

```json
{
  "input": "...",
  "expected_intent": "...",
  "must_contain": [],
  "must_not_contain": [],
  "expected_action": "queue_review",
  "max_turns": 2
}
```

### 13.4. Mục tiêu chất lượng MVP

| Chỉ số | Mục tiêu |
|---|---:|
| Gmail factual accuracy | >= 99% |
| Gmail draft acceptance không sửa | >= 60% |
| Gmail SMTP success | >= 98% |
| Facebook policy violation lọt qua | 0 |
| Facebook auto-send an toàn | >= 95% |
| Facebook complaint escalation đúng | >= 95% |
| Duplicate question trong thread | < 5% |
| Rule proposal có evidence hợp lệ | 100% |
| Cross-tenant data leakage | 0 |
| Facebook duplicate event side effects | 0 |
| Backup restore test pass | 100% |

---

## 14. Rollout an toàn

### Bước 1 - Shadow mode

- Agent tạo draft và evaluation nhưng không gửi tự động.
- Facebook đưa toàn bộ vào review queue.
- Gmail yêu cầu duyệt.
- Reflection chỉ tạo report, chưa tạo rule active.

### Bước 2 - Auto-send whitelist Facebook

Chỉ bật auto-send cho:

- Chào hỏi.
- Giờ mở cửa.
- Địa chỉ.
- Thông tin công khai ổn định.

### Bước 3 - Bật proposal learning

- Cho phép tạo proposal.
- Bắt buộc quản lý/chủ quán duyệt.
- Không auto-apply.

### Bước 4 - Mở rộng có kiểm soát

- Facebook có thể auto-send tư vấn món trong KB với confidence cao.
- Gmail có thể auto-approve template nội bộ rất ổn định sau khi có đủ metrics.
- Email có cam kết tài chính, pháp lý hoặc dữ liệu nhạy cảm vẫn cần duyệt.

### Feature flags

```env
NHIPQUAN_FB_AUTO_SEND=false
NHIPQUAN_FB_LEARNING_ENABLED=false
NHIPQUAN_MAIL_QUALITY_GATE=true
NHIPQUAN_MAIL_AUTO_APPROVE=false
NHIPQUAN_MAIL_REFLECTION_ENABLED=false
NHIPQUAN_RULE_AUTO_APPLY=false
NHIPQUAN_AI_CIRCUIT_BREAKER=true
NHIPQUAN_AI_RETENTION_DAYS=180
NHIPQUAN_AI_CANARY_ENABLED=true
```

---

## 15. Chỉ số vận hành và dashboard

### Gmail

- Tổng draft.
- Acceptance rate.
- Edit rate.
- Reject rate.
- Subject edit rate.
- Body edit rate.
- Context accuracy.
- SMTP success/failure.
- Average approval time.
- Tone Memory reuse rate.
- Số proposal pending/approved/rejected.

### Facebook

- Tổng message/comment.
- Auto-send rate.
- Queue rate.
- Escalation rate.
- Supervisor block rate.
- Manager edit rate.
- Customer follow-up rate.
- Resolution rate.
- First response time.
- Complaint SLA.
- False auto-send rate.
- Public comment incident count.
- Rule version đang active.

Dashboard cần hiển thị xu hướng theo ngày/tuần, không chỉ một con số hiện tại.

### 15.1. Circuit breaker và cảnh báo

Dashboard phải hiển thị theo từng `store_id` và channel:

- Circuit state: `closed`, `tripped`, `half_open`.
- Lý do trip, thời điểm trip và cửa sổ metric.
- Số auto actions, denominator và sample count.
- Reject/edit rate, false auto-send và hard safety violation.
- Model, prompt và rule version.
- Nút `Disable khẩn cấp` với xác nhận và audit.

Khi ngưỡng trip đạt, hệ thống phải tự chuyển traffic sang review/fallback và tạo alert.
Dashboard là nơi quan sát và thao tác khôi phục, không phải cơ chế duy nhất để phát hiện lỗi.

### 15.2. Ngưỡng circuit breaker

Circuit breaker chạy độc lập theo `store_id + channel + traffic_class`, với trạng thái:

```text
closed -> tripped -> half_open -> closed
```

Trong cửa sổ trượt 15 phút:

| Điều kiện | Hành động |
|---|---|
| Ít nhất 20 auto actions và `(rejected + materially_edited) / decided >= 25%` | Pause auto-send |
| Ít nhất 20 auto actions và `false_auto_send >= 2` | Pause ngay |
| Có 1 hard safety violation | Pause ngay |
| Ít nhất 10 lần gửi và send failure >= 30% | Pause channel |
| LLM/schema failure >= 5 lần trong 5 phút | Pause LLM path, chuyển fallback/review |

`false_auto_send` chỉ được tính từ sự kiện manager đánh dấu, không suy ra từ tín hiệu mơ hồ.
Sau khi trip, traffic mới chuyển sang review/fallback, tạo alert và lưu metric snapshot.
Chỉ người có quyền mới chuyển sang `half_open` sau tối thiểu 30 phút; half-open chạy 5 event
hoặc 10% traffic, tùy giá trị nhỏ hơn. Không có hard fail và score đạt threshold mới đóng breaker.
Disable thủ công toàn hệ thống hoặc riêng store/channel luôn có ưu tiên cao hơn auto-send.

### 15.3. Retention, xóa PII và backup

| Loại dữ liệu | Retention mặc định | Hết hạn |
|---|---:|---|
| Raw Facebook webhook | 7 ngày | Xóa vĩnh viễn |
| Nội dung hội thoại Facebook có PII | 90 ngày | Xóa body/PII, giữ aggregate đã ẩn danh |
| Email draft/body và bản sửa | 180 ngày | Xóa nội dung, giữ metadata/score tối thiểu |
| Generation/feedback/evaluation metadata | 365 ngày | Xóa hoặc anonymize |
| Audit approval/rollback và rule history | 730 ngày | Giữ metadata, xóa secret/body không cần thiết |
| Backup mã hóa | 35 ngày online | Rotation tự động |

PII gồm tên, email, số điện thoại, PSID mapping và nội dung khách gửi. Job xóa chạy theo
`store_id`, có dry-run, count, audit log và hỗ trợ legal hold có thời hạn. Không log raw body,
access token, App Password hoặc full recipient list. Có yêu cầu xóa dữ liệu khách/cửa hàng theo
quyền chủ quán; sau khi xóa nội dung chỉ giữ hash/ID, channel, `store_id`, timestamp, action và score.

SQLite/KV phải có snapshot nhất quán mỗi ngày, incremental WAL mỗi giờ, giữ 35 ngày online và
2 snapshot cuối tháng trong 12 tháng. Backup mã hóa, có checksum, schema version và coverage theo
`store_id`. Hàng tuần restore vào database tạm; mục tiêu RPO <= 1 giờ, RTO <= 4 giờ.

### 15.4. RACI và incident response

| Hoạt động | A - Accountable | R - Responsible | C - Consulted | I - Informed |
|---|---|---|---|---|
| Duyệt Facebook nhạy cảm | Chủ quán | Quản lý ca | AG Supervisor | Team |
| Duyệt Gmail draft | Quản lý/chủ quán | Người ra lệnh | AG-MAILWRITER | Người nhận |
| Review reflection hàng ngày | Quản lý vận hành | AI/ops engineer | Chủ quán | Team |
| Review report hàng tuần | Chủ quán | Quản lý vận hành | Product/engineering | Team |
| Approve rule/model release | Chủ quán | Engineering | Quản lý vận hành | Team |
| Disable auto-send khẩn cấp | On-call/chủ quán | Người phát hiện | Engineering | Quản lý |
| Backup/restore/retention | Engineering lead | Ops engineer | Security/data owner | Chủ quán |

Khi auto-send sai: (1) disable channel/store hoặc toàn hệ thống nếu chưa rõ phạm vi; (2) lưu
generation/event/store/model/prompt/rule IDs trong retention; (3) dừng canary/release liên quan;
(4) phân loại P0 an toàn/pháp lý/tiền, P1 khách hàng nghiêm trọng, P2 lỗi văn phong/vận hành;
(5) người thật đính chính P0/P1; (6) trong 24 giờ xác định nguyên nhân và phạm vi; (7) chỉ mở lại
sau regression test, owner approval và postmortem. Acknowledge P0 trong 15 phút, P1 trong 30 phút;
mọi disable, rollback và re-enable đều có actor, lý do và timestamp.

---

## 16. Tài liệu và runbook cần cập nhật

Cập nhật:

- `docs/FACEBOOK_CHATBOT_IMPLEMENTATION_GUIDE.md`
- `docs/FACEBOOK_CHATBOT_IMPLEMENTATION_GUIDE_VI.md`
- `docs/FACEBOOK_CHATBOT_SUMMARY.md`
- `docs/runbooks/gmail-smtp-connect.md`
- `packages/agents/src/ca_agents/ag_mailwriter/PHAM_VI.md`
- `docs/THIRD_PARTY.md` nếu thêm dependency.

Tạo mới:

```text
docs/runbooks/ai-learning-loop.md
docs/runbooks/gmail-reflection.md
docs/runbooks/facebook-reflection.md
docs/adr/ADR-015-ai-generation-feedback-learning.md
docs/runbooks/ai-incident-response.md
docs/runbooks/ai-backup-restore.md
docs/runbooks/ai-model-release.md
```

Runbook phải ghi rõ:

- Cách chạy reflection thủ công.
- Cách xem generation và feedback.
- Cách approve/reject/pause/rollback rule.
- Cách tắt auto-send.
- Cách xử lý SMTP lỗi.
- Cách xử lý Facebook webhook/Graph API lỗi.
- Cách che credential trong log.
- Cách khôi phục version rule trước.

---

## 17. Thứ tự ưu tiên thực thi

Nếu cần triển khai theo mức ưu tiên, thứ tự khuyến nghị là:

1. Ghi generation và feedback đầy đủ.
2. Hoàn thiện Gmail Quality Gate.
3. Nối active playbook rule vào Facebook prompt.
4. Xây Gmail Reflection.
5. Nâng cấp Facebook Reflection.
6. Thêm API/UI xem diff và proposal.
7. Thêm scheduler.
8. Mở rộng auto-send.

Không nên làm scheduler trước khi dữ liệu generation và feedback đủ tin cậy. Không nên auto-apply rule trước khi có approval, version và rollback.

---

## 18. Kết luận nghiệm thu tổng thể

Hai tính năng được xem là hoàn thiện khi đạt đủ các điều kiện:

- Facebook và Gmail đều sinh nội dung tự nhiên trong live mode và deterministic trong replay mode.
- Nội dung luôn dùng đúng dữ liệu xác thực.
- Gmail học được văn phong từ chỉnh sửa của quản lý.
- Facebook dùng được rule/playbook đã duyệt trong các lần trả lời sau.
- Mọi generation đều có audit, version và context snapshot.
- Mọi feedback đều được lưu thành event có thể truy vết.
- Quality Gate chặn nội dung sai hoặc nguy hiểm trước khi gửi.
- Reflection tạo được finding và proposal có evidence.
- Rule chỉ active sau khi người có quyền duyệt.
- Rule có thể pause và rollback.
- Có test golden cho các tình huống an toàn, nhạy cảm và lỗi context.
- Có dashboard và runbook đủ để vận hành.
- Có feature flag để tắt riêng auto-send và learning của từng channel.

Kết quả mong muốn là một vòng lặp có kiểm soát:

```text
AI tạo nội dung
  -> hệ thống kiểm tra
  -> con người quyết định
  -> hệ thống ghi nhận kết quả
  -> reflection tìm mẫu lặp
  -> con người duyệt bài học
  -> agent dùng bài học ở lần sau
```
