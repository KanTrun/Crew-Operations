---
title: Brainstorm kênh tin + Facebook page
date: 2026-08-27
status: accepted
---

# Brainstorm — Duyệt Phase 1+2

## Summary

User confirmed both staff messaging loop (Telegram→inbox→ca/lịch) and Facebook page management. Correct ops order: close AG-MSG pipeline first; Facebook as separate `/page-quan` surface with replay before Meta connect.

## Contract

See `plans/260827-1438-kenh-tin-telegram-zalo-va-facebook-page/plan.md`.

## Evidence

- MessagePort outbound stubs only (`messaging.py`)
- AG-MSG classify exists; does not enqueue or mutate schedule
- `/inbox` = constraints only
- No Facebook code in repo

## Recommendation executed into plan

7 phases; Phase 6 parallelizable after Phase 1; Phase 7 gated on real page.
