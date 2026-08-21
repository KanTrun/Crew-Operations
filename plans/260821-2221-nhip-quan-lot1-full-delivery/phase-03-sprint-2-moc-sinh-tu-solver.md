---
phase: 3
title: "Sprint 2 — Mốc sinh tử solver"
status: pending
priority: P1
effort: "17.75 person-days"
dependencies: [2]
---

# Phase 3: Sprint 2 — Mốc sinh tử thứ nhất (solver)

## Overview

**Mục tiêu:** máy sinh lịch tuần hợp lệ, **0 vi phạm ràng buộc cứng**.

**Chiếu được:** một lệnh CLI in lịch 25 người + báo cáo kiểm tra độc lập (mọi dòng cứng = 0). UI chưa bắt buộc.

## Requirements

- Functional: soft constraints + fairness debt; VF-SCHEMA/TRACE/CONF; AG-TKB; free-tier router; auth 3 roles; roster grid UI đọc mock/API
- Non-functional: solve ≤60s hoặc best-effort timeout; architecture AST tests cho agents

## Architecture

`packages/solver` CP-SAT; ADR-004/005. Gates đầu trong `packages/gates`. AG-TKB + router trong `packages/agents`.

## Related Code Files

- Create: `packages/solver/constraints/*`, `packages/gates/vf_{schema,trace,conf}*`, `packages/agents/ag_tkb/`, roster-grid feature
- Modify: DB migrations, Docker Compose 5 services
- Delete: —

## Implementation Steps

| Who | Work | Days |
|-----|------|------|
| A | Soft×5 + objective; sổ nợ 4 chiều min-max; VF×3 | 4,5 |
| B | Branch protection/CODEOWNERS/templates; Alembic; Compose; domain nửa còn lại; auth | 4,25 |
| C | AG-TKB; router 4 providers; arch tests + golden set 1 | 4,5 |
| D | Lưới lịch kéo-thả/ghim/chặn; upload TKB + confirm cạnh ảnh | 4,5 |

1. Script **độc lập** verify hard constraints (không tin solver tự khai)
2. Cố tình ảnh mờ → VF-CONF đẩy lên người
3. Ghi độ chính xác AG-TKB thật vào bảng 18.2 (kể cả số thấp)
4. Nếu trượt: cắt soft 5→3 + ADR — **không cắt cứng**

## AgentKit commands

```text
/ak:cook
/ak:test          # property test fairness 8 tuần
/ak:research      # xác nhận LICENSE OR-Tools nếu chưa
make bench
make eval         # sau khi có golden TKB
```

## Todo

- [ ] Lịch 25×21, 0 hard violation (script độc lập)
- [ ] Solve <60s hoặc best-on-timeout
- [ ] Fairness property test 8 tuần
- [ ] AG-TKB metric ghi bảng kết quả
- [ ] Ảnh mờ → escalate người
- [ ] Grid đọc được lịch từ mock/API

## Success Criteria

- [ ] Cổng ra sprint 2 — 6 điều kiện §14.3 (mốc sinh tử 1)

## Risk Assessment

| Risk | Signal | Response |
|------|--------|----------|
| Trượt mốc | Hard violation >0 hoặc timeout vô hạn | Cắt soft; giữ cứng; ADR |
| AG-TKB kém | Acc thấp | Giữ VF-CONF; không bịa số |
