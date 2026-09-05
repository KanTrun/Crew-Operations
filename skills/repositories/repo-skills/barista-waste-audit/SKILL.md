---
name: barista-waste-audit
description: "Kỹ năng kiểm tra định lượng công thức pha chế và tính toán tỷ lệ hao hụt nguyên vật liệu (cà phê, sữa, siro)."
disable-model-invocation: true
metadata:
  role: operating
  package: packages/opsengine
---

# Barista Waste Audit Skill

Kỹ năng dùng để đối soát định mức tiêu thụ nguyên vật liệu ca làm việc, phát hiện lãng phí hoặc hao hụt bất thường so với số lượng đồ uống bán ra từ máy POS.

## 1. Kiểm tra nhanh (Smoke Check)

Chạy script kiểm tra hao hụt:

```bash
python skills/repositories/repo-skills/barista-waste-audit/scripts/audit_recipe_waste.py
```

## 2. Bảng định mức công thức

Xem chi tiết tại [references/standard_recipes.md](references/standard_recipes.md):
- Espresso/Americano: 18g cà phê hạt.
- Latte/Capuccino: 18g cà phê hạt + 150ml sữa tươi.
- Ngưỡng hao hụt tối đa cho phép: 5.0%.

## 3. Quy trình thực thi cho Agent

1. Lấy dữ liệu số ly đồ uống bán ra từ hệ thống POS (`sold_items`).
2. Lấy dữ liệu tồn kho đầu ca trừ tồn kho cuối ca (`actual_used`).
3. Chạy script `scripts/audit_recipe_waste.py`.
4. Nếu `compliant = False`, Agent AG-WASTE hoặc AG-COPILOT tạo phiếu nhắc nhở Barista hoặc cảnh báo quản lý quán kiểm tra lại hao hụt nguyên liệu.
