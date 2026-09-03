---
title: "Phase 3: Đổi Ca Đủ ca_id & Đối Tác"
status: done
---

# Phase 3: Đổi Ca Đủ ca_id & Đối Tác

## Overview

- Bắt buộc kiểm tra `ca_id` và `doi_tac_nv_id` khi Quản lý duyệt yêu cầu đổi ca. Thiếu thông tin trả về 400 (`doi_ca_can_ca_id_va_doi_tac`).
- Xử lý nhân viên trùng tên: nếu phát hiện `doi_tac_khong_ro` mà quản lý chưa chỉ định rõ `doi_tac_nv_id` -> trả về 400 (`doi_tac_khong_ro_can_chon_nhan_vien`).
- Xác nhận hai chiều: Swap tạo ra ở trạng thái `cho_xac_nhan`. Đối tác xác nhận qua `/api/v1/doi-ca/{id}/xac-nhan` hoặc từ chối qua `/api/v1/doi-ca/{id}/tu-choi`.
- Hỗ trợ Quản lý áp đặt đổi ca: cờ `ap_dat=True` chuyển thẳng sang `dong_y` mà không cần chờ đối tác.

## Requirements

- [x] Chặn duyệt đổi ca thiếu mã ca hoặc đối tác.
- [x] Chặn duyệt khi đối tác trùng tên mà chưa chọn ID cụ thể.
- [x] Endpoint xác nhận và từ chối đổi ca.
- [x] Hỗ trợ cờ áp đặt đổi ca bởi Quản lý.

## Implementation Steps

1. Step 1
2. Step 2

## Todo

- [ ] Task A
- [ ] Task B

## Success Criteria

_Define done._
