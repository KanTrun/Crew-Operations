---
phase: 2
title: "API & UI cấu hình khung giờ"
status: completed
priority: P1
effort: "1d"
dependencies: [1]
---

# Phase 2: API & UI cấu hình khung giờ

## Overview

KV template `khung_gio` cho 3 khung; PATCH endpoint; panel cấu hình trên roster cho quản lý.

## Requirements

- Functional: chủ/quản lý đổi giờ sáng/chiều/tối; GET lịch áp dụng lên mọi ca cùng khung
- Non-functional: validate HH:MM; `bat_dau < ket_thuc`

## Architecture

- `main.py`: `_khung_template()`, `_apply_khung_to_ca()`, `PATCH /api/v1/lich-tuan/khung-gio`
- `KhungConfigPanel.tsx` — form 3 khung

## Related Code Files

- Modify: `apps/api/src/ca_api/interfaces/http/main.py`
- Create: `apps/web/src/app/roster/KhungConfigPanel.tsx`
- Modify: `apps/web/src/app/roster/page.tsx`
- Create: `apps/api/tests/unit/test_lich_tuan_khung.py`

## Implementation Steps

1. KV defaults + apply on `_format_ca_list` output
2. PATCH + auth quan_ly
3. UI panel + reload lịch
4. Unit tests

## Success Criteria

- [ ] Đổi sáng 06:00–11:00 phản ánh trên lưới và modal
- [ ] Test PATCH 403 nhân viên, 200 quản lý

## Risk Assessment

- Đổi giờ không re-solve solver — hiển thị cảnh báo trong panel (không block MVP).
