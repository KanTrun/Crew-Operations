---
title: "Brainstorm — UI/UX AgentKit pipeline for NHỊP QUÁN"
created: 2026-08-21
status: accepted
---

# Brainstorm — UI/UX cực xuất sắc qua AgentKit

## Outcome

Mọi cook chạm `apps/web` hoặc surface demo buộc chạy pipeline UI/UX AgentKit (Pro Max → Frontend Design → Frontend Development), với `docs/design-guidelines.md` là hợp đồng thẩm mỹ; product PWA tin cậy (không landing AI-slop).

## Constraints

- Register **Product** cho app quản lý/NV; Brand chỉ landing demo sân khấu
- Dials product: variance **3** · motion **2** · density **6** (PWA một tay, 44×44 touch)
- Hồ sơ: mobile-first phiếu, lưới lịch quản lý, cẩm nang — không dashboard tím Inter
- Phase-01 không ship UI đầy đủ; chỉ seed guidelines + docs T0

## Non-goals

- Thay Stitch/Figma bằng một tool duy nhất nếu không cần mockup
- Redesign hồ sơ nghiệp vụ vì “đẹp”
- Fake dữ liệu quán / chữ ký để đóng phase-01

## Acceptance

- [ ] `plan.md` có section **UI/UX AgentKit pipeline** + lệnh copy-paste
- [ ] Phase D (S1–S5) ghi bắt buộc Pro Max + Frontend Design trước JSX
- [ ] `docs/design-guidelines.md` tồn tại sau cook phase-01
- [ ] Phase-01 cook xong phần kỹ thuật; blocker người liệt kê rõ

## Recommendation

**Pipeline bắt buộc:** `/ak:ui-ux-pro-max` → `/ak:frontend-design` → `/ak:frontend-development` (+ `/ak:web-testing`). Optional `/ak:stitch` chỉ khi cần mockup trước code.

## Unresolved

1. Quán chính/dự bị (chặn việc 1–3 phase-01)
2. Handles GitHub A/C/D
