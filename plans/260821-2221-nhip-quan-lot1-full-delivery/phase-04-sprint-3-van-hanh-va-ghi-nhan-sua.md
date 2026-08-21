---
phase: 4
title: "Sprint 3 — Vận hành và ghi nhận sửa"
status: pending
priority: P1
effort: "18 person-days"
dependencies: [3]
---

# Phase 4: Sprint 3 — Tầng vận hành & ghi nhận lần sửa

## Overview

**Mục tiêu:** phiếu chạy trọn trên điện thoại; hệ thống bắt đầu ghi mọi lần người sửa (bước 1 vòng đời luật).

**Chiếu được:** NV cầm phone chạy mở quán, chụp minh chứng, để việc treo → hiện trên máy quản lý.

## Requirements

- Functional: opsengine (template/phieu/buoc/viec_treo/escalate); orc state machine + parallel dispatch + idempotency; AG-MSG 6 intents; messaging ports (Telegram/Zalo/console); staff mobile UI
- Non-functional: ghi nhận sửa **phải** sống từ S3 (cần ≥3 mẫu trước S5)

## Architecture

ADR-006 (YAML templates), ADR-007 (gates deterministic). Orchestration = writer duy nhất. Playbook chỉ có bảng `so_lan_sua` ở phase này.

## Related Code Files

- Create: `packages/opsengine/**`, `apps/api/.../orchestration/{state_machine,dispatcher,idempotency}`, `ag_msg/`, messaging adapters, `run-form` + staff mobile features
- Modify: playbook `so_lan_sua` store
- Delete: —

## Implementation Steps

| Who | Work | Days |
|-----|------|------|
| A | Opsengine đầy đủ; ghim ô re-solve; bảng ghi nhận sửa | 4,5 |
| B | Orc phần 1; agent approval inbox API; injectable clock + jobs | 4,5 |
| C | AG-MSG 2-tier; 3 message backends; Excel import p1 | 4,5 |
| D | Phiếu mobile 1 tay; lịch của tôi / nhả / nhận | 4,5 |

1. Chạy phiếu **trên điện thoại thật** (không emulator-only)
2. Kiểm idempotency: 2 lần cùng khoá → 1 ghi
3. Ma trận nhầm lẫn AG-MSG trên 6 ý định
4. Xác nhận bảng ghi nhận đã có cặp trước/sau thật

## AgentKit commands

```text
/ak:cook
/ak:frontend-development
/ak:databases
/ak:ui-ux-pro-max "one-hand run-form + staff mobile schedule"
/ak:frontend-design   # dials 3/2/6 — design-guidelines.md
/ak:test
/ak:web-testing
```

## Todo

- [ ] Phiếu ~20 bước xong trên phone thật
- [ ] Ảnh minh chứng + timing signals
- [ ] Orc 8 tasks song song + idempotency test
- [ ] AG-MSG confusion matrix ghi số
- [ ] Bảng ghi nhận có dữ liệu sửa thật

## Success Criteria

- [ ] Cổng ra sprint 3 — 5 điều kiện §14.4
- [ ] Đường dữ liệu cho S5 Cẩm nang đã chảy

## Risk Assessment

| Risk | Signal | Response |
|------|--------|----------|
| Quên ghi nhận sửa | DB trống cuối S3 | **Hard stop** — không mở S5 playbook logic |
| Zalo OA không free | ToS/pricing xấu | Chỉ Telegram + console (đã thiết kế 3 backends) |
