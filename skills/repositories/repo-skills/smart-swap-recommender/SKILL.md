---
name: smart-swap-recommender
description: "Kỹ năng đề xuất người thế ca tối ưu khi có nhân sự xin nghỉ đột xuất, cân bằng kỹ năng và giờ công trong tuần."
disable-model-invocation: true
metadata:
  role: operating
  package: packages/agents
---

# Smart Swap Recommender Skill

Sử dụng kỹ năng này khi có nhân viên báo vắng, xin nghỉ ốm hoặc cần tìm người đổi ca khẩn cấp trong ngày.

## 1. Kiểm tra nhanh (Smoke Check)

Chạy script tìm ứng viên đổi ca:

```bash
python skills/repositories/repo-skills/smart-swap-recommender/scripts/recommend_shift_swap.py
```

## 2. Tiêu chí tính điểm

Xem chi tiết tại [references/swap_scoring_policy.md](references/swap_scoring_policy.md):
- Loại bỏ ngay ứng viên bận học (TKB) hoặc trùng ca.
- Ưu tiên người có đúng kỹ năng ca yêu cầu (+40đ).
- Ưu tiên người làm ít giờ hơn trong tuần (+30đ).

## 3. Quy trình thực thi cho Agent

1. Xác định thông tin ca bị trống: giờ làm, vị trí chuyên môn (`shift_info`).
2. Thu thập danh sách nhân sự quán (`all_staff`).
3. Chạy script `scripts/recommend_shift_swap.py`.
4. Trả về cho Quản lý / AG-COPILOT ứng viên số 1 (`best_candidate`) kèm điểm số và lý do cụ thể để phê duyệt 1-click.
