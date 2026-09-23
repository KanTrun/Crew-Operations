## Vì sao

<!-- Lý do thay đổi, không chỉ mô tả diff -->

## Cái gì

-

## Checklist người viết

- [ ] Test cho hành vi mới (đỏ nếu xoá mã mới)
- [ ] Không phá 5 quy tắc kiến trúc §11.2
- [ ] Không số/chuỗi trần / `Any` mới trong `packages/*` và `domain/`
- [ ] Chạm contracts → đã chạy `make contracts`
- [ ] Thêm thư viện → đã ghi `docs/THIRD_PARTY.md`
- [ ] Chạm agent → bump phiên bản prompt + `make eval`
- [ ] Chạm orchestration/lõi → test tất định còn xanh
- [ ] Nhánh đúng vùng tiền tố (A/B/C/D) · sống ≤ 3 ngày

## Checklist AI / Jev (khi chạm sensors, fb_policy, moderation)

- [ ] Jev là cảm biến, **không** quyết định luồng/agent (ADR-002)
- [ ] `leo_thang = regex OR jev` — chỉ tăng, không gỡ leo thang (đơn điệu)
- [ ] Jev tắt/lỗi → fail-closed về phía **con người** (không im lặng auto)
- [ ] Đã ẩn danh hóa (tên/SĐT) trước khi gửi Jev (kế hoạch §6)
- [ ] Có test: Jev lỗi → queue; Jev tắt → giữ hành vi cũ; regex vẫn thắng
- [ ] Kill-switch `jev_enabled` qua API hoạt động (không cần deploy)

## Người duyệt

Dừng ở lỗi `[chặn]` đầu tiên. Xem `docs/github-operating-model.md`.
