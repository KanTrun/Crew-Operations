---
phase: 6
title: "Sprint 5 — Cẩm nang sống"
status: completed
priority: P1
effort: "17.25 person-days"
dependencies: [5]
software_note: "Luật→solver inject; Playwright 8 flows; §14.6 so_luat_that_quan=0 cho đến khi quán gắn dữ liệu"
---

# Phase 6: Sprint 5 — Cẩm nang sống đóng vòng lặp

## Overview

**Mục tiêu:** một luật đi hết **8 bước**, từ lần sửa người → tham số lõi.

**Chiếu được:** thẻ luật có nguồn 4 lần sửa bấm xem được, kết quả tập sự, số lần áp dụng.

## Requirements

- Functional: pattern mine; probation ×5; auto-disable <80%; VF-RULE; map luật→solver/template/threshold; orc budget+replay; swap market 3-way; QR attendance; AG-RULE/SOP/WASTE; playbook UI; SOP chat; Playwright 8 flows
- Non-functional: ADR-010/011; A/B experiment bảng sơ bộ

## Architecture

Vòng đời §9.2. AG-RULE không đề xuất nếu <3 bằng chứng. Fail-closed VF-RULE. Chỉ 5 loại luật §9.1.

## Related Code Files

- Create: `packages/playbook/{tim_mau,tap_su,theo_doi}`, `vf_rule`, `ag_rule/`, `ag_sop/`, `ag_waste/`, swap-market API, QR, playbook+sop-chat UI, e2e specs
- Modify: orc budget/replay; solver param injection từ luật đã duyệt
- Delete: —

## Implementation Steps

| Who | Work | Days |
|-----|------|------|
| A | Playbook còn lại; VF-RULE; map luật→lõi | 4,5 |
| B | Orc p2; chợ đổi ca; QR 1 lần | 4,5 |
| C | AG-RULE; AG-SOP; AG-WASTE; bảng kết quả phần C | 4,25 |
| D | Agent-trace p2; playbook UI; SOP UI; Playwright 8 | 4,0 |

1. Chứng minh ≥1 luật bị VF-RULE **loại** (nếu không có ca loại → cổng chưa đạt)
2. Nhét luật 60% accuracy → phải tự tắt
3. AG-SOP: 20 câu; mọi câu có citation; ≥1 “chưa có trong cẩm nang”
4. Nếu không đủ bằng chứng thật: **không bịa** — dùng lịch sử dựng lại + nói số thật

## AgentKit commands

```text
/ak:cook
/ak:test
/ak:web-testing
/ak:docs          # ADR-010, ADR-011
make ab
make replay PHIEN=...
```

## Todo

- [x] 1 luật đủ 8 bước đang hiệu lực (**dựng lại 8 tuần**, không phải NV quán)
- [x] ≥1 luật bị VF-RULE loại + lý do UI
- [x] Bảng tập sự 5 lần
- [x] Auto-disable test 60%
- [x] AG-SOP 20 Q + citations / «chưa có trong cẩm nang»
- [x] A/B bảng có số sơ bộ (`make ab` + `/api/v1/ab`; replay: `make replay PHIEN=...`)
- [x] Playwright 8 luồng (`apps/web/e2e/flows.spec.ts`, CI job 08)
- [x] Map luật hiệu lực → CP-SAT (`ca_solver.luat_inject` + lifecycle `dang_giai`)

## Success Criteria

- [ ] Cổng ra sprint 5 — 6 điều kiện §14.6 *(phần mềm xong; luật quán thật = 0)*

## Risk Assessment

| Risk | Signal | Response |
|------|--------|----------|
| 0 luật đủ chứng | Pattern count <3 | Demo dựng lại + nói thật; không fake DB |
| AG-RULE viết luật về người | Prompt drift | PHAM_VI + VF-RULE + eval đỏ |
