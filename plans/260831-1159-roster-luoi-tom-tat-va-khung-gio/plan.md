---
title: "Roster lưới tóm tắt + khung giờ"
description: "Approach A — lưới tuần gọn, zebra, lọc, giờ từ API, cấu hình template 3 khung (sáng/chiều/tối)."
status: in-progress
priority: P1
effort: "2-3d"
tags: [roster, ops-ui, web, api]
created: 2026-08-31
blockedBy: []
blocks: []
brainstorm: plans/260831-0107-nang-cap-mat-van-hanh-ops-ui/reports/brainstorm-ops-ui-redesign.md
related: plans/260831-0107-nang-cap-mat-van-hanh-ops-ui
---

# Roster lưới tóm tắt + khung giờ (Approach A)

## Overview

Nâng cấp `/roster` theo hướng **A** đã chọn: giữ ma trận 7×3, ô tóm tắt, progressive disclosure qua modal ngày, hiển thị `bat_dau`–`ket_thuc` thật, API cấu hình template khung (ví dụ mở cửa 06:00).

## Hợp đồng

| Trường | Nội dung |
|--------|----------|
| **Outcome** | Quản lý đọc lịch tuần nhanh, lọc được, chỉnh giờ 3 khung; nhân viên vẫn xem “Lịch của tôi” |
| **Constraints** | Design v3 ops (T0, density 6); không đổi solver/21 ca; `present.ts` cho nhãn |
| **Non-goals** | Timeline day-first (B); hover expand (C); thêm slot ca thứ 4 |
| **Acceptance** | Giờ từ API; ô ≤2 dòng; zebra hàng; lọc NV/khung/vị trí; PATCH khung-gio + test; web build + docker |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Lưới tóm tắt & lọc](./phase-01-luoi-tom-tat-va-loc.md) | Pending |
| 2 | [API & UI cấu hình khung giờ](./phase-02-api-khung-gio.md) | Pending |
| 3 | [Ship: test, docker, git](./phase-03-ship.md) | Pending |

## Success Criteria

- [ ] Bảng dùng `.nq-roster-table`, zebra theo hàng khung, ô compact
- [ ] `ListToolbar` + spotlight cột ngày; sửa nhân sự chỉ trong modal
- [ ] `GET /api/v1/lich-tuan` trả `khung_gio`; `PATCH` cập nhật template
- [ ] `npm run build` + `docker compose build web` pass; git push

<!-- slug: roster-luoi-tom-tat-va-khung-gio -->
