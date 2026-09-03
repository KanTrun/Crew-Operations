---
title: "Phase 4: Wire Inbox Vào Solver & Lifecycle"
status: done
---

# Phase 4: Wire Inbox Vào Solver & Lifecycle

## Overview

- `_run_solver()` nạp toàn bộ ràng buộc từ `inbox_rang_buoc` đã được duyệt:
  - `xin_nghi`: nạp vào `inp.nghi_phep` dạng `(nv_id, thu)`.
  - `cap_nhat_tkb` / `bao_tre`: nạp vào `inp.tkb[nv_id]` dạng `(thu, start, end)`.
- Ràng buộc gắn ngữ cảnh tuần: chỉ nạp item khớp `tuan_iso` của đợt giải, bỏ qua các ràng buộc của tuần khác.
- Khử trùng lặp: không tạo ràng buộc dư thừa khi quản lý duyệt nhiều lần.
- Phân tích xung đột Infeasible: khi solver trả về `INFEASIBLE`, tính toán chi tiết ca nào thiếu người tối thiểu do những ràng buộc nào và trả về `danh_sach_xung_dot`.
- Mở lại lịch `da_dong` -> `nhap`: chỉ vai trò `chu_quan`, bắt buộc truyền `ly_do`, ghi audit log `lifecycle_reopen`.

## Requirements

- [x] Solver đọc ràng buộc đã duyệt và không xếp phạm quy.
- [x] Ràng buộc tuần khác không lọt vào solver tuần này.
- [x] Phân tích xung đột trả về `danh_sach_xung_dot` khi Infeasible.
- [x] Quy trình mở lại lịch từ `da_dong` có kiểm tra vai trò và lý do.

