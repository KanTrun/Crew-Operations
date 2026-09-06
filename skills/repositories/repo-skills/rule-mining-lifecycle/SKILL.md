---
name: rule-mining-lifecycle
description: "Kỹ năng phân tích lịch sử sửa đổi và tự động phát hiện mẫu lặp lại (>= 3 lần) để đề xuất luật mới theo Cẩm nang 8 bước."
disable-model-invocation: true
metadata:
  role: operating
  package: packages/playbook
---

# Rule Mining Lifecycle Skill

Kỹ năng giúp cẩm nang của quán "tự học và tự tiến hóa" từ thực tế vận hành, biến các lỗi lặp đi lặp lại thành luật mới được kiểm soát chặt chẽ.

## 1. Kiểm tra nhanh (Smoke Check)

Chạy script tìm mẫu luật:

```bash
python skills/repositories/repo-skills/rule-mining-lifecycle/scripts/mine_rule_patterns.py
```

## 2. Tiêu chuẩn 8 bước

Xem chi tiết tại [references/rule_lifecycle_stages.md](references/rule_lifecycle_stages.md):
- Ngưỡng phát hiện mẫu: Tối thiểu $\ge 3$ lần lặp lại cùng một lý do/nhân sự/ngày.
- Trạng thái ban đầu: `ready_for_trial` (cho phép chạy thử nghiệm ngầm trong 5 ca).

## 3. Quy trình thực thi cho Agent

1. Lấy danh sách lịch sử sửa đổi từ `packages/playbook` (`list_sua()`).
2. Chạy script `scripts/mine_rule_patterns.py`.
3. Nếu tìm thấy luật đề xuất, AG-RULE / AG-COPILOT tạo đề xuất 1 câu ngắn gọn trình Quản lý phê duyệt.
