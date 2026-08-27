---
phase: 6
title: "Facebook page surface replay"
status: done
priority: P1
effort: "2-3d"
dependencies: [1]
---

# Phase 6: Facebook page surface replay

## Overview

Surface web **`/page`** (Page quán): hàng đợi comment/Messenger **fixture**, trả lời mock, nháp bài + duyệt quản lý. Không đè `/inbox` lịch. Chưa cần page Meta thật.

## Requirements

- Functional: list thread fixture; reply lưu mock; draft post trạng thái `nhap|cho_duyet|da_dang_mock`; empty state “Chưa nối Meta”
- Non-functional: chỉ `quan_ly`/`chu_quan` đăng/duyệt; NV có thể trả lời thread nếu policy cho phép (mặc định: QL + NV ca)

## Architecture

```text
PagePort(replay) → threads/posts store
       │
       ▼
  /page UI ── reply ──► mock outbox
       └── draft post ──► duyệt QL ──► mock published
```

Khách khó chịu / sự cố → optional tạo **việc treo** (cầu nối ops), không CRM.

## Related Code Files

- Create: `apps/web/src/app/page-quan/` hoặc `/page/page.tsx` (tránh đụng `app/page.tsx` landing — dùng `/page-quan` hoặc `/kenh-page`)
- Create: API `/api/v1/page/...` replay
- Create: `data/golden/page/threads_01.json`
- Modify: AppShell nav (manager)
- Modify: `docs/ui-surfaces.md`

## Implementation Steps

1. Chọn route không đụng landing: khuyến nghị **`/page-quan`**
2. API list/reply/draft trên store SQLite hoặc JSON var
3. UI neo-brutalism theo design-guidelines hiện có
4. Nút “Tạo việc treo” từ một thread
5. E2E: mở `/page-quan` thấy N thread fixture

## Success Criteria

- [ ] Fixture page dùng được không có token Meta
- [ ] Không lẫn với `/inbox` ràng buộc
- [ ] Manager duyệt nháp bài (trạng thái mock)

## Risk Assessment

Nhầm route `/page` với Next landing `app/page.tsx` — dùng `/page-quan` từ đầu.
