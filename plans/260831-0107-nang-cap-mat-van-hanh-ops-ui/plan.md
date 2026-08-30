---
title: "Nâng cấp mặt vận hành Ops UI"
description: "Biến hub và 10 trang ops từ form mỏng thành bảng điều khiển doanh nghiệp — picker người/ca, nhiều tương tác, API thật."
status: in-progress
priority: P1
effort: "4-5d"
tags: [ops-ui, hom-nay, web, api]
created: 2026-08-31
blockedBy: []
blocks: []
brainstorm: plans/reports/260831-brainstorm-ops-ui-redesign.md
---

# Nâng cấp mặt vận hành Ops UI

## Overview

Triển khai hướng **B** từ brainstorm: lớp Ops dùng chung + API bổ sung tối thiểu + redesign từng trang. Giữ `kit.tsx`, `globals.css`, design v3. Không mock frontend; dữ liệu qua FastAPI + KV.

## Hợp đồng

| Trường | Nội dung |
|--------|----------|
| **Outcome** | Hub `/hom-nay` và 10 trang ops tương tác được, nhãn tiếng Việt, chọn người/ca từ lịch — không mã `nv_03` trên UI |
| **Constraints** | `present.ts`, role nav, Docker `make docker-up`, không Postgres migration |
| **Non-goals** | IA 3-hub, agent mới, rewrite backend |
| **Acceptance** | ≥3 hành động/trang; zero default dev IDs; API mới có test; docker build + git push |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Ops context & pickers](./phase-02-ops-context-va-pickers.md) | Pending |
| 2 | [Hub & trang nặng](./phase-03-hub-va-trang-nang.md) | Pending |
| 3 | [Trang overflow & API](./phase-04-trang-overflow-va-api.md) | Pending |
| 4 | [Docker, git, test, ship](./phase-05-docker-git-test-ship.md) | Pending |

## Success Criteria

- [ ] `PersonSelect` / `ShiftSelect` dùng `/api/v1/lich-tuan` + `/api/v1/me`
- [ ] `/hom-nay` bento 12-col + preview treo/cảnh báo
- [ ] Đổi ca: đồng ý 3 nhánh qua API mới
- [ ] Treo: đánh dấu xử lý; Handover: lưu lịch sử
- [ ] `make docker-up` pass; git push thành công

<!-- slug: nang-cap-mat-van-hanh-ops-ui -->
