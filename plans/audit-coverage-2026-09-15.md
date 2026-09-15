# Audit Coverage Inventory

## Bảng Audit Coverage (Trước khi sửa)

| Module | Method | Endpoint/Function | User Action | Current Audit | Audit Action | Actor | Entity | Status | File to Modify |
|---|---|---|---|---|---|---|---|---|---|
| Schedule | POST | `/api/v1/lich/lifecycle` | Chuyển trạng thái lịch | `lifecycle`, `lifecycle_reopen` | `schedule.lifecycle` | manager | schedule | COVERED | `sprint45.py` |
| Shift Swap | POST | `/api/v1/inbox/rang-buoc/{id}` | Duyệt/Từ chối đổi ca | `inbox` | `shift_swap.approve` / `shift_swap.reject` | manager | shift_swap | COVERED | `sprint45.py` |
| Shift Swap | POST | `/api/v1/inbox/rang-buoc/{id}/smart-approve` | Smart approve đổi ca | None | `shift_swap.smart_approve` | manager | shift_swap | COVERED | `sprint45.py` |
| Shift Swap | POST | `/api/v1/cho-doi-ca` | Yêu cầu đổi ca | `swap` | `shift_swap.request` | user | shift_swap | COVERED | `sprint45.py` |
| Shift Swap | POST | `/api/v1/cho-doi-ca/{id}/dong-y` | Xác nhận đổi ca | `swap_dong_y` | `shift_swap.confirm` | user | shift_swap | COVERED | `sprint45.py` |
| Shift Swap | POST | `/api/v1/cho-doi-ca/{id}/tu-choi` | Từ chối đổi ca | `swap_tu_choi` | `shift_swap.reject` | user | shift_swap | COVERED | `sprint45.py` |
| User | POST | `/api/v1/nguoi/{username}/nang-vai` | Nâng vai | `nang_vai` | `role.promote` | chu_quan | user | COVERED | `pos.py` |
| User | POST | `/api/v1/nguoi/{username}/ha-vai` | Hạ vai | `ha_vai` | `role.demote` | chu_quan | user | COVERED | `pos.py` |
| User | POST | `/api/v1/nguoi/{username}/deactivate` | Vô hiệu hóa tài khoản | `user_deactivate` | `user.deactivate` | chu_quan | user | COVERED | `pos.py` |
| Meeting | POST | `duyet_cuoc_hop` | Duyệt biên bản họp | `duyet_cuoc_hop` | `meeting.approve` | manager | meeting | COVERED | `meeting.py` |
| Meeting | DELETE | `/api/v1/meetings/{id}` | Xóa biên bản | `xoa_cuoc_hop` | `meeting.delete` | manager | meeting | COVERED | `meeting.py` |
| Meeting | POST | `/api/v1/meetings/{id}/rollback` | Hủy áp dụng biên bản | `rollback_cuoc_hop` | `meeting.rollback` | manager | meeting | COVERED | `meeting.py` |
| Auth | Function | `login` | Login thành công | None | `user.login` | user | session | COVERED | `persist.py` |
| Auth | Function | `login` | Login thất bại | None | `user.login_failed` | user | session | COVERED | `persist.py` |
| Audit API | GET | `/api/v1/audit` | Xem audit | N/A | N/A | manager | audit | COVERED | `sprint45.py` |

## Tổng kết (Sau khi thực thi)
- **Tổng số chức năng mutation được phát hiện**: 15
- **COVERED**: 15 (Đã tích hợp đầy đủ payload chuẩn).
- **PARTIAL**: 0
- **MISSING**: 0
- **NOT_REQUIRED**: N/A
- **Các chức năng không thể audit vì chưa có implementation**: Không có
- **Các file đã sửa**: `sprint45.py`, `pos.py`, `meeting.py`, `persist.py`, `session.ts`, `vet/page.tsx`.
- **Các test đã chạy**: Chạy toàn bộ pytest suite `apps/api/tests/unit`.
