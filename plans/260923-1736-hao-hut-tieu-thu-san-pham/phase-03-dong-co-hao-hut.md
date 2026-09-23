---
phase: 3
title: "Động cơ hao hụt"
status: pending
priority: P1
effort: "0.5 ngày"
dependencies: [2]
---

# Phase 3: Động cơ hao hụt

## Overview

Cho AG-WASTE khả năng **tính** hao hụt theo nguyên liệu, không chỉ gom cụm ghi chú.
Toán tất định, thuần, unit-test được (ADR-002).

## Requirements

- Functional: tính lượng lý thuyết từ BOM × số món đã bán.
- Functional: so với lượng thực tế từ `kiem_ke`; ra lệch, tỷ lệ, mức độ.
- Functional: xếp hạng nguyên nhân từ `waste_notes` theo mặt hàng.
- Functional: **gộp nguyên liệu theo `mat_hang`** để nối được BOM ↔ kiểm kê ↔ ghi chú.
- Non-functional: hàm thuần, không I/O, không đọc DB, không gọi mạng.
- Non-functional: thiếu một vế ⇒ `LossLevel.thieu_du_lieu`, các trường số là `None`.

## Architecture

Ba hàm thuần trong `ag_waste`, ăn khớp hợp đồng phase 2:

```text
loc_theo_mat_hang(rows)        -> dict[mat_hang, float]      # gộp nhiều dòng cùng mặt hàng
tinh_ly_thuyet(ban_theo_mon, bom_theo_mon) -> dict[mat_hang, float]
so_hao_hut(ly_thuyet, thuc_te, nguong)     -> list[LossLine]
xep_hang_nguyen_nhan(notes)                -> list[LossCauseRank]
```

`so_hao_hut` là trái tim: với mỗi mặt hàng xuất hiện ở **một trong hai** vế, sinh
một `LossLine`. Mặt hàng chỉ có một vế ⇒ số của vế kia là `None` ⇒ `thieu_du_lieu`.

Ngưỡng: mặc định từ config, cho phép ghi đè theo mặt hàng.

## Related Code Files

- Modify: `packages/agents/src/ca_agents/ag_waste/extract.py`
- Modify: `packages/agents/src/ca_agents/ag_waste/__init__.py`
- Modify: `packages/agents/src/ca_agents/ag_waste/PHAM_VI.md` (khai năng lực mới)
- Create: `packages/agents/tests/test_ag_waste_loss.py`
- Modify: `packages/agents/tests/test_ag_waste.py` (giữ nguyên test cũ — phải còn xanh)

## Implementation Steps

1. Viết `loc_theo_mat_hang`, `tinh_ly_thuyet` — thuần cộng dồn, ép `float`, bỏ giá trị ≤ 0.
2. Viết `so_hao_hut` — xử lý bốn nhánh mức độ, `None` cho vế thiếu, giữ `ty_le` âm.
3. Viết `xep_hang_nguyen_nhan` — đếm theo `nguyen_nhan`, gom `mat_hang` liên quan, sắp giảm dần.
4. Test: hai vế đủ; chỉ một vế; cả hai rỗng; đếm dư (lệch âm); vượt ngưỡng nghiêm trọng;
   hai dòng cùng mặt hàng được gộp; ngưỡng riêng theo mặt hàng thắng ngưỡng mặc định.
5. Cập nhật `PHAM_VI.md`: thêm nhiệm vụ tính hao hụt; giữ nguyên dòng "Cấm".

## Success Criteria

- [ ] `pytest packages/agents -q` xanh, test `test_ag_waste.py` cũ vẫn xanh.
- [ ] Không hàm nào chạm I/O — kiểm bằng cách đọc mã, và test chạy không cần fixture DB.
- [ ] `so_hao_hut` với hai dict rỗng trả `[]`, không raise.
- [ ] Mặt hàng thiếu vế có `muc_do == thieu_du_lieu` và trường số là `None`.
- [ ] `ruff check packages/agents` sạch.

## Risk Assessment

Rủi ro: tên mặt hàng không khớp giữa ba nguồn (`sua_tuoi` ở kiểm kê vs `sua_ml` ở
BOM). **Tín hiệu:** dòng hao hụt ra `thieu_du_lieu` hàng loạt dù dữ liệu có thật.
**Phản ứng:** thêm bảng bí danh (`ALIAS`) trong `ag_waste` và test riêng cho nó;
không tự động fuzzy-match vì fuzzy sẽ ghép sai im lặng.

