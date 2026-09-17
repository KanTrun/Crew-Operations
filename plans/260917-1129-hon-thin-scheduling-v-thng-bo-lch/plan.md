---
title: "Hoàn thiện scheduling và thông báo lịch"
description: "Hoàn thiện luồng xếp lịch, chợ ca, thông báo deep-link và bàn giao an toàn lên main."
status: in_progress
priority: P1
effort: "2-3 ngày"
tags: [scheduling, notifications, open-shift, e2e]
created: 2026-09-17
---

# Hoàn thiện scheduling và thông báo lịch

## Overview

Hoàn thiện phần còn thiếu của scheduling mà không thay đổi các hợp đồng API đã có:
tách solver khỏi tầng HTTP, nối giao diện nhân viên/quản lý vào open-shift APIs, và chứng
minh thông báo lịch mở đúng tuần rồi được acknowledge. Công việc kết thúc bằng test,
review, đồng bộ hai plan tiền nhiệm, rebase với `origin/main`, commit đúng phạm vi và
push trực tiếp lên `main` theo yêu cầu.

## Constraints And Non-Goals

- Giữ tương thích các endpoint scheduling, lifecycle, notification và open-shift hiện có.
- Dùng persistence/atomic claim hiện có; không tạo cơ chế claim song song ở frontend.
- Không sửa luồng Facebook Page/chatbot trong đợt này.
- Không đưa thay đổi cục bộ `.github/workflows/ci.yml` vào commit scheduling.
- Không dùng lệnh Git phá huỷ; khi remote thay đổi phải fetch/rebase và giải quyết xung đột theo hành vi mới nhất.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Tầng application gọi solver qua module trung lập, không import tầng HTTP | P1 |
| 2 | Nhân viên nhận ca trống và quản lý xử lý khoảng trống bằng UI hiện hữu | P1 |
| 3 | E2E chứng minh thông báo mở đúng tuần và được acknowledge | P1 |
| 4 | Toàn bộ thay đổi được kiểm thử, review, đồng bộ plan và push lên `main` | P1 |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Phase 1: Tách solver adapter](./phase-01-start.md) | Pending |
| 2 | [Phase 2: UI open shift và approval](./phase-02-ui-open-shift-v-approval.md) | Pending |
| 3 | [Phase 3: E2E notification và regression](./phase-03-e2e-notification-v-regression.md) | Pending |
| 4 | [Phase 4: Review đồng bộ và phát hành](./phase-04-review-ng-b-v-pht-hnh.md) | Pending |

## File Inventory

- Backend: `apps/api/src/ca_api/services/scheduling_service.py`, `apps/api/src/ca_api/interfaces/http/main.py`, `apps/api/src/ca_api/interfaces/http/sprint45.py`, và module solver trung lập mới trong `apps/api/src/ca_api/services/`.
- Frontend: `apps/web/src/app/roster/page.tsx`, `apps/web/src/app/doi-ca/page.tsx` khi luồng nhân viên thuộc chợ đổi ca.
- Tests: unit/integration scheduling hiện có và `apps/web/e2e/lich-tuan.spec.ts`.
- Documentation: hai plan tiền nhiệm và plan này; không churn tài liệu evergreen nếu hợp đồng người dùng không đổi.

## Verification Matrix

| Surface | Verification |
|---------|--------------|
| Solver adapter | Focused Pytest cho scheduling/lifecycle/pin assignment |
| Open-shift UI | Frontend typecheck, build, focused Playwright/API assertions |
| Notification deep-link | Playwright kiểm URL `?tuan=YYYY-Www`, roster tuần đích và ack |
| Shared regression | Full backend Pytest suite, frontend build và relevant E2E |
| Delivery | Clean scoped diff, plan validation, rebase thành công, push verified |

## Risks And Rollback

- Rủi ro lớn nhất là circular import hoặc sai payload khi di chuyển solver; giảm thiểu bằng cách di chuyển nguyên hành vi và chạy test ngay sau edit đầu tiên.
- Claim cạnh tranh phải tiếp tục được quyết định ở backend; UI chỉ hiển thị kết quả server và refresh state.
- E2E phụ thuộc fixture tuần cụ thể; test phải tạo/intercept dữ liệu xác định thay vì dựa vào ngày máy chạy.
- Rollback bằng một commit revert cho thay đổi scheduling; dữ liệu hiện có không cần migration.

## Success Criteria

- [ ] Không còn application service hoặc primary HTTP router import `_run_solver` từ `sprint45.py`.
- [ ] Nhân viên có thể xem và claim ca trống đủ điều kiện; lỗi cạnh tranh/không đủ điều kiện hiển thị rõ.
- [ ] Quản lý có thể xem khoảng trống và thực hiện action hiện được API hỗ trợ mà không cần gọi API thủ công.
- [ ] Click notification mở đúng tuần, render lịch tuần đó và acknowledge notification.
- [ ] Backend tests, frontend typecheck/build và focused Playwright đều pass.
- [ ] Plan cũ được sync trạng thái, commit không chứa CI edit ngoài phạm vi, và `main` được push thành công.

<!-- slug: hon-thin-scheduling-v-thng-bo-lch -->