# Bước 4 — Thông báo cập nhật lịch tuần

## Outcome

Khi lịch tuần được quản lý công bố hoặc cập nhật sau công bố, nhân viên nhận
được thông báo vận hành bền vững trên hệ thống và từ bot chat. Mỗi thông báo
dẫn đúng tới `/lich-tuan?tuan=YYYY-Www`, nơi lịch tuần tương ứng được hiển thị.

## Constraints

- Giữ nguyên lifecycle hiện có: `nhap -> dang_giai -> cho_duyet -> da_duyet -> da_cong_bo`.
- Không để nhân viên xem lịch khi tuần chưa ở `da_cong_bo` hoặc `da_dong`.
- Không dùng dữ liệu mẫu trong production; fixture chỉ được bật bằng cờ hiện hữu.
- Giữ tương thích API lịch, chat và giao diện roster hiện tại.
- Không trộn sửa CI không liên quan vào logic scheduling.

## Non-goals

- Không thay thế CP-SAT hoặc thiết kế lại workflow duyệt lịch.
- Không tạo trang lịch mới; `/lich-tuan` tiếp tục dùng roster hiện hữu.
- Không gửi email/SMS/push ngoài trình duyệt và chat nội bộ.

## Acceptance criteria

1. Chuyển một tuần sang `da_cong_bo` tạo một bản ghi thông báo có `tuan_iso`
   và URL exact-week.
2. Nhân viên có thể tải danh sách thông báo chưa đọc, mở link lịch, và đánh dấu
   đã xem; quản lý có thể nhận cùng thông báo vận hành.
3. Chat scheduler tạo `ops_card` có metadata và link exact-week, không tự sinh
   Hoa/Tuấn/Minh/Lan khi không có availability thật.
4. `/lich-tuan?tuan=...` chọn đúng tuần từ query string và vẫn giữ các kiểm tra
   quyền/lifecycle hiện tại.
5. Có test backend cho publish, deep link, ack và fixture guard; có E2E hoặc
   test frontend phù hợp cho deep link.
6. Test CI đang hỏng `test_multiturn_reservation_does_not_re_ask_time` được sửa
   ở nguyên nhân encoding/dữ liệu replay và toàn bộ kiểm tra liên quan pass.

## Implementation

1. Thêm bảng/hàm persistence thông báo vận hành, với dedupe theo store, tuần,
   loại sự kiện và phiên bản cập nhật; thêm HTTP list/ack.
2. Gọi persistence từ transition `da_cong_bo` và các cập nhật lịch làm thay đổi
   nội dung sau công bố; phát realtime event kèm tuần.
3. Bổ sung link tuần vào chat scheduler và loại bỏ fallback dữ liệu mẫu trong
   production.
4. Hiển thị notification center gọn trong shell/roster và đồng bộ tuần qua
   query string.
5. Thêm test, chạy focused checks rồi mở rộng build/typecheck/E2E.
6. Sửa lỗi CI Facebook replay độc lập, chạy lại test chính, review diff và push
   `main` nếu branch protection cho phép.

## Validation and rollback

- Backend: các test lifecycle, persistence, scheduler, inbox/solver.
- Frontend: typecheck/build và E2E lịch tuần.
- Rollback: revert commit feature; bảng mới là additive và không ảnh hưởng dữ
  liệu lịch cũ.

## Implementation status

- Done: exact-week notification persistence and deduplication, lifecycle publish
   hook, list/ack API, scheduler deep-link metadata, and `/lich-tuan?tuan=...`
   query handling.
- Remaining: dedicated frontend/E2E coverage for notification deep links and
   the pre-existing Facebook replay failure outside scheduling scope.