# Handoff cho Claude: Gemini 3.8 Live Extended Thinking cho AI-COPILOT NHỊP QUÁN (v3)

> Ngày lập bản gốc: 2026-09-17  
> v2: kiểm chứng kỹ thuật qua web search.  
> v3: thu hẹp phạm vi theo quyết định của người dùng: text giữ nguyên hoàn toàn, chỉ triển khai voice bằng một model duy nhất.  
> Trạng thái: tài liệu kế hoạch, chưa yêu cầu chỉnh mã nguồn trong bước này.

## 0. Quyết định phạm vi

1. **Text Copilot chat không đổi.** Giữ nguyên thứ tự provider mặc định trong `router.py`: `groq -> gemini -> openrouter -> bai -> ollama`. Không tạo route ưu tiên riêng cho `task="text:copilot_chat"` và không đôn Gemini lên đầu.
2. **Voice chỉ dùng một model:** `gemini-3.8-live-extended-thinking`. Không dùng `gemini-3.8-live` và không xây logic chọn model theo độ phức tạp câu hỏi.
3. **Không fallback sang model voice khác.** Nếu model voice duy nhất lỗi, quota hoặc timeout, phải báo lỗi rõ ràng và gợi ý người dùng quay lại chat text.

Toàn bộ nội dung cũ về Phase 1 ưu tiên Gemini cho text và Phase 5 chọn model theo intent không còn áp dụng. Track còn lại là xây voice, một tính năng lớn qua Live API, không phải đổi model ID trong client text.

## 1. Yêu cầu gốc

Người dùng muốn áp dụng các model Gemini mới vào AI chat đứng đầu của NHỊP QUÁN, dựa trên thông tin Google giới thiệu:

- `gemini-3.8-live`: model voice realtime, tối ưu độ trễ, quy mô và chi phí.
- `gemini-3.8-live-extended-thinking`: model voice realtime có reasoning sâu, duy trì mạch hội thoại bằng tín hiệu âm thanh trong lúc suy luận.

Ý định sản phẩm có hai lớp khác nhau:

1. Nâng chất lượng/trải nghiệm AI-COPILOT chat hiện tại.
2. Về sau có thể bổ sung hội thoại bằng giọng nói Gemini Live.

Không được gộp hai lớp này thành một thay đổi model ID đơn giản. `gemini-3.8-live` và `gemini-3.8-live-extended-thinking` là model cho Live API audio-to-audio qua WebSocket; chúng không phải model text thông thường để ném vào endpoint `generateContent` hiện tại.

## 2. Kết luận kỹ thuật đã xác minh

Tài liệu Google Gemini API cập nhật 2026-09-15 liệt kê:

- Text/multimodal: `gemini-3.8-flash`.
- Live voice mặc định: `gemini-3.8-live`.
- Live voice reasoning sâu: `gemini-3.8-live-extended-thinking`.
- Live API dùng WebSocket có trạng thái.
- Input gồm audio PCM 16 kHz, text và ảnh.
- Output audio PCM 24 kHz.
- Google khuyến nghị ephemeral token khi client kết nối Live API trực tiếp.

Tài liệu tham khảo chính thức:

- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/live-api
- https://ai.google.dev/gemini-api/docs/live-api/thinking
- https://ai.google.dev/gemini-api/docs/live-api/tools
- https://ai.google.dev/gemini-api/docs/live-api/ephemeral-tokens

## 3. Hiện trạng repository

Repository là monorepo Python + Next.js:

- `apps/api`: FastAPI backend.
- `apps/web`: Next.js 15 PWA.
- `packages/agents`: LLM router và các AI agent.
- `packages/contracts`: Pydantic contracts, intent và role matrix.
- `packages/gates`, `packages/opsengine`, `packages/solver`: các lớp kiểm chứng/nghiệp vụ tất định.

Nguyên tắc kiến trúc phải giữ nguyên:

- Core điều phối và solver không phụ thuộc LLM.
- Agent chỉ phân tích, trích xuất, đọc dữ liệu hoặc tạo proposal.
- Model không được tự ghi/sửa/xóa database.
- Action nguy hiểm phải qua proposal, quyền, scope, stale check và phê duyệt.
- Khi LLM lỗi hoặc không chắc chắn thì fail-closed/fallback an toàn.
- `CA_AGENT_MODE=replay` phải không gọi mạng và tiếp tục chạy test deterministic.

## 4. Các file và luồng liên quan

### 4.1 LLM provider và router

File chính: `packages/agents/src/ca_agents/llm.py`

Hiện có:

- `complete(...)`: gọi provider live đầu tiên khả dụng.
- `complete_stream(...)`: stream qua một số provider OpenAI-compatible.
- `_gemini(...)`: gọi Gemini qua:

  `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`

- API key dùng header `x-goog-api-key`, không đưa vào URL.
- Có model cooldown và provider cooldown.
- Có xử lý fallback khi model không tồn tại, quota, timeout, 429 hoặc lỗi 5xx.

Danh sách Gemini hiện tại đã chứa:

```text
gemini-3.8-flash
gemini-3.7-flash
gemini-3.6-flash
gemini-3.5-flash
gemini-3.5-flash-lite
gemini-2.5-flash
```

File `packages/agents/src/ca_agents/router.py` hiện định tuyến live theo thứ tự:

```text
groq -> gemini -> openrouter -> bai -> ollama
```

Vision hiện có thứ tự ưu tiên Gemini trước.

### 4.2 AG-COPILOT

File chính: `packages/agents/src/ca_agents/ag_copilot/copilot_agent.py`

`_generate_conversational_reply(...)`:

- Chỉ gọi LLM khi `CA_AGENT_MODE=live`.
- Kiểm tra `provider_status()` trước.
- Gọi `complete(...)` với:

```text
task="text:copilot_chat"
json_mode=False
timeout_s=15.0
```

- Nếu LLM lỗi/không có provider thì dùng fallback hội thoại tất định.

`run_copilot(...)` vẫn là entrypoint chính để parse intent, gọi tool whitelist và tạo `CopilotResponse`. Không được biến voice/text model thành nơi tự thực hiện nghiệp vụ.

### 4.3 API Copilot

File chính: `apps/api/src/ca_api/interfaces/http/copilot.py`

Endpoint hiện có:

- `POST /api/v1/copilot/message`
- `POST /api/v1/copilot/message/stream`

Backend xác thực user từ session, sau đó tạo `verified_context` gồm:

- `store_id`
- `user_id`
- `user_role`
- `active_date`
- `channel`
- `recent_messages`
- `attachments`

Không được tin `store_id`, role hoặc user ID do client tự gửi.

Endpoint stream hiện chạy `run_copilot(...)` trước, gửi event `meta`, sau đó chia `reply_text` thành các event `delta`, rồi gửi `done`. Proposal được lưu/audit trước khi stream text.

### 4.4 Frontend Copilot

File chính: `apps/web/src/ui/copilot/useCopilotChat.ts`

Frontend:

- Gọi `/api/v1/copilot/message/stream`.
- Đọc SSE `meta`, `delta`, `done`.
- Hiển thị delta như streaming.
- Fallback về POST JSON nếu SSE không khả dụng.
- Lưu lịch sử theo mode `pane` hoặc `page` trong localStorage.

Không đổi contract frontend chỉ để đổi model provider. Nếu bổ sung voice, cần thêm một mode/transport riêng, không làm hỏng SSE text hiện tại.

### 4.5 Contract và quyền

File chính: `packages/contracts/src/ca_contracts/__init__.py`

`CopilotResponse` gồm:

- `reply_text`
- `intent`
- `confidence`
- `action_proposal`
- `direct_answer`
- `citations`
- `agent_mode`

`CopilotIntent` có nhiều intent đọc và mutating/proposal. Role matrix là nguồn sự thật duy nhất. Các request thay đổi dữ liệu phải giữ `ActionProposal` và trạng thái cần phê duyệt.

## 5. Phạm vi triển khai khuyến nghị

### Phase 1: Gemini 3.8 Flash làm model ưu tiên cho Copilot text

Mục tiêu:

- Với `task="text:copilot_chat"`, thử Gemini trước.
- Nếu thiếu key hoặc Gemini lỗi thì fallback provider hiện có.
- Giữ nguyên endpoint, contract, role check, tool registry, approval và audit.
- Không đưa Live model vào `_gemini(...)` hiện tại.

Thứ tự riêng cho Copilot text nên là:

```text
gemini -> groq -> openrouter -> bai -> ollama
```

Khuyến nghị định tuyến theo task, thay vì đảo thứ tự toàn bộ hệ thống, để giảm blast radius:

```text
text:copilot_chat -> gemini -> groq -> openrouter -> bai -> ollama
vision:*          -> giữ ưu tiên Gemini hiện có
task khác         -> giữ hành vi cũ trừ khi có yêu cầu riêng
```

Model cấu hình đề xuất:

```env
GEMINI_MODEL=gemini-3.8-flash
```

Không ghi key thật vào repo. Chỉ cập nhật `.env.example` nếu cần tài liệu hóa model mặc định.

### Phase 2: Kiểm thử và đo lường

Sau Phase 1 cần đo:

- Gemini success rate.
- Tỷ lệ fallback theo provider.
- HTTP 400/401/403/404/429/5xx.
- Time to first response và tổng latency.
- P95/P99 latency.
- Chất lượng tiếng Việt.
- Intent accuracy.
- Tỷ lệ proposal bị gate/supervisor chặn.
- Hành vi replay/CI.

Chỉ chuyển sang Phase 3 khi Phase 1 không có regression và fallback được chứng minh bằng test.

### Phase 3: Gemini text streaming thật, nếu cần

Hiện SSE frontend có thể giữ nguyên. Có hai lựa chọn:

1. Giữ `complete(...)`, backend chia kết quả hoàn chỉnh thành delta. Ít rủi ro nhưng không phải token streaming thật.
2. Bổ sung Gemini streaming thật rồi chuyển chunk sang SSE. Trải nghiệm tốt hơn nhưng cần xử lý lỗi giữa stream và bảo vệ metadata/proposal.

Metadata proposal phải được tạo sau `run_copilot(...)` và các kiểm tra liên quan. Không được để token/chunk model đi thẳng ra UI trước khi kiểm soát contract.

### Phase 4: Gemini Live voice

Đây là tính năng mới, không phải một chỉnh sửa nhỏ của provider text.

Model cấu hình dự kiến:

```env
GEMINI_LIVE_MODEL=gemini-3.8-live
GEMINI_LIVE_THINKING_MODEL=gemini-3.8-live-extended-thinking
```

Luồng đề xuất:

```text
Browser microphone
  -> WebSocket voice session
  -> Gemini Live API
  -> audio PCM + transcript + tool events
  -> Browser
```

Phải thiết kế thêm:

- Quyền microphone.
- Audio PCM input/output.
- WebSocket session có trạng thái.
- Reconnect, timeout, stop session.
- Transcript realtime.
- Barge-in/interruption.
- Trạng thái đang suy luận.
- Tool call qua whitelist.
- Session gắn với user/store/role đã xác thực.
- Audit và chính sách lưu transcript/audio.

MVP voice nên chỉ cho tài khoản nội bộ đã đăng nhập, ưu tiên hỏi đáp và tra cứu. Chưa mở action mutation bằng voice cho tới khi tool call, proposal và approval được kiểm thử đầy đủ.

### Phase 5: Extended Thinking có chọn lọc

Không dùng Extended Thinking cho mọi lượt voice. Đề xuất:

| Loại yêu cầu | Model |
|---|---|
| Chào hỏi, hỏi SOP, hỏi lịch cá nhân | `gemini-3.8-live` |
| Phân tích nhiều điều kiện/phức tạp | `gemini-3.8-live-extended-thinking` |
| Hành động thay đổi dữ liệu | model Live + whitelist + proposal + approval |
| Ý định không rõ | hỏi lại, không gọi tool |

Không tự chèn câu “Để tôi kiểm tra...” nếu chưa xác minh event/audio behavior của Live API. Có thể hiển thị trạng thái `Đang suy luận...` ở UI và chỉ phát câu đệm khi timeout/không có audio được xử lý rõ ràng.

## 6. Ràng buộc an toàn bắt buộc

Claude phải giữ tất cả điều kiện sau:

1. Không commit API key, token hoặc transcript nhạy cảm.
2. Không đưa `GEMINI_API_KEY` vào browser.
3. Không tin identity/store/role từ payload client.
4. Không cho model gọi database trực tiếp.
5. Tool call phải nằm trong whitelist.
6. Mutation phải tạo proposal và yêu cầu phê duyệt như hiện tại.
7. Không bypass `VF-SCOPE`, `VF-STALE`, `VF-CONF`, supervisor hoặc audit.
8. Replay mode không gọi mạng.
9. Provider/model lỗi phải fallback hoặc fail-closed.
10. Không dùng `gemini-3.8-live*` với endpoint `generateContent` hiện tại.
11. Không đổi contract `CopilotResponse` nếu chưa có migration và test tương ứng.
12. Không sửa solver/deterministic core để phục vụ model mới.

## 7. Kế hoạch file-level cho Phase 1

Đây là phạm vi chỉnh sửa nhỏ nhất được chấp nhận:

### Có thể cần chỉnh

- `packages/agents/src/ca_agents/router.py`: thêm route ưu tiên theo task hoặc cơ chế tương đương.
- `packages/agents/src/ca_agents/llm.py`: chỉ chỉnh logic lựa chọn provider/model nếu cần; giữ nguyên `_gemini` text API, cooldown và fallback.
- `apps/api/.env.example`: ghi model text mặc định `gemini-3.8-flash` nếu cần.
- `packages/agents/tests/test_router.py`: test route `text:copilot_chat` ưu tiên Gemini.
- Một test LLM mới hoặc test hiện có: test fallback khi Gemini lỗi/thiếu key.
- `docs` hoặc `plans`: cập nhật hướng dẫn cấu hình nếu implementation tạo behavior mới.

### Không được chỉnh trong Phase 1

- Không tạo WebSocket voice.
- Không thêm microphone UI.
- Không đổi `CopilotResponse`.
- Không đổi role matrix.
- Không đổi tool registry.
- Không đổi approval flow.
- Không đổi solver.
- Không đổi Facebook chatbot chỉ vì cùng có chữ chat.

## 8. Test và validation bắt buộc

Test unit cần có:

- Replay mode luôn trả replay và không gọi provider.
- `text:copilot_chat` chọn Gemini đầu tiên khi live.
- Gemini thiếu key thì thử provider kế tiếp.
- Gemini lỗi 429/5xx/404 thì cooldown/fallback đúng.
- Gemini response rỗng hoặc lỗi JSON không làm crash.
- Model list vẫn chứa fallback model hợp lệ.
- Vision route không bị regression.
- Copilot tạo proposal như trước.
- Role không đủ quyền vẫn bị block.

Test API cần giữ xanh:

- `/api/v1/copilot/message`.
- `/api/v1/copilot/message/stream`.
- Persist/audit proposal.
- SSE event `meta -> delta* -> done`.

Lệnh validation theo repo:

```text
CA_AGENT_MODE=replay python -m pytest -q packages/agents/tests/test_router.py packages/agents/tests/test_llm_bai.py packages/agents/tests/test_llm_cooldown.py
CA_AGENT_MODE=replay python -m pytest -q apps/api/tests/unit/test_copilot_api.py
ruff check apps/api/src packages scripts
cd apps/web && npm run typecheck
```

Trên Windows, nếu shell không hiểu cú pháp `VAR=value command`, dùng biến môi trường tương đương của CMD/PowerShell hoặc chạy task có sẵn trong workspace. Không dùng key thật để chạy test unit.

## 9. Tiêu chí nghiệm thu Phase 1

Phase 1 chỉ được coi là hoàn tất khi:

- Copilot text ưu tiên `gemini-3.8-flash` trong live mode.
- Không có Gemini key thì hệ thống vẫn fallback đúng.
- Gemini lỗi quota/model/network thì hệ thống không bị treo và có fallback.
- Replay/CI vẫn deterministic và không gọi mạng.
- SSE/frontend không đổi contract và không regression.
- Các proposal nghiệp vụ vẫn cần phê duyệt.
- Không có secret trong diff/log/test artifact.
- Test liên quan pass.
- Có ghi rõ model đang dùng và cách rollback.

Rollback tối thiểu:

```env
GEMINI_MODEL=gemini-2.5-flash
```

và tắt route ưu tiên Copilot nếu implementation có feature flag.

## 10. Cách Claude nên thực hiện

Trước khi sửa:

1. Đọc file này và xác nhận đang làm Phase nào.
2. Kiểm tra git diff/worktree để không ghi đè thay đổi người dùng.
3. Đọc router, LLM client, AG-COPILOT, API endpoint, frontend SSE và test lân cận.
4. Nêu một hypothesis ngắn và một test có thể bác bỏ hypothesis đó.
5. Nếu chỉ làm Phase 1, không mở rộng sang Live voice.

Trong khi sửa:

1. Thực hiện thay đổi nhỏ nhất.
2. Sau edit đầu tiên chạy ngay test hẹp liên quan.
3. Nếu test fail, sửa trong cùng slice và chạy lại trước khi mở rộng.
4. Không dùng API key thật trong command hoặc test output.

Sau khi sửa:

1. Chạy test provider/router.
2. Chạy test Copilot API/SSE.
3. Chạy ruff/typecheck phù hợp.
4. Kiểm tra `git diff --check`.
5. Báo cáo rõ file đã đổi, test đã chạy, phần nào chưa làm và cách rollback.

## 11. Quyết định sản phẩm cần hỏi lại trước Phase 4

Nếu muốn triển khai Gemini Live voice, cần chốt riêng:

- Voice chỉ dành cho nhân viên/quản lý hay cả khách Facebook?
- Có lưu transcript không? Lưu bao lâu?
- Browser kết nối backend WebSocket hay dùng ephemeral token?
- Có cho voice gọi tool nghiệp vụ ngay không?
- Extended Thinking tự chọn theo intent hay người dùng bật?
- Có cần chuyển đổi liền mạch giữa text và voice trong cùng conversation không?
- Ngưỡng latency chấp nhận được là bao nhiêu?
- Có ngân sách/quota riêng cho Live API không?

Cho tới khi các câu hỏi trên được chốt, phạm vi an toàn là Phase 1: Gemini 3.8 Flash làm provider ưu tiên cho Copilot text; chưa triển khai Gemini Live audio.
