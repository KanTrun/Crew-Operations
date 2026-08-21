---
phase: 3
title: "Sprint 2 — Mốc sinh tử solver"
status: completed
priority: P1
effort: "17.75 person-days"
dependencies: [2]
---

# Phase 3: Sprint 2 — Mốc sinh tử thứ nhất (solver)

## Overview

**Mục tiêu:** máy sinh lịch tuần hợp lệ, **0 vi phạm ràng buộc cứng**.

**Chiếu được:** `make bench` → `scripts/solve_tuan.py` + `scripts/verify_hard.py` (mọi dòng cứng = 0). UI: `/roster`.

## Todo

- [x] Lịch 25×21, 0 hard violation (script độc lập)
- [x] Solve <60s hoặc best-on-timeout
- [x] Fairness property test 8 tuần
- [x] AG-TKB metric ghi bảng kết quả (`docs/metrics-18-2.md`)
- [x] Ảnh mờ → escalate người (VF-CONF + `tkb_blur_01`)
- [x] Grid đọc được lịch từ mock/API (`/roster` + `GET /api/v1/lich-tuan`)

## Success Criteria

- [x] Cổng ra sprint 2 — 6 điều kiện §14.3 (mốc sinh tử 1)

## Notes

ADR-004 CP-SAT · ADR-005 fairness debt. Soft s01/s02 trong objective; s03–s05 trọng số sẵn, s05 chưa đóng đủ (có thể cắt 5→3 sau nếu cần).
