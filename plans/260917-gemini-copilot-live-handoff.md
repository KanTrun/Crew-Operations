# Handoff cho Claude: Gemini 3.8 Live Extended Thinking cho AI-COPILOT NHỊP QUÁN (v3)

> Ngày lập bản gốc: 2026-09-17  
> v2: kiểm chứng kỹ thuật qua web search.  
> v3: thu hẹp theo quyết định của người dùng: text giữ nguyên hoàn toàn, chỉ triển khai voice bằng một model duy nhất.
> Trạng thái: tài liệu kế hoạch, chưa yêu cầu chỉnh mã nguồn trong bước này.

## 0. Quyết định phạm vi

1. **Text Copilot chat không đổi.** Giữ nguyên thứ tự provider trong `router.py`: `groq -> gemini -> openrouter -> bai -> ollama`. Không tạo route ưu tiên riêng cho `task="text:copilot_chat"` và không đôn Gemini lên đầu.
2. **Voice chỉ dùng một model:** `gemini-3.8-live-extended-thinking`. Không dùng `gemini-3.8-live` và không xây logic chọn model theo độ phức tạp câu hỏi.
3. **Không fallback sang model voice khác.** Khi model voice duy nhất lỗi, quota hoặc timeout, báo lỗi rõ ràng và gợi ý quay lại chat text.

Toàn bộ nội dung cũ về ưu tiên Gemini cho text và chọn model theo intent không còn áp dụng. Track duy nhất là xây voice qua Live API; đây là tính năng lớn, không phải đổi model ID trong client text.

## 1. Yêu cầu gốc đã thu hẹp

Bổ sung hội thoại bằng giọng nói vào AI-COPILOT bằng đúng model `gemini-3.8-live-extended-thinking`, có reasoning sâu và duy trì mạch hội thoại bằng tín hiệu âm thanh trong khi xử lý nền.

Phần text hiện tại không nằm trong phạm vi thay đổi lần này.

## 2. Kỹ thuật đã xác minh

Theo tài liệu Google Gemini API được kiểm chứng ngày 2026-09-17:

- `gemini-3.8-live-extended-thinking` là model Live voice có reasoning sâu.
- Model có thể xử lý reasoning nền và tool call bất đồng bộ trong khi vẫn duy trì audio hội thoại.
- Câu đệm như “Để tôi kiểm tra...” là hành vi do model cung cấp; không tự giả lập câu đệm trong frontend.
- Dùng `interaction_status` để biểu diễn trạng thái xử lý nếu event này được API trả về; không tự suy đoán trạng thái từ timeout tùy ý.
- Live API dùng WebSocket có trạng thái.
- Input: audio PCM 16-bit, 16 kHz, little-endian; text; ảnh JPEG tối đa 1 FPS.
- Output: audio PCM 16-bit, 24 kHz.
- Có hai cách triển khai: server-to-server và client-to-server.
- MVP NHỊP QUÁN chọn **server-to-server** để backend giữ auth, role, store scope, whitelist và audit.
- Nếu sau này chọn client-to-server, frontend chỉ được dùng ephemeral token, tuyệt đối không dùng API key thật.

Nguồn tham khảo chính thức:

- https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live-extended-thinking
- https://ai.google.dev/gemini-api/docs/live-api
- https://ai.google.dev/gemini-api/docs/live-api/thinking
- https://ai.google.dev/gemini-api/docs/live-api/tools
- https://ai.google.dev/gemini-api/docs/live-api/ephemeral-tokens
- https://ai.google.dev/gemini-api/docs/deprecations

## 3. Hiện trạng repository

Repository là monorepo Python + Next.js:

- `apps/api`: FastAPI backend.
- `apps/web`: Next.js 15 PWA.
- `packages/agents`: LLM router và AI agents.
- `packages/contracts`: Pydantic contracts, intent và role matrix.
- `packages/gates`, `packages/opsengine`, `packages/solver`: lớp kiểm chứng/nghiệp vụ tất định.

Nguyên tắc phải giữ nguyên:

- Core điều phối và solver không phụ thuộc LLM.
- Agent chỉ phân tích, trích xuất, đọc dữ liệu hoặc tạo proposal.
- Model không được tự ghi/sửa/xóa database, kể cả qua voice.
- Action nguy hiểm phải qua proposal, quyền, scope, stale check và phê duyệt.
- LLM lỗi hoặc không chắc chắn thì fail-closed.
- `CA_AGENT_MODE=replay` không gọi mạng và phải có test double/mock cho voice.

## 4. Các file và luồng liên quan

### 4.1 Text hiện có, phải giữ nguyên

Các file text chỉ đọc để tham chiếu pattern, không đổi behavior trong task này:

- `packages/agents/src/ca_agents/llm.py`
- `packages/agents/src/ca_agents/router.py`
- `packages/agents/src/ca_agents/ag_copilot/copilot_agent.py`
- `apps/api/src/ca_api/interfaces/http/copilot.py`
- `apps/web/src/ui/copilot/useCopilotChat.ts`
- `packages/contracts/src/ca_contracts/__init__.py`

Hiện text dùng `generateContent`, provider chain `groq -> gemini -> openrouter -> bai -> ollama`, API Copilot JSON/SSE và contract `CopilotResponse`. Không dùng model Live với endpoint text `generateContent`.

### 4.2 Thành phần voice dự kiến

Tên file chỉ là gợi ý; Claude phải kiểm tra convention thật trước khi chọn:

- Service mới trong `packages/agents`, ví dụ `ca_agents/ag_copilot/voice_session.py`, phụ trách mở/đóng và forward WebSocket tới Gemini Live API. Tách khỏi `llm.py`.
- WebSocket endpoint mới trong `apps/api`, ví dụ `apps/api/src/ca_api/interfaces/ws/copilot_voice.py`, làm proxy server-to-server.
- Hook frontend mới, ví dụ `apps/web/src/ui/copilot/useCopilotVoice.ts`. Không gộp vào `useCopilotChat.ts`.
- Contract voice riêng nếu cần; không đổi `CopilotResponse` của text chỉ vì thêm voice.

Backend phải xác thực session như endpoint text, tạo `verified_context` từ user server-side và không tin identity/store/role trong message client.

## 5. Kế hoạch triển khai một track Voice

### Bước 0: quyết định sản phẩm, blocker trước mọi code

Phải chốt các câu hỏi sau; Claude không được tự đoán:

- Voice chỉ cho nhân viên/quản lý đã đăng nhập hay mở cho khách Facebook? Khuyến nghị MVP: chỉ nội bộ đã đăng nhập.
- Có lưu transcript không, lưu bao lâu? Có lưu audio thô không?
- Dùng server-to-server hay client-to-server + ephemeral token? Khuyến nghị MVP: server-to-server.
- MVP chỉ hỏi đáp/tra cứu hay cho gọi tool nghiệp vụ? Khuyến nghị MVP: chỉ hỏi đáp/tra cứu; mutation để phase sau.
- Ngưỡng latency chấp nhận được là bao nhiêu?
- Có quota/ngân sách riêng cho Live API không?
- Voice là phiên độc lập hay nối tiếp lịch sử text?

### Bước 1: thiết kế session

Sau khi Bước 0 được chốt:

- Xác định lúc mở/đóng session, timeout, reconnect và giới hạn phiên.
- Xử lý barge-in ở client và server, gồm dừng audio đang phát và báo interruption cho Live API.
- Theo dõi `interaction_status` để hiển thị trạng thái xử lý.
- Quy định transcript/audio retention và redact dữ liệu nhạy cảm.
- Xác định cách audit event, lỗi và tool call.

### Bước 2: implementation MVP

- Capture microphone và chuyển thành PCM 16-bit 16 kHz.
- Backend WebSocket xác thực session rồi proxy hai chiều với Live API.
- Nhận PCM 16-bit 24 kHz và phát ở browser.
- UI có trạng thái đang nghe, đang xử lý, đang nói, lỗi và dừng phiên.
- Chỉ dùng model cố định:

```env
GEMINI_LIVE_MODEL=gemini-3.8-live-extended-thinking
```

Không thêm `GEMINI_LIVE_FALLBACK_MODEL`, không thêm `gemini-3.8-live`, không route theo độ phức tạp.

MVP chỉ hỏi đáp/tra cứu. Nếu voice nhận yêu cầu mutation, từ chối an toàn hoặc chuyển thành hướng dẫn dùng text; không tự thực thi.

### Bước 3: tool call và approval, chỉ sau khi MVP voice ổn định

Nếu sản phẩm sau này bật tool call:

- Voice tool call phải đi qua cùng whitelist và pipeline `run_copilot(...)` như text.
- Identity, role và `store_id` lấy từ backend session.
- Read intent có thể trả dữ liệu theo quyền.
- Mutation chỉ tạo `ActionProposal`, không thực thi trực tiếp.
- Phải qua `VF-SCOPE`, `VF-STALE`, `VF-CONF`, supervisor và audit.
- Không tạo đường tắt riêng vì input là audio.

## 6. Ràng buộc an toàn bắt buộc

1. Không commit API key, token, audio hoặc transcript nhạy cảm.
2. Không đưa `GEMINI_API_KEY` vào browser; nếu đổi hướng client-to-server thì dùng ephemeral token.
3. Không tin identity/store/role từ payload client.
4. Không cho model gọi database trực tiếp.
5. Tool call phải nằm trong whitelist.
6. Mutation phải tạo proposal và chờ phê duyệt.
7. Không bypass `VF-SCOPE`, `VF-STALE`, `VF-CONF`, supervisor hoặc audit.
8. Replay mode không gọi mạng; voice phải có mock/double.
9. Khi model voice lỗi/quota/timeout: fail-closed, báo lỗi rõ và gợi ý chat text. Không thử model voice khác.
10. Không dùng model Live với endpoint `generateContent`.
11. Không đổi contract text `CopilotResponse` nếu không có lý do độc lập và migration/test.
12. Không sửa solver hoặc deterministic core để phục vụ voice.
13. Không tự ý thêm lựa chọn giữa `gemini-3.8-live` và extended-thinking.
14. Không tự ý đổi routing/model cho `task="text:copilot_chat"`.

## 7. Test bắt buộc cho voice

Test unit/integration mới:

- Replay mode không gọi mạng thật và dùng mock Live API.
- Chỉ tạo session với model `gemini-3.8-live-extended-thinking`.
- Session lấy `store_id`, `user_id`, `user_role` từ backend verified context.
- Payload client cố đổi identity/store/role không có hiệu lực.
- WebSocket đóng đúng khi client stop, timeout hoặc upstream lỗi.
- Lỗi/quota/timeout của Live API trả lỗi rõ, không làm sập session khác.
- Audio input/output được forward đúng định dạng đã chốt.
- `interaction_status` được ánh xạ đúng sang trạng thái UI nếu upstream gửi event.
- Không tự phát câu đệm giả khi model chưa trả audio/event tương ứng.
- Nếu tool call được bật, tool đi đúng whitelist và audit.
- Mutation nếu được bật vẫn tạo proposal, không execute trực tiếp.
- Role không đủ quyền bị block như text.

Regression test text:

- Router `text:copilot_chat` vẫn giữ provider đầu tiên là Groq.
- Chain mặc định vẫn là `groq -> gemini -> openrouter -> bai -> ollama`.
- `/api/v1/copilot/message` và `/api/v1/copilot/message/stream` không đổi.
- Text contract, approval, audit và replay không regression.

Lệnh validation cần điều chỉnh theo cấu trúc test thực tế:

```text
CA_AGENT_MODE=replay python -m pytest -q packages/agents/tests/test_router.py
CA_AGENT_MODE=replay python -m pytest -q apps/api/tests/unit/test_copilot_api.py
CA_AGENT_MODE=replay python -m pytest -q packages/agents/tests/
ruff check apps/api/src packages scripts
cd apps/web && npm run typecheck
```

Trên Windows dùng cú pháp biến môi trường tương ứng của CMD/PowerShell hoặc task có sẵn. Không dùng API key thật hay ephemeral token thật trong unit test/CI.

## 8. Tiêu chí nghiệm thu MVP voice

- Voice chỉ dùng đúng `gemini-3.8-live-extended-thinking`.
- Text không đổi, chain provider mặc định được test khóa lại.
- MVP chỉ dành cho user nội bộ đã đăng nhập.
- MVP chỉ hỏi đáp/tra cứu; mutation voice bị chặn hoặc chuyển sang text.
- Server-to-server giữ auth, role, store scope và audit ở backend.
- Live API lỗi thì fail-closed rõ ràng, không fallback model voice.
- Replay/CI deterministic và không gọi mạng.
- Không có secret, audio hoặc transcript nhạy cảm trong diff/log/test artifact.
- Có feature flag để tắt toàn bộ voice mà không ảnh hưởng text.
- Có rollback rõ: tắt feature flag, đóng endpoint voice, giữ text hoạt động.

## 9. Claude phải thực hiện như thế nào

Trước khi sửa:

1. Xác nhận Bước 0 đã được người dùng chốt. Nếu chưa, dừng và hỏi.
2. Xác nhận có quyền truy cập repo thật. Nếu không, chỉ thiết kế/tài liệu.
3. Kiểm tra worktree và không ghi đè thay đổi có sẵn.
4. Đọc pattern auth/audit/whitelist trong `copilot.py`, `copilot_agent.py` và module WebSocket hiện có nếu có.
5. Nêu một hypothesis ngắn và một test có thể bác bỏ trước khi viết code lớn.
6. Giữ nguyên toàn bộ text path và không mở rộng scope sang model khác.

Trong khi sửa:

1. Thay đổi nhỏ từng slice: contract/config, service, endpoint, frontend, test.
2. Sau edit đầu tiên chạy ngay test hẹp liên quan.
3. Không dùng key/token thật trong command, log hoặc fixture.
4. Không đánh dấu MVP hoàn tất nếu tool call/approval chưa được kiểm chứng.

Sau khi sửa:

1. Chạy test voice với mock.
2. Chạy regression test router và Copilot API/SSE.
3. Chạy ruff, typecheck và `git diff --check`.
4. Kiểm tra không có secret/runtime artifact trong diff.
5. Báo cáo file đã đổi, test đã chạy, phần chưa làm và cách rollback.

## 10. Điều kiện mở rộng sau MVP

Chỉ xem xét tool call qua voice sau khi MVP voice ổn định. Khi đó phải có quyết định riêng về:

- Có lưu transcript và retention bao lâu.
- Có lưu audio thô hay không.
- Có cho mutation bằng voice hay chỉ tạo proposal.
- Có nối voice với lịch sử text hay không.
- Cách audit audio event/tool event.
- Ngưỡng latency và quota.

Không được mở rộng sang `gemini-3.8-live` hoặc thêm model voice fallback nếu người dùng chưa thay đổi quyết định phạm vi ở mục 0.
