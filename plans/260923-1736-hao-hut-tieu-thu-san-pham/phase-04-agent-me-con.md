---
phase: 4
title: "Agent mẹ–con"
status: completed
priority: P1
effort: "0.5 ngày"
dependencies: [3]
---

# Phase 4: Agent mẹ–con

## Overview

Nối AG-COPILOT (mẹ) với AG-WASTE (con) qua đúng kênh có sẵn: `configure_data_sources()`
+ `ANALYZE_LOSS`. Mẹ điều phối và diễn giải; con tính. Không phá cổng kiến trúc.

## Requirements

- Functional: intent mới `ANALYZE_LOSS` trả lời được "hao hụt tuần này do đâu, nguyên liệu nào".
- Functional: mẹ truyền dữ liệu thô vào con, con trả số, mẹ diễn giải thành câu tiếng Việt.
- Non-functional: `tool_registry.py` **không** import `ca_agents.ag_waste`, `ca_api`,
  `ca_playbook`, `ca_gates` — dữ liệu vào bằng inject.
- Non-functional: không có dữ liệu ⇒ trả lời trung thực, không bịa số.
- Non-functional: mọi câu trả lời kèm `explanation` nói rõ nguồn.

## Architecture

Giữ nguyên mẫu đang dùng cho `ANALYZE_WASTE`: hàm con được inject vào tool registry
dưới một tên trong `_SOURCES`, mẹ gọi qua `_src(...)`.

```text
main.py (API layer)
  configure_data_sources(..., loss_engine=ca_agents.ag_waste.so_hao_hut, ...)
        │
        ▼
ag_copilot/tool_registry.py    tool_loss_summary(intent=ANALYZE_LOSS)
        │  _src("loss_engine") → hàm thuần của con
        │  _kv_get("kiem_ke" / "waste_notes") → dữ liệu thật
        ▼
ToolExecutionResult(data={dong, tong, nguyen_nhan_hang_dau}, summary, explanation)
```

Luồng hội thoại: người dùng hỏi → `intent_parser` nhận `ANALYZE_LOSS` → mẹ gọi
`tool_loss_summary` → mẹ trả lời kèm số và nguồn. Mẹ **không** tự tính.

## Related Code Files

- Modify: `packages/agents/src/ca_agents/ag_copilot/intent_parser.py`
- Modify: `packages/agents/src/ca_agents/ag_copilot/tool_registry.py`
- Modify: `packages/agents/src/ca_agents/ag_copilot/system_prompt.md`
- Modify: `packages/agents/src/ca_agents/ag_copilot/PHAM_VI.md`
- Modify: `packages/contracts/src/ca_contracts/__init__.py` (`CopilotIntent.ANALYZE_LOSS`)
- Modify: `packages/contracts/schema/ActionProposal.json` (sinh lại)
- Modify: `packages/agents/src/ca_agents/ag_copilot/profile.py` nếu có (kiểm trước)
- Modify: `apps/api/src/ca_api/interfaces/http/main.py` (inject nguồn mới)
- Modify: `apps/api/src/ca_api/interfaces/http/copilot.py` (deep-link intent)
- Create: `packages/agents/tests/test_ag_copilot_loss.py`

## Implementation Steps

1. Thêm `ANALYZE_LOSS` vào `CopilotIntent`; chạy `make contracts`.
2. Thêm `ANALYZE_LOSS` vào `intent_parser` với các cụm từ thật ("hao hụt", "thất thoát",
   "lệch kiểm kê", "tiêu hao nguyên liệu").
3. Viết `tool_loss_summary` theo mẫu `tool_get_waste_summary`: đọc nguồn qua `_src`,
   rỗng thì trả `co_du_lieu: False` + câu trung thực.
4. Đăng ký `WHITELISTED_INTENTS["ANALYZE_LOSS"]`.
5. Inject `loss_engine` trong `main.configure_data_sources`.
6. Cập nhật `system_prompt.md` bảng tool; cập nhật `PHAM_VI.md`.
7. Test: intent parse đúng; chưa cấu hình nguồn ⇒ báo trung thực; có dữ liệu ⇒ có số.

## Success Criteria

- [x] `pytest packages/agents apps/api/tests -q` xanh.
- [x] Cổng `test_architecture.py` xanh (không import chéo).
- [x] Hỏi "hao hụt tuần này do đâu" qua API trả `intent=ANALYZE_LOSS`.
- [x] Khi KV rỗng, tool trả `co_du_lieu: False` — test khẳng định điều này.
- [x] `explanation` luôn nêu nguồn (`kiem_ke`, `menu_mon.bom`, `waste_notes`).

## Risk Assessment

Rủi ro: `ANALYZE_LOSS` và `ANALYZE_WASTE` dễ khớp nhầm cụm từ, làm intent cũ đổi
hành vi. **Tín hiệu:** test `test_ag_copilot.py:41` ("Báo cáo hao hụt sữa hôm nay")
đổi kết quả. **Phản ứng:** đặt `ANALYZE_LOSS` khớp **sau** các cụm hẹp hơn trong
`intent_parser`, và giữ test cũ làm chốt canh; nếu test cũ đổi thì sửa thứ tự khớp,
không sửa test.

