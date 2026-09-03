---
title: "Nối logic lịch inbox TKB kênh tin"
description: "Duyệt tin nhắn nhân viên trong /inbox thực sự tác động tới Solver CP-SAT và Lịch làm việc, có xử lý đầy đủ các trường hợp biên."
status: completed
priority: P1
effort: "large"
tags: [inbox, solver, tkb, lifecycle, edge-cases]
created: 2026-08-27
completed: 2026-09-03
---

# Nối logic lịch inbox TKB kênh tin

## Overview

Kế hoạch này giải quyết triệt để vấn đề: Khi Quản lý bấm "Duyệt" tin nhắn nhân viên trong `/inbox`, quyết định đó thực sự có hiệu lực trên Solver và Lịch làm việc (`phan_cong`), thay vì chỉ lưu nhãn mà không tác động tới thuật toán xếp lịch. Đã tích hợp đầy đủ 11 quy tắc biên (edge cases).

## Goals

| # | Goal | Priority | Status |
|---|------|----------|--------|
| 1 | Rút trích thông tin có cấu trúc (thứ, giờ, tuần, ca, đối tác) từ tin nhắn tự nhiên | P1 | Completed |
| 2 | Chặn tin rác (/help, chào) và không ghi đè fixture khi đã có tin kênh thật | P1 | Completed |
| 3 | Quy trình đổi ca chặt chẽ (đủ ca_id, đối tác, xác nhận 2 chiều hoặc QL áp đặt) | P1 | Completed |
| 4 | Nạp ràng buộc đã duyệt khớp tuần vào CP-SAT solver & phân tích xung đột Infeasible | P1 | Completed |
| 5 | Mở lại lịch đã đóng (da_dong -> nhap) bắt buộc có lý do và ghi audit log | P1 | Completed |
| 6 | Giao diện /inbox trung thực, có modal giải quyết đổi ca và cảnh báo xác minh | P1 | Completed |
| 7 | Bộ kiểm thử 11 test cases bao phủ toàn bộ các kịch bản biên | P1 | Completed |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Phase 1: Start & Extract Cấu Trúc](./phase-01-start.md) | Completed |
| 2 | [Phase 2: Lọc Tin & Tách Fixture](./phase-02-loc-tin-va-tach-fixture.md) | Completed |
| 3 | [Phase 3: Đổi Ca Đủ ca_id & Đối Tác](./phase-03-doi-ca-du-ca-id-doi-tac.md) | Completed |
| 4 | [Phase 4: Wire Inbox Vào Solver & Lifecycle](./phase-04-wire-inbox-vao-solver-lifecycle.md) | Completed |
| 5 | [Phase 5: UI Trung Thực & CTA Tuần](./phase-05-ui-trung-thuc-cta-tuan.md) | Completed |
| 6 | [Phase 6: Bộ Kiểm Thử 11 Test Cases](./phase-06-docker-github-ci-bao-ve.md) | Completed |

## Success Criteria

- [x] Tin nhắn xin nghỉ/đổi ca/TKB tự động trích xuất `thu`, `tuan_id`, `start-end`, `ca_id`, `doi_tac`.
- [x] Không nạp ràng buộc tuần khác vào solver của tuần hiện tại.
- [x] Đổi ca yêu cầu đủ `ca_id` và đối tác; hỗ trợ đối tác trùng tên (`doi_tac_khong_ro`).
- [x] Duyệt xin nghỉ/TKB nạp vào `inp.nghi_phep` và `inp.tkb`; solver tuyệt đối không xếp phạm quy.
- [x] Phân tích xung đột rõ ràng khi solver trả về `INFEASIBLE`.
- [x] Mở lại lịch `da_dong` -> `nhap` bắt buộc vai trò `chu_quan`, có `ly_do` và audit log.
- [x] 11/11 automated tests pass trong CI/test suite.

<!-- slug: noi-logic-lich-inbox-tkb-kenh-tin -->