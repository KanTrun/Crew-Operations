---
name: customer-memory-voc
description: "Kỹ năng phân tích cảm xúc phản hồi khách hàng (VOC) và tự động ghi nhớ sở thích cá nhân hóa của khách quen."
disable-model-invocation: true
metadata:
  role: operating
  package: packages/agents
---

# Customer Memory & VOC Skill

Kỹ năng dùng để phân tích đánh giá của khách hàng từ Google Reviews, Fanpage, Zalo OA và lưu vết thói quen uống để chăm sóc khách hàng cá nhân hóa.

## 1. Kiểm tra nhanh (Smoke Check)

Chạy script phân tích phản hồi:

```bash
python skills/repositories/repo-skills/customer-memory-voc/scripts/analyze_customer_feedback.py
```

## 2. Tiêu chuẩn phân loại

Xem chi tiết tại [references/sentiment_categories.md](references/sentiment_categories.md):
- Phân loại 3 mức: `POSITIVE`, `NEUTRAL`, `NEGATIVE`.
- Báo động khẩn cấp: Khi xuất hiện nhiều từ khóa tiêu cực liên tiếp về thái độ hoặc vệ sinh.

## 3. Quy trình thực thi cho Agent

1. Nhận chuỗi tin nhắn đánh giá từ khách hàng (`feedback_text`).
2. Chạy script `scripts/analyze_customer_feedback.py`.
3. Nếu phát hiện `extracted_preferences`, lưu vào hồ sơ khách hàng quen.
4. Nếu phát hiện `urgent_attention_needed = True`, AG-VOC báo động Quản lý xử lý khẩn cấp.
