---
phase: 8
title: "Tài liệu, kiểm chứng, commit"
status: completed
priority: P1
effort: "0.5 ngày"
dependencies: [7]
---

# Phase 8: Tài liệu, kiểm chứng, commit

## Overview

Chốt tài liệu, chạy toàn bộ cổng, và commit từng phase theo conventional commits.

## Requirements

- Functional: `docs/ui-surfaces.md` cập nhật mô tả mặt `waste`.
- Functional: `README.md` bảng endpoint có `/api/v1/hao-hut` và intent `ANALYZE_LOSS`.
- Functional: ADR ghi quyết định "ảnh sinh tại máy, không dùng API ảnh đám mây".
- Non-functional: chạy hết cổng trước khi commit cuối.
- Non-functional: commit không tham chiếu AI; scope thuộc `commitlint.config.cjs`.

## Related Code Files

- Modify: `docs/ui-surfaces.md`
- Modify: `README.md`
- Create: `docs/adr/019-anh-san-pham-sinh-tai-may.md`
- Modify: `docs/THIRD_PARTY.md` (nếu phase 6 chưa làm)
- Modify: plan này (đánh dấu phase xong, cập nhật `ak plan status`)

## Implementation Steps

1. Cập nhật `ui-surfaces.md` + `README.md`.
2. Viết ADR-019 theo house style các ADR đã có (đọc 2 ADR gần nhất trước để theo mẫu).
3. Chạy chuỗi cổng: `ruff check apps/api/src packages scripts` → `pytest` →
   `npm run lint` trong `apps/web` → `npm run build` → `npm run test:e2e`.
4. Kiểm `make contracts` không drift.
5. Commit từng phase (nếu chưa commit ở từng phase) bằng thông điệp tiếng Việt qua
   `git commit -F <file>` (tránh mojibake PowerShell — xem memory repo).
6. Cập nhật trạng thái phase trong plan; chạy `ak plan status` để đối chiếu.

## Success Criteria

- [x] `ruff check apps/api/src packages scripts` sạch.
- [x] `pytest` xanh toàn bộ.
- [x] `cd apps/web; npx tsc --noEmit` sạch.
- [x] `npx next build` thành công, route `/hao-phi` có trong output.
- [x] e2e xanh (hoặc nêu rõ spec nào đỏ và vì sao, kèm bằng chứng).
- [x] `make contracts` lần hai không đổi file nào.
- [x] `git log` có commit cho từng phase, đúng conventional commit + scope hợp lệ.
- [x] `docs/adr/019-*.md` tồn tại và nêu rõ lý do chọn sinh ảnh tại máy.

## Risk Assessment

Rủi ro: e2e cần `next build` + hai webServer; máy dev không có `py` launcher
(đã ghi trong memory repo). **Tín hiệu:** playwright config hỏng ở bước dựng server.
**Phản ứng:** chạy thủ công `demo_api.py` rồi để playwright tái dùng cổng, hoặc
nêu rõ giới hạn môi trường kèm bằng chứng thay vì tuyên bố "đã xanh".

