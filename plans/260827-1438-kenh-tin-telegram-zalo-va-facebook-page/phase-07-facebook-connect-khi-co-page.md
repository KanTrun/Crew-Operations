---
phase: 7
title: "Facebook connect khi co page"
status: pending
priority: P2
effort: "2d + App Review"
dependencies: [6]
---

# Phase 7: Facebook connect khi có page

## Overview

Khi chủ quán đã tạo Facebook Page + Meta App: checklist nối token, bật `PagePort` live (đọc/ghi qua Graph theo quyền đã duyệt), tắt replay. Phase này **không chặn** demo Phase 1–6.

## Requirements

- Functional: form manager dán Page ID + token (hoặc OAuth sau); webhook verify challenge; map webhook → cùng store Phase 6
- Non-functional: token mã hóa at-rest nếu có thể; không log token; App Review ngoài repo

## Architecture

```text
Meta App → Page token (env/DB) → PagePort(live)
Webhook → verify → normalize → same /page-quan store
Publish approved draft → Graph feed (khi quyền đủ)
```

## Related Code Files

- Modify: `PagePort` live adapter
- Modify: webhook router Facebook
- Create: `docs/runbooks/facebook-page-connect.md` checklist
- Modify: empty state `/page-quan` → “Đã nối” khi health check Graph OK

## Implementation Steps

1. Runbook: tạo App, quyền, webhook callback URL, verify token
2. Health: `GET /api/v1/page/status` → connected|replay
3. Wire inbound comment/messages → threads
4. Wire publish draft đã duyệt → Graph (feature flag)
5. Rollback: `NHIPQUAN_PAGE_MODE=replay`

## Success Criteria

- [ ] Runbook đủ để nối ≤ 30 phút khi đã có page
- [ ] Flag replay vẫn chạy CI không token
- [ ] Live chỉ khi manager bật + token hợp lệ

## Risk Assessment

App Review chậm / từ chối — signal: không publish được; response: giữ Business Suite thủ công + `/page-quan` replay cho ops nội bộ; không block Lô 1.
