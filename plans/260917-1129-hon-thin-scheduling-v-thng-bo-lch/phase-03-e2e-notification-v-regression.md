---
title: "Phase 3: E2E notification và regression"
status: done
---

# Phase 3: E2E notification và regression

## Overview

Khóa hành vi notification bằng E2E xác định: nhận thông báo, điều hướng đúng tuần,
render roster tuần đích và acknowledge thành công; đồng thời bảo vệ open-shift flow mới.

## Requirements

- [ ] Test không phụ thuộc tuần hiện tại hoặc dữ liệu môi trường ngẫu nhiên.
- [ ] URL sau click chứa chính xác `tuan=YYYY-Www` từ notification.
- [ ] Ack được chứng minh bằng request hoặc state server/UI, không chỉ bằng biến mất trực quan mơ hồ.
- [ ] Existing 21-slot roster assertion tiếp tục pass.

## Implementation Steps

1. Dùng fixture/interception pattern sẵn có để cung cấp notification và dữ liệu tuần đích xác định.
2. Mở roster, xác nhận notification, click, kiểm URL và nội dung tuần đích.
3. Kiểm ack endpoint/state và bổ sung open-shift happy/error path cần thiết.
4. Chạy focused Playwright spec; sau đó backend notification tests và frontend build.

## Todo

- [ ] Thêm notification receipt assertion.
- [ ] Thêm exact-week navigation assertion.
- [ ] Thêm acknowledgement assertion.
- [ ] Thêm regression coverage cho open-shift action.
- [ ] Chạy focused E2E và ghi lại kết quả.

## Success Criteria

Focused E2E pass ổn định và thất bại rõ ràng nếu deep-link sai tuần, roster không đổi tuần,
ack không gửi, hoặc open-shift action không cập nhật state.
