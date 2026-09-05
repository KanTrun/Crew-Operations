---
name: sop-execution
description: "Kỹ năng xác minh và hướng dẫn thực thi quy trình vận hành quán (SOP) theo Cẩm nang 8 bước."
disable-model-invocation: true
metadata:
  role: operating
  package: packages/playbook
---

# SOP Execution Skill

Sử dụng kỹ năng này khi nhân viên thực hiện các quy trình nghiệp vụ (mở ca, giao ca, đóng ca, kiểm kho, xử lý hỏng hóc thiết bị).

## 1. Kiểm tra nhanh (Smoke Check)

Kiểm tra checklist quy trình:

```bash
python skills/repositories/repo-skills/sop-execution/scripts/verify_sop_checklist.py
```

## 2. Quy chuẩn 8 bước cẩm nang

Xem chi tiết tại [references/eight_step_playbook.md](references/eight_step_playbook.md):
- Mọi điều chỉnh quy trình đều trải qua các bước: Ghi nhận -> Tìm mẫu -> Đề xuất -> Cổng VF -> Tập sự -> Duyệt -> Tham số hóa -> Đào thải.

## 3. Quy trình thực thi cho Agent

1. Xác định quy trình mà nhân viên đang thực hiện (ví dụ: `quy_trinh_mo_ca`).
2. Lấy danh sách `required_steps` từ cẩm nang.
3. Thu thập danh sách `completed_steps` từ báo cáo/tin nhắn của nhân viên.
4. Gọi script `scripts/verify_sop_checklist.py` để tính toán tỷ lệ hoàn thành (`completion_rate`).
5. Nếu còn `missing_steps`, agent phản hồi nhắc nhở rõ ràng từng bước còn thiếu.
