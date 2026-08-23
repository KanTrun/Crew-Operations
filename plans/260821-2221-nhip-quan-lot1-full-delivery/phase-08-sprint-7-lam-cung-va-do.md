---
phase: 8
title: "Sprint 7 — Làm cứng và đo"
status: pending
blocked_reason: "Cổng §14.8 cần đo tại quán + 215 tests + 0 bug mở. Cấm feature mới. Không đánh dấu xong."
priority: P1
effort: "18 person-days (no new features)"
dependencies: [7]
---

# Phase 8: Sprint 7 — Làm cứng và đo

## Overview

**Mục tiêu:** mọi số trong hồ sơ là số đo được; sửa lỗi từ 2 tuần quán dùng thật.

**Cấm:** tính năng mới. Sức chứa 18 ngày người chỉ harden + measure + phản biện.

## Requirements

- Functional: — (không thêm feature)
- Non-functional: 165→215 tests; domain branch coverage >90%; 12 số §18.2; solver regression; light load; 20 câu phản biện chéo

## Architecture

Không đổi kiến trúc. Ưu tiên nhánh lỗi, biên, fail-closed paths.

## Related Code Files

- Create: tests biên, charts tỉ lệ không-cần-sửa theo tuần
- Modify: bugfix only
- Delete: dead code nếu an toàn

## Implementation Steps

| Work | Who | Days |
|------|-----|------|
| Tests → 215 (error/edge) | A,B,C,D | 2,0 mỗi |
| Fix bugs từ quán | A,B,C,D | 1,5 mỗi |
| Đo + vẽ 12 số §18.2 | A,D | 1,0 mỗi |
| Solver regression + light load | A,B | 1,0 mỗi |
| Luyện 20 câu §17 (hỏi chéo) | Chung | 1,0 |

1. `/ak:test` coverage drive
2. `/ak:fix` từng bug mức chặn/nặng
3. `/ak:security-scan` lần 2
4. `/ak:retro` sâu trước S8 freeze

## AgentKit commands

```text
/ak:test
/ak:fix
/ak:security-scan
/ak:web-testing
/ak:journal
/ak:retro
# KHÔNG /ak:cook feature mới
```

## Todo

- [ ] 215 tests xanh; domain branch >90%
- [ ] Đường cong tỉ lệ không-cần-sửa theo tuần (data thật)
- [ ] 12 số §18.2 có giá trị hoặc “chưa đo”+lý do
- [ ] 0 bug blocker/major mở
- [ ] Mỗi người trả lời 5 câu phản biện **không** phải phần mình

## Success Criteria

- [ ] Cổng ra sprint 7 — 5 điều kiện §14.8

## Risk Assessment

| Risk | Signal | Response |
|------|--------|----------|
| Lén thêm feature | PR có feat ngoài bug | Reject PR; đưa backlog Lô 2 |
| Thiếu data đường cong | Ít tuần dùng | Vẽ đúng tuần có data; ghi gap |
