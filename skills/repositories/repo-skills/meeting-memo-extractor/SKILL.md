---
name: meeting-memo-extractor
description: "Kỹ năng trích xuất biên bản họp ca thành danh sách đầu việc có người phụ trách và hạn hoàn thành rõ ràng."
disable-model-invocation: true
metadata:
  role: operating
  package: packages/agents
---

# Meeting Memo Extractor Skill

Kỹ năng dùng để chuyển đổi nội dung cuộc họp ngắn hoặc thông báo nội bộ thành danh sách việc cần làm (Pending tasks trong opsengine).

## 1. Kiểm tra nhanh (Smoke Check)

Chạy script trích xuất đầu việc:

```bash
python skills/repositories/repo-skills/meeting-memo-extractor/scripts/extract_meeting_actions.py
```

## 2. Tiêu chuẩn biên bản họp

Xem chi tiết tại [references/meeting_format_guide.md](references/meeting_format_guide.md):
- Bóc tách: Người phụ trách, Đầu việc cụ thể, Mức độ ưu tiên.

## 3. Quy trình thực thi cho Agent

1. Nhận văn bản ghi chép cuộc họp từ Quản lý (`meeting_text`).
2. Chạy script `scripts/extract_meeting_actions.py`.
3. Tạo các thẻ việc treo tương ứng để theo dõi tiến độ hoàn thành.
