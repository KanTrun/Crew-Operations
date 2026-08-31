---
phase: 1
title: "Lưới tóm tắt & lọc"
status: completed
priority: P1
effort: "1d"
dependencies: []
---

# Phase 1: Lưới tóm tắt & lọc

## Overview

Refactor grid `/roster`: ô gọn, zebra, giờ từ `bat_dau`/`ket_thuc`, toolbar lọc, spotlight ngày, bỏ dropdown khỏi lưới chính.

## Requirements

- Functional: ô hiển thị số NV + vị trí; click ô/header mở modal ngày
- Non-functional: mobile không cuộn ngang dư thừa; a11y `scope`/`caption`

## Architecture

- `lib/roster.ts` — `shiftRowLabel`, `shiftCellSummary`
- `roster/RosterGrid.tsx` — bảng `.nq-roster-table`
- `roster/page.tsx` — state lọc + compose

## Related Code Files

- Create: `apps/web/src/lib/roster.ts`, `apps/web/src/app/roster/RosterGrid.tsx`
- Modify: `apps/web/src/app/roster/page.tsx`, `apps/web/src/app/globals.css`

## Implementation Steps

1. Helper giờ từ shift data
2. RosterGrid compact + zebra classes
3. ListToolbar (search, khung, vị trí)
4. Spotlight `data-day` trên cột; modal giữ logic pin

## Success Criteria

- [ ] Không còn hardcode "Sáng 07–12"
- [ ] Ô lưới không có dropdown thêm người
- [ ] Zebra hàng lẻ/chẵn rõ trên dark theme

## Risk Assessment

- Rủi ro: file `page.tsx` lớn — tách `RosterGrid` giảm regression. Mitigation: giữ modal/pin logic trong page.
