---
name: inventory-restock-check
description: "Kỹ năng dự báo và cảnh báo đặt hàng nguyên vật liệu khi tồn kho chạm điểm đặt hàng lại (Reorder Point)."
disable-model-invocation: true
metadata:
  role: operating
  package: packages/opsengine
---

# Inventory Restock Check Skill

Sử dụng kỹ năng này để kiểm tra lượng tồn kho thực tế của quán, phát hiện các mặt hàng nguy cơ đứt hàng và sinh đề xuất nhập hàng (Draft ActionProposal) cho Quản lý / AG-COPILOT.

## 1. Kiểm tra nhanh (Smoke Check)

Chạy script kiểm tra tồn kho:

```bash
python skills/repositories/repo-skills/inventory-restock-check/scripts/check_inventory_restock.py
```

## 2. Công thức ROP

Xem chi tiết tại [references/reorder_thresholds.md](references/reorder_thresholds.md):
- Điểm đặt hàng lại = (Tiêu hao ngày x Số ngày giao) + Mức tối thiểu an toàn.
- Cảnh báo: `CRITICAL` (Dưới mức tối thiểu) hoặc `WARNING` (Cần lên đơn trong 24h).

## 3. Quy trình thực thi cho Agent

1. Lấy dữ liệu tồn kho hiện tại (`current_inventory`).
2. Chạy script `scripts/check_inventory_restock.py`.
3. Nếu phát hiện `alerts`, AG-COPILOT tổng hợp danh sách mặt hàng cần nhập và đề xuất Quản lý duyệt đặt hàng.
