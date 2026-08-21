---
phase: 9
title: "Sprint 8 — Đóng băng và bảo vệ"
status: pending
priority: P1
effort: "18 person-days (blocker fixes only)"
dependencies: [8]
---

# Phase 9: Sprint 8 — Đóng băng và bảo vệ

## Overview

**Mục tiêu:** mã đóng băng; demo 10 phút thành phản xạ.

**Chỉ sửa lỗi mức chặn** (2 người duyệt mỗi fix).

## Requirements

- Functional: demo script §15 ổn định; offline fallback
- Non-functional: tag `v1.0.0-final`; `make demo` trên 3 máy (1 sạch); ≥5 lần demo liên tiếp không lỗi, ≥2 offline

## Architecture

Freeze `main` / `release/final`. Cherry-pick chỉ hotfix. Bộ dữ liệu demo cố định + `demo-reset` <10s.

## Related Code Files

- Create: frozen demo seed, offline fixture pack
- Modify: blocker hotfixes only
- Delete: —

## Implementation Steps

| Work | Person-days |
|------|-------------|
| Freeze + blocker reserve | 6,0 |
| Demo drill ×≥5 có đồng hồ + giám khảo giả | 4,0 |
| Demo dataset + offline plan §15 | 2,0 |
| Slide/docs/bảng kết quả bản cuối | 3,0 |
| `make demo` trên 3 máy | 1,0 |
| Buffer trống cố ý | 2,0 |

1. Tag `v1.0.0-final` + Docker image từ đúng tag
2. Mỗi thành viên chạy **toàn bộ** demo một mình
3. `/ak:ship` final; `ak plan check` phase 9; `ak plan close`; `/ak:retro` kết thúc dự án
4. Backlog Lô 2 → plan mới sau (không nhét vào đây)

## AgentKit commands

```text
/ak:ship
/ak:docs          # bản cuối
/ak:journal
/ak:retro
ak plan check ./plans/.../phase-09-*.md
ak plan close <id>
ak plan archive <id>
make demo && make demo-reset
```

## Todo

- [ ] Tag `v1.0.0-final`; `main` xanh; demo máy sạch
- [ ] Demo ×5 liên tiếp OK; ≥2 offline
- [ ] Mọi thành viên chạy demo solo
- [ ] Hồ sơ nộp đủ: mô tả HT, video, slide, link code, THIRD_PARTY, bảng kết quả
- [ ] Plan AgentKit đóng/archive

## Success Criteria

- [ ] Cổng ra sprint 8 — 4 điều kiện §14.9
- [ ] Outcome brainstorm đạt: bảo vệ được với bằng chứng đo, không chuyện bịa

## Risk Assessment

| Risk | Signal | Response |
|------|--------|----------|
| Demo phụ thuộc mạng | Fail offline drill | Bật chế độ offline fixtures ngay |
| Hotfix lớn muộn | Diff > blocker | Hoãn fix không-blocker; ghi known issue |
