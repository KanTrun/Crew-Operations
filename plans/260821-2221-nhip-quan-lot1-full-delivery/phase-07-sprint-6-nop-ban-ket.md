---
phase: 7
title: "Sprint 6 — Nộp bán kết"
status: pending
priority: P1
effort: "14.75 person-days"
dependencies: [6]
---

# Phase 7: Sprint 6 — Nộp bán kết

## Overview

**Mục tiêu:** đóng gói sản phẩm chạy thật, có tài liệu, video, nộp.

**Chiếu được:** tag `v0.1.0-semifinal` + video <5 phút + tài liệu hệ thống.

## Requirements

- Functional: sổ tiêu thụ từ kiểm kê; bench 8 quy mô; reminders+escalate; bù ca khẩn + DB lock; AG-VOC/EXPLAIN/BRIEF; A/B experiment; runbook-demo; slides+video
- Non-functional: ≥165 tests; 11 CI xanh; 11 ADR; THIRD_PARTY đủ; bảng kết quả không số đoán

## Architecture

Sổ tiêu thụ **không agent** (§4.3). Contested claim lock ở DB. Demo path = `make demo` <5 phút từ trắng.

## Related Code Files

- Create: `opsengine/tieu_thu`, `ag_voc/`, `ag_explain/`, `ag_brief/`, API agent-trace read, docs package
- Modify: reminder jobs, emergency fill, ADR-011 contents listing cuts
- Delete: —

## Implementation Steps

| Who | Work | Days |
|-----|------|------|
| A | Sổ tiêu thụ; bench 8; tests ops/playbook/core; giới hạn phương pháp phần A | 3,25 |
| B | Reminders; bù ca+lock; trace API; 11 ADR + THIRD_PARTY | 3,75 |
| C | AG-VOC/EXPLAIN/BRIEF; A/B 1 vs N | 3,75 |
| D | Tài liệu thể lệ; runbook-demo; video+slide | 4,0 |

1. Tag GitHub + release notes liệt kê **được/chưa**
2. Mọi agent Lô 1 có `PHAM_VI.md` 9 thuộc tính (test đỏ nếu thiếu)
3. `/ak:ship` release branch `release/semifinal`
4. `/ak:security-scan` trước nộp

## AgentKit commands

```text
/ak:cook
/ak:docs
/ak:ship
/ak:security-scan
/ak:test
make demo
make budget
git tag v0.1.0-semifinal
```

## Todo

- [ ] ≥165 tests xanh; 11 CI xanh
- [ ] `make demo` <5 phút từ trắng
- [ ] Tag `v0.1.0-semifinal` + notes trung thực
- [ ] 10× PHAM_VI.md + test thiếu tệp
- [ ] 11 ADR incl. ADR-011 cuts
- [ ] THIRD_PARTY đủ license
- [ ] Bảng kết quả: số thật hoặc “chưa đo”

## Success Criteria

- [ ] Cổng ra sprint 6 — 7 điều kiện §14.7
- [ ] Hồ sơ bán kết nộp đủ theo thể lệ

## Risk Assessment

| Risk | Signal | Response |
|------|--------|----------|
| Thiếu số đo | Dòng bảng trống | Ghi “chưa đo” + lý do — **cấm** số đẹp |
| Race bù ca | 2 người nhận | Test 5 concurrent; DB lock bắt buộc |
