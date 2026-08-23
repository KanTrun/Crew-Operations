# NHỊP QUÁN — Design Guidelines

**Authority for all `apps/web` work.**

## Product

Cafe ops PWA — không marketing landing làm surface chính.

## Motion tiers

| Tier | Duration | Dùng cho |
|------|----------|----------|
| T0 Functional | 150–180ms | Input, phiếu CTA, roster |
| T1 Ambient | 180–280ms | Skeleton, tile reveal, nav |
| T2 Editorial | 300–600ms | Banner hub, login |

`prefers-reduced-motion: reduce` → tắt animation không cần thiết.

## Color tokens

Atmosphere: đêm quán / gỗ cháy — `--nq-bg`, `--nq-accent`, `--nq-accent-soft`, `--nq-glow`.

## Shared kit

`src/ui/kit.tsx` — EditorialBanner, Loading/Skeleton, BtnLink, ProgressBar.

## Changelog

- 2026-08-23 — Full UI redesign wave 0–3 (motion tiers, kit v2, skeleton load)
