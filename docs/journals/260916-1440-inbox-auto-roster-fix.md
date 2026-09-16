---
title: Inbox approval and automatic weekly roster fix
date: 2026-09-16
branch: fix/inbox-constraints-auto-roster
---

# Inbox approval and automatic weekly roster fix

## Context

Managers could click **Duyệt ràng buộc** after scrolling but not see its confirmation modal. Approving a schedule constraint also only persisted the constraint; it did not rerun the weekly solver.

## What happened

- `.nq-page` retains a transform from its entry animation, so fixed modal descendants used the long page as their containing block and could render outside the viewport.
- Inbox modals now render through React portals on `document.body`.
- Schedule-affecting approvals now offer an explicit, default-on automatic CP-SAT run.
- Solver responses report dynamic day-by-time cell coverage and successful runs return the lifecycle to `cho_duyet`.
- Published or closed schedules remain locked; infeasible runs preserve the existing assignment.

## Reflection

Changing backdrop color could not fix the positioning defect. Reproducing from a scrolled Inbox item exposed the transformed-containing-block behavior. Schedule automation also needed lifecycle guards because convenience must not silently rewrite a published roster.

## Decisions

- Keep automatic scheduling visible and reversible through the confirmation checkbox.
- Count the 21 UI cells from solver metadata instead of hard-coding success.
- Preserve the old schedule unless CP-SAT returns a valid solution.

## Next

- Managers review and publish the generated roster from `/roster`.
- Verification completed: 14 Inbox/solver tests, 36 broader related tests, Ruff, TypeScript typecheck, production build, and browser checks passed.
