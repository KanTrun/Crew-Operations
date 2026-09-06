---
name: fbpage-concierge
description: "Kỹ năng trực fanpage, trả lời tin nhắn khách hàng (menu, giá cả, giờ mở cửa) và hỗ trợ đặt bàn trước."
disable-model-invocation: true
metadata:
  role: operating
  package: packages/agents
---

# Fanpage & Concierge Skill

Kỹ năng dùng để tự động hóa việc chăm sóc khách hàng qua kênh Facebook Fanpage, Zalo OA hoặc quầy Lễ tân (Concierge).

## 1. Kiểm tra nhanh (Smoke Check)

Chạy script tra cứu menu và bàn trống:

```bash
python skills/repositories/repo-skills/fbpage-concierge/scripts/lookup_menu_and_tables.py
```

## 2. Chính sách trả lời tin nhắn

Xem chi tiết tại [references/fanpage_faq_policy.md](references/fanpage_faq_policy.md):
- Giờ mở cửa: 07:00 - 22:30.
- Bảng giá chuẩn: không tự ý hứa hẹn giảm giá ngoài chính sách.

## 3. Quy trình thực thi cho Agent

1. Xác định nhu cầu khách hàng: Hỏi món / giá, hay Đặt bàn trước.
2. Chạy script `scripts/lookup_menu_and_tables.py`.
3. Soạn câu trả lời lịch sự, đầy đủ thông tin để gửi lại khách.
