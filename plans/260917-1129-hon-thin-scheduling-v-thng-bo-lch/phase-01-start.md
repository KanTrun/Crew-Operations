---
title: "Phase 1: Tách solver adapter"
status: done
---

# Phase 1: Tách solver adapter

## Overview

Loại dependency ngược từ application service và primary router sang module HTTP legacy,
trong khi giữ nguyên kết quả solver, lỗi và payload công khai.

## Requirements

- [ ] Solver callable nằm trong module trung lập thuộc `ca_api.services` hoặc ownership tương đương.
- [ ] `scheduling_service.py`, `main.py` và `sprint45.py` dùng cùng callable đó.
- [ ] Không đổi schema request/response hoặc lifecycle semantics.

## Implementation Steps

1. Đồng bộ `main` với `origin/main`, bảo toàn `.github/workflows/ci.yml`, rồi đọc lại caller sau rebase.
2. Di chuyển nguyên logic `_run_solver` sang module trung lập với tên public nội bộ rõ nghĩa.
3. Đổi ba caller sang module mới và giữ wrapper tương thích trong `sprint45.py` chỉ nếu test/call site thực sự cần.
4. Chạy focused scheduling tests ngay sau edit đầu tiên; sửa cùng slice nếu import hoặc payload lệch.

## Todo

- [ ] Ghi nhận baseline focused tests sau khi rebase.
- [ ] Tạo adapter/service solver trung lập.
- [ ] Xoá dependency application-to-HTTP.
- [ ] Chạy focused tests và import/type diagnostics.

## Success Criteria

Các caller production đi qua module trung lập, không có circular import, và focused tests
cho solve/lifecycle/pin assignment pass không cần nới assertion.
