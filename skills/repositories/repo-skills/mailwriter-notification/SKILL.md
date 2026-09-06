---
name: mailwriter-notification
description: "Kỹ năng soạn thảo email điều hành chuyên nghiệp gửi nhà cung cấp nguyên liệu hoặc thông báo nội bộ cho nhân viên."
disable-model-invocation: true
metadata:
  role: operating
  package: packages/agents
---

# Mailwriter & Notification Skill

Kỹ năng dùng để tự động soạn thảo bản nháp email điều hành gửi đối tác (đặt hàng, đề nghị báo giá) hoặc gửi thông báo lịch trực cho toàn thể nhân sự.

## 1. Kiểm tra nhanh (Smoke Check)

Chạy script định dạng email:

```bash
python skills/repositories/repo-skills/mailwriter-notification/scripts/format_ops_email.py
```

## 2. Tiêu chuẩn email

Xem chi tiết tại [references/email_templates_guide.md](references/email_templates_guide.md):
- Đặt hàng: tiêu đề rõ ràng kèm danh mục nguyên liệu.
- Nội bộ: đính kèm liên kết PWA và hướng dẫn hạn chót phản hồi.

## 3. Quy trình thực thi cho Agent

1. Xác định đối tượng nhận email: Nhà cung cấp hay Đội ngũ nhân viên.
2. Thu thập danh mục mặt hàng hoặc nội dung thông báo.
3. Chạy script `scripts/format_ops_email.py`.
4. AG-COPILOT xuất bản nháp email (Draft ActionProposal) kèm nút "Duyệt & Gửi" cho Quản lý.
