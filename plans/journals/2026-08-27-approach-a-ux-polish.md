---
title: Approach A UX polish
date: 2026-08-27
summary: "System-level contrast, cursor, auth, and layout fixes across apps/web after Duyệt A."
---

# Approach A UX polish

## What happened
Approach A for NHIP QUAN web UX: copper/yellow solid fills had unreadable light text (global `a { color: accent }`), laggy custom cursor, tall auth column, bento tiles hugging left, and cramped summary spacing.

Post-review: `.nq-ink-on-solid { color: !important }` trapped hover invert (ink on dark bg). Five ops pages double-padded inside AppShell.

## Decision
Dropped `!important`; scoped ink via `a.nq-ink-on-solid, button.nq-ink-on-solid`. Removed nested page padding. Restored e2e hooks (`.nq-bento-tile`, `.nq-summary-n`) without resurrecting dead layout CSS. Deleted CustomCursor. Playwright contrast spec added (needs local browsers).

## Next steps
Hard-refresh localhost:3000. Commit if wanted. Run `npx playwright install` then contrast e2e.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
