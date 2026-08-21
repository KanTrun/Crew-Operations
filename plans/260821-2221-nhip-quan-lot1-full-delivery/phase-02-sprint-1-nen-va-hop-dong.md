---
phase: 2
title: "Sprint 1 — Nền và hợp đồng"
status: pending
priority: P1
effort: "17.25 person-days"
dependencies: [1]
---

# Phase 2: Sprint 1 — Nền và hợp đồng

## Overview

**Mục tiêu:** từ cuối tuần 1, không ai bị chặn bởi ai.

**Chiếu được:** máy trống → `git clone && make demo` → trang đăng nhập + mock server đủ 5 contracts. Chưa có tính năng thật.

## Requirements

- Functional: monorepo, CI 11 cổng, 5 contracts + mock, seed data, agent runtime khung, Next PWA khung, 3 YAML thật
- Non-functional: ruff/mypy strict/eslint; `packages/*` thuần; sức chứa ≤4,5 ngày/người

## Architecture

Cây §11.1. Contracts là nguồn sự thật; OpenAPI → TS client cho D. ADR-001/002/003 merged.

## Related Code Files

- Create: `apps/api`, `apps/web`, `packages/{contracts,solver,gates,opsengine,playbook,agents}`, `infra/docker`, `Makefile`, `.github/workflows`
- Modify: contracts schemas
- Delete: —

## Implementation Steps

| Who | Work | Days |
|-----|------|------|
| A | Seed 25/21/8; nửa domain+policy; solver khung + 6 ràng buộc cứng | 4,25 |
| B | Monorepo toolchains; CI 11 cổng; 5 contracts + mock | 4,0 |
| C | Thu+gán nhãn dataset; agent runtime + versioned prompts + content cache | 4,0 |
| D | Next PWA + design system + OpenAPI client; đo hiện trạng; 3 YAML | 4,0 |
| Chung | Buổi chốt contracts + 3 ADR (2h×4) | 1,0 |

1. `/ak:cook` theo vùng nhánh `feat/api-*`, `feat/solver-*`, `feat/agents-*`, `feat/web-*`, `feat/tpl-*`
2. `make contracts && make demo` trên 4 máy
3. Merge chỉ qua PR + CODEOWNERS
4. `/ak:retro` cuối sprint trước khi mở S2

## AgentKit commands

```text
/ak:cook --parallel   # A/B/C/D theo CODEOWNERS
/ak:devops            # hoàn thiện 11 CI gates
/ak:databases         # nếu cần stub schema sớm
# === UI/UX BẮT BUỘC (người D) ===
/ak:ui-ux-pro-max "NHIP QUAN cafe ops PWA shell + design tokens"
/ak:frontend-design   # dials 3/2/6 Product — follow docs/design-guidelines.md
/ak:frontend-development
/ak:web-testing
/ak:test              # schema tests cho contracts
ak plan status
```

## Todo

- [ ] 5 contracts trên `main` + schema tests
- [ ] CI 11 cổng xanh `main` + PR thử
- [ ] `make demo` trên 4 máy
- [ ] ADR-001, 002, 003 merged
- [ ] 3 YAML từ quán thật (không bịa)

## Success Criteria

- [ ] Cổng ra sprint 1 — đủ 5 điều kiện §14.2
- [ ] Không còn blocker “chờ người khác” cho S2

## Risk Assessment

| Risk | Signal | Response |
|------|--------|----------|
| YAML bịa | D không ngồi được ca thật | Dùng quán dự bị; **chặn** cổng ra S1 |
| CI chưa đủ 11 | PR không bị chặn đúng | Không mở S2 cho tới khi PR thử bị chặn đúng kỳ vọng |
