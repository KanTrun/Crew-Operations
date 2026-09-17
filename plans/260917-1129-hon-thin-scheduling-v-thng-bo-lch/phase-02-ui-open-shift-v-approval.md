---
title: "Phase 2: UI open shift và approval"
status: done
---

# Phase 2: UI open shift và approval

## Overview

Nối UI hiện hữu với open-shift APIs để nhân viên tự nhận ca trống và quản lý xử lý
khoảng trống theo quyền, không nhân đôi logic eligibility ở client.

## Requirements

- [ ] Nhân viên xem danh sách ca trống liên quan và claim bằng API hiện có.
- [ ] Quản lý xem trạng thái open shift/claim và action xử lý hiện được backend hỗ trợ.
- [ ] Loading, empty, success, stale/conflict và error states không làm mất roster hiện tại.
- [ ] UI giữ ngôn ngữ, component và permission patterns đang dùng trong repo.

## Implementation Steps

1. Xác nhận payload thực tế của list/create/claim/resolve routes và role context frontend.
2. Thêm data loading và mutation nhỏ nhất vào `roster/page.tsx` và/hoặc `doi-ca/page.tsx` theo ownership hiện tại.
3. Refresh dữ liệu server sau mutation; hiển thị message từ backend cho eligibility và race failures.
4. Thêm test focused cho rendering/action mới rồi chạy typecheck trước khi mở rộng edit.

## Todo

- [ ] Hiển thị ca trống và trạng thái claim.
- [ ] Nối employee claim action.
- [ ] Nối manager resolution/approval action API đang hỗ trợ.
- [ ] Hoàn thiện empty/loading/error/permission states.
- [ ] Chạy typecheck và focused UI test.

## Success Criteria

Luồng nhân viên và quản lý hoàn tất từ UI đến backend persistence, kể cả stale claim,
mà không thay đổi swap flow hoặc sao chép luật eligibility sang TypeScript.
