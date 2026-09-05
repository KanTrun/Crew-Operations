---
name: handover-reconciliation
description: "Kỹ năng đối soát tiền két thu ngân và bàn giao việc treo ca làm việc giữa các nhân sự."
disable-model-invocation: true
metadata:
  role: operating
  package: packages/opsengine
---

# Handover Reconciliation Skill

Kỹ năng dùng để đối soát doanh thu tiền mặt thực tế trong két so với số liệu ghi nhận trên phần mềm POS, và kiểm tra danh sách việc treo cần bàn giao giữa 2 ca.

## 1. Kiểm tra nhanh (Smoke Check)

Chạy script đối soát tiền két:

```bash
python skills/repositories/repo-skills/handover-reconciliation/scripts/reconcile_shift_cash.py
```

## 2. Quy tắc cân bằng két

Xem chi tiết tại [references/handover_checklist.md](references/handover_checklist.md):
- Tiền thực tế trong két = Tiền đầu ca + Doanh thu tiền mặt POS - Các khoản chi két.
- Mọi chênh lệch âm (thiếu tiền) đều phải ghi nhận biên bản giao ca.

## 3. Quy trình thực thi cho Agent

1. Lấy dữ liệu `opening_cash`, `pos_cash_sales`, `paid_outs` từ POS.
2. Thu thập số tiền mặt nhân viên đếm được cuối ca (`actual_cash_counted`).
3. Chạy script `scripts/reconcile_shift_cash.py`.
4. Báo cáo kết quả:
   - Nếu `MATCHED`: Xác nhận bàn giao ca hoàn tất.
   - Nếu `SHORTAGE` hoặc `SURPLUS`: Yêu cầu kiểm đếm lại hoặc lập biên bản giao ca.
