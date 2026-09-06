---
name: daily-brief-generator
description: "Kỹ năng tự động tạo bản tin giao ban ca làm việc (nhân sự, doanh thu mục tiêu, việc treo từ ca trước)."
disable-model-invocation: true
metadata:
  role: operating
  package: packages/agents
---

# Daily Brief Generator Skill

Kỹ năng dùng để tổng hợp thông tin và định dạng bản tin đầu ca làm việc gửi vào nhóm chat nhân viên (Telegram/Zalo).

## 1. Kiểm tra nhanh (Smoke Check)

Chạy script sinh bản tin:

```bash
python skills/repositories/repo-skills/daily-brief-generator/scripts/generate_daily_brief.py
```

## 2. Quy chuẩn bản tin

Xem chi tiết tại [references/brief_templates.md](references/brief_templates.md):
- Phần 1: Nhân sự trực ca (Kíp trưởng, Barista, Thu ngân).
- Phần 2: Mục tiêu doanh thu và món trọng tâm đẩy bán.
- Phần 3: Lưu ý việc treo từ ca trước.

## 3. Quy trình thực thi cho Agent

1. Thu thập dữ liệu ca làm việc từ lịch phân ca CP-SAT.
2. Lấy danh sách việc treo từ `opsengine`.
3. Chạy script `scripts/generate_daily_brief.py` để tạo bản tin hoàn chỉnh.
4. Trả về cho AG-COPILOT để gửi tự động vào nhóm chat ca làm việc.
