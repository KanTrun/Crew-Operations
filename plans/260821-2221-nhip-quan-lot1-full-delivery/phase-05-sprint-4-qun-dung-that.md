---
phase: 5
title: "Sprint 4 — Quán dùng thật"
status: in-progress
priority: P1
effort: "18 person-days"
dependencies: [4]
---

# Phase 5: Sprint 4 — Mốc sinh tử thứ hai (quán dùng thật)

## Overview

**Mục tiêu:** quán dùng thật — lịch tuần và phiếu mở quán do hệ thống quản lý.

**Chiếu được:** screenshot phone NV thật + lịch tuần đang hiệu lực tại quán.

## Requirements

- Functional: anti-fake checklist signals; reason codes; VF-CONFLICT/NUM; schedule lifecycle; background solver; publish+ICS; AG-HANDOVER; constraints inbox; fairness board; today board
- Non-functional: append-only audit log; ADR-008/009

## Architecture

Vòng đời lịch: nháp → đang giải → chờ duyệt → đã công bố → đã đóng. Người là trọng tài khi VF-CONFLICT.

## Related Code Files

- Create: anti-fake detectors, `vf_conflict`, `vf_num`, `ag_handover/`, fairness/today/PDF features, agent-trace UI p1
- Modify: schedule publish APIs, Excel import p2, stock thresholds in templates
- Delete: —

## Implementation Steps

| Who | Work | Days |
|-----|------|------|
| A | Anti-fake + signals; reason codes; VF-CONFLICT; VF-NUM | 4,5 |
| B | Lifecycle lịch; solver job; publish+ICS; audit log | 4,5 |
| C | AG-HANDOVER; inbox UI/API; Excel p2; thresholds; golden×3 + `make eval` | 4,5 |
| D | Fairness board; today board; fairness PDF; agent-trace p1; a11y | 4,5 |

1. Công bố 1 lịch tuần thật; NV nhận tin
2. ≥5 phiếu thật bởi NV quán (không phải đội)
3. Cuối sprint: kiểm đã có ≥1 mẫu ≥3 lần sửa cùng pattern cho S5

## AgentKit commands

```text
/ak:cook
/ak:ship          # cẩn thận merge khi quán đang dùng
/ak:fix          # nếu blocker sản xuất
/ak:journal       # ghi sự cố người/quán
make eval
```

## Todo

- [x] Lịch tuần công bố + tin (ICS + lifecycle fixture; tin = console/Telegram stub)
- [ ] ≥5 phiếu thật (NV quán — **chưa có đối tác**)
- [x] Audit log đủ vết đổi lịch (append-only `data/out/audit.jsonl`)
- [x] Inbox ≥10 approve/reject (fixture, dán nhãn)
- [x] Case VF-CONFLICT (dựng: hai claim, không tự chọn)
- [x] Đủ dữ liệu mẫu cho AG-RULE trên **dựng lại** (0 luật quán thật)

## Success Criteria

- [ ] Cổng ra sprint 4 — 6 điều kiện §14.5 (mốc sinh tử 2)

## Risk Assessment

| Risk | Signal | Response |
|------|--------|----------|
| Quán không đổi giữa tuần | 0 phiếu thật | Lùi; chạy 1 ca thử; không fake screenshot |
| Thiếu mẫu sửa | <3 cùng pattern | Báo ngay đóng sprint; chuẩn bị narrative trung thực S5 |
