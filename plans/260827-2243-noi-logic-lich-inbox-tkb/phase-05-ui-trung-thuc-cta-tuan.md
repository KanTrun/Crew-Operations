---
title: "Phase 5: UI Trung Thực & CTA Tuần"
status: done
---

# Phase 5: UI Trung Thực & CTA Tuần

## Overview

- Nâng cấp giao diện `/inbox`:
  - Hiển thị badge `Cần xác minh` (màu đỏ/cảnh báo) khi `can_xac_minh=True` hoặc độ tin cậy `< 0.7`.
  - Hiển thị badge `Trùng tên đối tác` khi `doi_tac_khong_ro=True`.
  - Hiển thị chi tiết trích xuất: Tuần (`tuan_id`), Khung giờ (`start–end`), Ca (`ca_id`), Đối tác (`doi_tac`).
  - Hộp thoại (Modal) chọn Ca (`ShiftSelect`) & Người nhận (`PersonSelect`) khi Quản lý duyệt đổi ca thiếu dữ liệu hoặc trùng tên, kèm checkbox "Áp đặt bởi Quản lý".

## Requirements

- [x] Hiển thị nhãn/badge cảnh báo xác minh và trùng tên rõ ràng.
- [x] Modal giải quyết đổi ca tiện dụng, không bắt Quản lý gõ tay ID.
- [x] Hỗ trợ áp đặt đổi ca trực tiếp trên UI.
