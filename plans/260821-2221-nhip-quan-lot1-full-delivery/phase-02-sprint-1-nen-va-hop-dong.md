---
phase: 2
title: "Sprint 1 — Nền và hợp đồng"
status: completed
priority: P1
effort: "17.25 person-days"
dependencies: [1]
---

# Phase 2: Sprint 1 — Nền và hợp đồng

## Overview

**Mục tiêu:** không ai bị chặn bởi ai.

**Chiếu được:** `make demo` (API) + `cd apps/web && npm run dev` → đăng nhập `quanly/demo` → năm hợp đồng mock (`nguon=fixture_synthetic`).

## Todo

- [x] 5 contracts + schema export (`make contracts`) + tests
- [x] CI unit cài workspace; ruff gate cứng (không `|| true`)
- [x] `make demo` / `scripts/demo_api.py` + login UI
- [x] ADR-001, 002, 003 (đã có từ phase-01)
- [x] 3 YAML fixture (ADR-012) — không bịa quán thật

## Success Criteria

- [x] Cổng ra kỹ thuật Sprint 1 đủ để mở S2 trên fixture
- [x] Solver c01–c06 + tests; agent runtime replay + cache
- [x] Web tokens theo `docs/design-guidelines.md`

## Notes

YAML “quán thật” vẫn pending quan sát ca — dùng fixture có nhãn. Docker full stack: `make dev`.
