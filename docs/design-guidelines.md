# NHỊP QUÁN — Design Guidelines v3 (Premium Ops)

**Authority for all `apps/web` work.**

## Product

Cafe ops PWA — register **Product Premium**: studio-grade trên shell/hub/login; utilitarian trên phiếu/roster.

## Dials

| Dial | Hub/Login | Ops (phiếu, roster) |
|------|-----------|---------------------|
| DESIGN_VARIANCE | 5 — bento, motif | 3 — lưới đều |
| MOTION_INTENSITY | T2 editorial / T1 ambient | T0 functional |
| VISUAL_DENSITY | 7 — glass, glow | 6 — hairline |

## Color & motif

Atmosphere: **đêm quán / đồng / gỗ cháy** — grain overlay 4%, steam-line pattern, accent copper `#c4a574` with OKLCH hover drift.

## Layout

- `--nq-max`: `min(1200px, 100%)` desktop hub; mobile 1 cột
- Bento grid 12-col trên `/hom-nay`
- Progressive disclosure: hero = human line; technical (solver, raw state) = drawer

## Disclosure rules

- Login: **không** in credential trên UI prod — runbook `docs/runbook-demo.md`
- Hub: một dòng hero; meta có `nguồn quán` (e2e); solver trong drawer

## Motion tiers

T0 160ms · T1 220ms · T2 480ms · `prefers-reduced-motion` tắt animation

## Kit (`src/ui/kit.tsx`)

`EditorialBanner`, `BentoTile`, `TechnicalDrawer`, `Loading`/skeleton, `BtnLink`, `PageActions`

## Changelog

- 2026-08-23 — v3 Premium Ops (international studio bar, bento, disclosure, motif)
