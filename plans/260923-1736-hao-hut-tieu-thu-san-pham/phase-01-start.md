---
phase: 1
title: "Khảo sát & bằng chứng"
status: completed
priority: P1
effort: "0.5 ngày"
dependencies: []
---

# Phase 1: Khảo sát & bằng chứng

## Overview

Chốt hiện trạng bằng bằng chứng đọc được từ mã, để mọi phase sau không xây trên
phỏng đoán. Không sửa mã ở phase này.

## Requirements

- Functional: xác định chính xác đường đi dữ liệu hao hụt hiện có (ghi, đọc, lưu).
- Non-functional: mọi kết luận phải kèm `file:line`; không suy diễn từ tên gọi.

## Findings

### Đã có gì

| Thành phần | Vị trí | Trạng thái |
|---|---|---|
| Agent hao hụt | `packages/agents/src/ca_agents/ag_waste/` (`extract.py`, `PHAM_VI.md`) | Chỉ gom cụm ghi chú theo thứ |
| Trang | `apps/web/src/app/hao-phi/page.tsx` (167 dòng) | Form ghi chú + danh sách cụm |
| API cũ | `sprint45.py:1365` `POST /api/v1/waste`, `:1628` `GET /api/v1/waste` | Ghi `kv waste_notes`; không audit |
| Tool mẹ | `tool_registry.py:792` `tool_get_waste_summary` | Đọc `waste_notes`, gọi `waste_cluster` inject |
| Phép toán mẫu | `skills/repositories/repo-skills/barista-waste-audit/scripts/audit_recipe_waste.py` | `RECIPES`, ngưỡng 5%, `compliant` |
| Dữ liệu kiểm kê | `kv kiem_ke`, 112 dòng trong `data/seed/sample.json` | Công thức §4.3, có `dem_tay_doc_lap` |
| Công thức BOM | `menu_mon.bom` (`persist.py:_MENU_MAC_DINH`), `BomEditor` | `bom-editor.tsx:6` có `BOM_INGREDIENTS` |
| Tiêu thụ tự động | `pos.py:171` `_ghi_tieu_thu_uoc_luong` | Ghi khi đơn sang `xong`, `nguon="uoc_luong_tu_quay"` |
| Danh mục kho mẫu | `data/fixtures/professional/pos.json` `inventory_items` | 8 mặt hàng, có `min_level`/`reorder_level` |
| Nhãn tiếng Việt | `apps/web/src/lib/present.ts:236` `NGUYEN_NHAN`, `:257` `MAT_HANG` | Đã có sẵn bảng nhãn |

### Lỗ thật đã xác nhận

1. **Không có phép toán hao hụt nào trong hệ thống.** `ag_waste` không nhận
   `mat_hang`/`so_luong`/`nguyen_nhan` dù bản ghi có đủ ba trường.
2. **`kiem_ke` bị bỏ rơi.** Không endpoint nào đọc `kiem_ke` ngoài test seed.
3. **`POST /api/v1/waste` thiếu `_audit`** — so với `tieu_thu_ghi` cùng file có gọi.
4. **`worker._tong_ket_ngay` đọc sai khoá thời gian** (`ngay`/`at`) trong khi bản
   ghi thật dùng `luc`/`created_at` ⇒ đếm ra 0.
5. **Không có nước đóng chai trong danh mục mặc định** (`_MENU_MAC_DINH` chỉ 4 món
   cà phê/trà), dù `BOM_INGREDIENTS` đã có `nuoc_dong_chai`.
6. **`data/menu_images/` rỗng** và bị `.gitignore:89` bỏ qua; không món nào có ảnh.

## Related Code Files

- Read-only ở phase này.

## Success Criteria

- [x] Mọi kết luận có `file:line` kiểm lại được.
- [x] Phân biệt rõ "đã có" và "còn thiếu" — không trộn.
- [x] Xác định ba nguồn thật để tính hao hụt: `kiem_ke`, `menu_mon.bom`, `waste_notes`.

## Risk Assessment

Rủi ro: `kiem_ke` là dữ liệu seed sinh từ `scripts/generate_fixture_data.py`, không
phải bản ghi do quán gõ tay. **Tín hiệu đã vỡ:** nếu chỉ có `kiem_ke` mà không có
đơn quầy thật thì cột "lý thuyết" luôn rỗng. **Phản ứng đã định trước:** engine
phải trả `thieu_du_lieu` cho cột lý thuyết thay vì suy diễn — đã đưa vào acceptance
criteria số 2.

