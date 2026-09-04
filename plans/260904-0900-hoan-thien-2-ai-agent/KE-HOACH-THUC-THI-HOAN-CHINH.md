# Kế Hoạch Thực Thi Hoàn Chỉnh AI Agent

> Phạm vi: đưa AG-FBPAGE và AG-MAILWRITER từ trạng thái tích hợp chức năng đến vận hành an toàn, kiểm chứng được.
>
> Tài liệu này là execution plan. Chi tiết contract, retention, RACI và ngưỡng rollout chuẩn xem `KE-HOACH-HOAN-THIEN-2-AI-AGENT.md` cùng thư mục.

## Mục tiêu nghiệm thu

Hoàn thành khi đồng thời đạt các điều kiện sau:

1. Không agent nào auto-send dữ liệu mặc định, placeholder hoặc context không xác thực.
2. Mỗi generation, feedback, evaluation và rule proposal truy vết được theo `store_id` và có idempotency.
3. Rule chỉ ảnh hưởng output sau khi chủ quán duyệt, kích hoạt và còn hiệu lực; pause/rollback có hiệu lực tức thì.
4. Gmail và Facebook đều có quality signal, reflection, proposal có evidence, dashboard và thao tác vận hành.
5. Tất cả kiểm thử chạy bằng Python 3.12+ trong replay mode; live mode chỉ bật qua feature flag.
6. Có scheduler, circuit breaker tự động, retention thực thi, backup/restore rehearsal và runbook incident.

## Nguyên tắc không thay đổi

- API/orchestrator lưu dữ liệu và quyết định policy; LLM chỉ sinh nội dung hoặc đề xuất.
- Thiếu facts xác thực, confidence thấp, safety flag hoặc breaker mở phải chuyển `queue_review`/fallback, không auto-send.
- Mọi query, cache key, rule, proposal, job và audit log phải phân vùng theo `store_id`.
- Không auto-apply rule, không tự mở lại breaker và không retry live LLM vô hạn.
- `CA_AGENT_MODE=replay` không cần network, token Facebook, Gmail App Password hay LLM key.

## Điều kiện khởi động

| Việc | Chủ sở hữu | Tiêu chí xong |
|---|---|---|
| Chuẩn hóa runtime dev/CI | Engineering | Python 3.12+ và `uv` hoặc Python 3.12 + pip; `python -m pytest` chạy được |
| Khoá baseline | QA | Lưu kết quả test hẹp hiện tại; không chấp nhận regression không giải thích |
| Khoá cờ production | Ops | `NHIPQUAN_FB_AUTO_SEND=false`, `NHIPQUAN_MAIL_AUTO_APPROVE=false`, `NHIPQUAN_RULE_AUTO_APPLY=false` |
| Chuẩn bị fixture golden | QA + vận hành | Có Gmail/Facebook positive, hard-negative, missing-context, PII, injection, complaint và duplicate webhook |

Không bắt đầu rollout live trước khi bảng trên hoàn thành. Hiện workstation local đang dùng Python 3.10 và thiếu `pytest`, vì vậy đây là blocker đầu tiên cần xử lý.

## Lộ trình theo PR

### PR 0 - Runtime và regression baseline

**Phạm vi**

- Cài/khai báo Python 3.12 và dependency test theo cách thống nhất cho Windows và CI.
- Thêm command test hẹp cho AI agents vào Makefile hoặc tài liệu runbook.
- Chạy và lưu baseline của agent, persistence, HTTP learning và UI lint.

**Nghiệm thu**

```text
CA_AGENT_MODE=replay python -m pytest \
  packages/agents/tests/test_ag_fbpage.py \
  packages/agents/tests/test_ag_fbpage_reflection.py \
  packages/agents/tests/test_ag_mailwriter.py \
  packages/agents/tests/test_ag_copilot.py \
  apps/api/tests/unit/test_ai_learning_persistence.py \
  apps/api/tests/unit/test_ai_learning_http.py \
  apps/api/tests/unit/test_ai_learning_facebook_reflection_http.py -q
```

Pass toàn bộ trước khi sang PR 1.

### PR 1 - Facebook fail-closed facts

**Vấn đề cần sửa**

`AG-FBPAGE` hiện có profile, menu, Wi-Fi và promotion mẫu bên trong agent. Khi orchestration không nạp public context thật, output có thể bị auto-send với dữ liệu giả.

**Phạm vi**

- Bỏ default facts khỏi đường auto-send; tách rõ display fallback cho review và public facts đã xác thực.
- Xác định facts bắt buộc theo intent: giờ/địa chỉ cần profile đã xác thực; menu/giá cần menu đã xác thực; khuyến mãi cần promotion active đã xác thực.
- Thiếu fact hoặc fact mâu thuẫn: `queue_to_inbox`, có reason machine-readable `missing_verified_context`.
- Không gửi Wi-Fi password trừ khi policy public context cho phép rõ ràng.
- Lưu source/version/hash của context vào generation audit.

**Tests bắt buộc**

- Thiếu profile/menu/promotion không auto-send.
- Context đầy đủ vẫn auto-send whitelist hợp lệ.
- Không còn `123 Đường Cà Phê`, hotline/menu/demo Wi-Fi trong auto-response.
- Live LLM không được làm tăng quyền quyết định policy.

**Cổng merge**: `test_ag_fbpage.py` mới và cũ pass; không thay đổi behavior booking/complaint luôn review.

### PR 2 - Hoàn chỉnh learning record và quality gate

**Phạm vi**

- Review toàn bộ đường Facebook/Gmail để generation được ghi trước delivery và feedback được ghi tại approve/edit/reject/send result/customer follow-up.
- Bổ sung evaluator Facebook nếu còn thiếu score context, policy, safety, naturalness và personalization.
- Chuẩn hóa `policy_action`, `agent_version`, `prompt_version`, `rule_version`, `rollout_bucket`, context hash và event state.
- Mở rộng golden fixtures cho missing fact, public comment, financial promise, PII leak, SMTP/Graph failure và webhook duplicate.

**Cổng merge**

- Dedupe không gọi classifier, LLM hoặc transport lần hai.
- Cross-tenant generation/evidence bị từ chối trước khi ghi.
- Quality gate block hard fail; review flag luôn vượt auto-send.
- Redaction không làm lộ email, phone, PSID mapping, token hay App Password.

### PR 3 - Rule lifecycle và learning loop hai kênh

**Phạm vi**

- Gmail/Facebook reflection dùng feedback thực tế, chỉ sinh proposal khi đủ evidence đồng nhất.
- API transition bắt buộc owner: `pending -> approved -> active -> paused -> rolled_back`; conflict chuyển `conflict_pending`.
- Nạp duy nhất active rule đúng `store_id`, channel, intent/audience scope, và rollout bucket ổn định.
- Rule/prompt/model version phải gắn vào generation kế tiếp.

**Cổng merge**

- Proposal pending/rejected không ảnh hưởng output.
- Active rule thay đổi output case tương ứng; pause/rollback trả output về baseline.
- Canary luôn ổn định với cùng `store_id + conversation_id/recipient_id`.
- Không có proposal trùng khi chạy reflection lặp lại.

### PR 4 - Dashboard hai kênh và thao tác con người

**Phạm vi**

- Mở rộng `/ai-learning` từ Gmail-only thành tab hoặc bộ lọc Gmail/Facebook.
- Facebook cần inbox/timeline: intent, confidence, policy, supervisor flag, draft gốc, bản sửa, SLA và feedback.
- Gmail cần xem draft gốc/bản cuối cạnh nhau, diff, quality flags, approval time và metrics theo ngày/tuần.
- Bổ sung UI reject, rollback và xác nhận trước disable/re-enable breaker.
- Thêm trạng thái circuit breaker theo store/channel/traffic class và lý do trip.

**Cổng merge**

- Manager chỉ xem đúng dữ liệu store mình; employee bị chặn.
- Owner mới được approve/activate/pause/rollback rule và vận hành breaker.
- UI gọi endpoint Facebook reflection được, không chỉ Gmail.
- Playwright smoke: login owner, lọc Gmail/Facebook, chạy reflection, thấy proposal, lifecycle rule và breaker state.

### PR 5 - Scheduler, retention và incident controls

**Phạm vi**

- Worker scheduler idempotent theo store/channel cho metrics hourly, reflection daily, quality report weekly, retention weekly, backup daily và restore rehearsal weekly.
- Triển khai retention từ dry-run sang execute mode có legal hold, audit count và anonymize body/PII theo policy.
- Circuit breaker tự động với `closed -> tripped -> half_open -> closed`; tripped phải ép traffic về review/fallback.
- Alert on-call/chủ quán khi trip, backup fail, job fail/retry exhausted hoặc safety violation.
- Backup encrypted root, checksum, rotation và restore test database tạm.

**Cổng merge**

- Chạy lặp job không tạo duplicate evaluation/proposal hoặc xóa dữ liệu sai store.
- Hard safety violation hoặc ngưỡng error làm trip breaker trong test; auto-send bị chặn ngay.
- Half-open chỉ mở theo quota và cần owner acknowledgement.
- Restore rehearsal kiểm checksum, schema và record count.

### PR 6 - Shadow, canary và release

**Pha 1: shadow**

- Facebook 100% review; Gmail 100% approval; reflection tạo report/proposal pending.
- Tối thiểu 20 event hợp lệ/channel/store hoặc 7 ngày, tùy điều kiện nào đến sau.

**Pha 2: Facebook whitelist**

- Chỉ chào hỏi, giờ mở cửa và địa chỉ với verified context.
- Không auto-send menu giá, booking, complaint, promotion động, public comment nhạy cảm hoặc bất kỳ case supervisor flag.

**Pha 3: controlled expansion**

- Mở beverage/menu chỉ sau golden pass và số liệu shadow đạt ngưỡng.
- Canary rule 10%, sau đó 50%, rồi 100%; mỗi bước cần owner approval và không có hard fail.

**Điều kiện promote**

- Facebook policy violation lọt qua: 0.
- Facebook complaint escalation đúng: >= 95%.
- Gmail factual accuracy: >= 99%; SMTP success: >= 98%.
- Rule evidence validity và cross-tenant isolation: 100%.
- Edit/reject rate không xấu hơn baseline quá 5 điểm phần trăm.

## Trình tự phụ thuộc

```text
PR 0 Runtime baseline
    -> PR 1 Facebook fail-closed facts
    -> PR 2 Audit + quality gates
    -> PR 3 Rule lifecycle + reflection
    -> PR 4 Dashboard two-channel
    -> PR 5 Scheduler + incident controls
    -> PR 6 Shadow/canary rollout
```

PR 4 có thể phát triển giao diện song song với PR 3, nhưng không merge thao tác lifecycle trước khi API PR 3 hoàn tất. PR 5 không được bắt đầu auto-schedule trước khi PR 2 đảm bảo dữ liệu audit đáng tin.

## Checklist release

- [ ] Python 3.12+ và suite replay xanh ở Windows/CI.
- [ ] Facebook không auto-send với missing/unverified facts.
- [ ] Golden set Gmail/Facebook đạt ngưỡng và có report baseline.
- [ ] Test tenant isolation, dedupe, redaction, rule rollback và breaker đều xanh.
- [ ] Dashboard Gmail + Facebook đã smoke bằng owner và manager.
- [ ] Scheduler idempotent, alert route, backup/restore rehearsal và retention execute mode đã kiểm chứng.
- [ ] Feature flags production ban đầu ở shadow/review mode.
- [ ] Owner duyệt checklist release, RACI/on-call và runbook incident.

## Runbook bắt buộc trước live

- `docs/runbooks/ai-learning-loop.md`: generation, feedback, reflection, approval và rollback.
- `docs/runbooks/ai-incident-response.md`: disable, triage P0/P1/P2, evidence retention và re-enable.
- `docs/runbooks/ai-backup-restore.md`: backup, checksum, restore rehearsal, RPO/RTO.
- `docs/runbooks/ai-model-release.md`: golden eval, model/prompt version, shadow/canary và rollback.

## Quyết định vận hành ban đầu

Giữ Facebook auto-send và Gmail auto-approve tắt cho đến hết Pha 1. `NHIPQUAN_RULE_AUTO_APPLY` luôn tắt; rule chỉ active sau approval rõ ràng của chủ quán. Đây là mức an toàn mặc định, không phải một cờ tạm để bỏ qua khi thiếu metrics.