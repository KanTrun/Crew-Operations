# 2026-08-22 — Phase-03 Sprint 2 cook (--auto)

## What
Delivered mốc sinh tử solver: CP-SAT 25×21, independent verify TOTAL 0, VF×3, AG-TKB metric with blur, roster UI, Alembic skeleton.

## Evidence
- `make bench`: OPTIMAL ~0.1s, verify_hard all c01–c06 = 0
- 67 pytest; ruff clean
- AG-TKB replay: 50/51 (1 blur counted incorrect) → docs/metrics-18-2.md
- PR: https://github.com/KanTrun/CA-CONG-BANG/pull/6

## Lesson
`git add -A` pulled `.claude/` with a fake Slack token in a skill test → push protection. Keep `.claude/` gitignored; never stage skill caches.
