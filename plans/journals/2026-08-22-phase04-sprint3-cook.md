# 2026-08-22 — Phase-04 Sprint 3 cook (review repair)

## What
Phase-03 already on `main` (`c6a2284`). Sprint 3 lives on `feat/ops-sprint3-van-hanh` (uncommitted). After review, idempotency is locked, nha/nhan mutate `_ASSIGN`, photos require `data:image`, timing is keyed by step `ma`, AG-MSG 200/200 is disclosed as keyword-on-template, staff UI no longer injects a default fixture token.

## Evidence
- 38 pytest in api/opsengine/agents/playbook; ruff clean on touched Python
- Concurrent `IdempotencyStore.once` → one `fn` run
- `/orc/dispatch` writes=8 then replay; manager token required
- Gate 1 (phone thật) is software-ready, not CI-proven

## Lesson
Tests that only assert JSON shape will green-light fabricated `so_lan_sua` and empty-photo fallbacks. Assert mutation and reject empty evidence.
