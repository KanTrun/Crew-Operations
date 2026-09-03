---
title: "Phase 6: Bộ Kiểm Thử 11 Test Cases"
status: done
---

# Phase 6: Bộ Kiểm Thử 11 Test Cases

## Overview

Xây dựng bộ kiểm thử tự động toàn diện `apps/api/tests/unit/test_inbox_tkb_solver.py` bao phủ đầy đủ 11 kịch bản:
1. `test_inbound_xin_nghi_classification_and_extraction`: Phân loại & trích xuất thứ/tuần.
2. `test_duyet_xin_nghi_wires_into_solver_nghi_phep`: Duyệt nghỉ nạp `inp.nghi_phep` và solver không xếp ngày đó.
3. `test_duyet_cap_nhat_tkb_wires_into_solver_tkb`: Duyệt TKB bận nạp `inp.tkb` và solver không xếp ca trùng giờ.
4. `test_duyet_doi_ca_requires_ca_id_and_doi_tac`: Thiếu ca/đối tác trả về 400; có đủ tạo swap `cho_xac_nhan`.
5. `test_lifecycle_da_dong_to_nhap_with_audit`: Mở lại lịch yêu cầu vai trò `chu_quan`, có `ly_do` và audit log.
6. `test_solver_ignores_constraints_from_other_weeks`: Ràng buộc tuần khác không nạp vào solver tuần này.
7. `test_low_confidence_marked_can_xac_minh`: Tin nhắn mơ hồ được gắn `do_tin_cay < 0.7` và `can_xac_minh=True`.
8. `test_deduplicate_identical_inbox_constraints`: Tránh trùng lặp khi duyệt nhiều lần cùng một yêu cầu.
9. `test_ambiguous_partner_name_requires_explicit_id`: Trùng tên đối tác yêu cầu chỉ định ID cụ thể.
10. `test_infeasible_solver_returns_specific_conflicts`: Trả về danh sách xung đột chi tiết khi solver Infeasible.
11. `test_swap_rejected_by_partner_not_applied_to_solver`: Đối tác từ chối swap qua `/tu-choi`.

## Requirements

- [x] 11/11 tests pass trong môi trường pytest.
- [x] Ruff lint sạch 100%.
- [x] TypeScript typecheck & Next.js production build pass 100%.
