# ADR-016 — Grand AI Experience boundary

## Status
Accepted (plan 260920-1442, Phase 01)

## Context
NHỊP QUÁN cần một bề mặt trải nghiệm AI riêng (portfolio) đứng bên ngoài các
màn hình vận hành hiện tại: War Room, Shift Rescue, Quán tự viết luật, HỒN
QUÁN Spatial Memory, QUÁNVERSE. Trước đây mọi AI quấn vào copilot/ops.

## Decision
- **Product boundary:** bề mặt mới sống trong Next.js hiện tại tại `/quanverse`
  + `apps/web/src/ui/experience/` + router API versioned dưới `apps/api`.
  Đọc dữ liệu NHỊP QUÁN qua `ExperienceReadAdapter` (protocol) — KHÔNG import
  DB internals hay mutate lifecycle hiện có trực tiếp.
- **AI boundary:** LLM chỉ lo ngôn ngữ/giọng nói. Retrieval, scoring,
  simulation, policy, permission, consent, audit, writes thuộc deterministic
  services.
- **Action boundary:** mọi mutation là `ExperienceActionProposal` trước; cần
  human confirm đã verify trước khi đổi roster/rules/memories/preferences/modes.

## Consequences
- Portfolio đọc-side không thể phá vỡ ops hiện có; rollback = tắt feature flag.
- Phase 02-06 có thể phát triển song song sau khi Phase 01 contracts merge.
- Một tương lai tách `apps/experience` runtime là optional, không đổi contracts.

## Links
- `docs/architecture-grand-ai-experience.md`
- `packages/contracts/src/ca_contracts/grand_experience.py`
- ADR-002 (tất định), ADR-008 (con người quyết định)