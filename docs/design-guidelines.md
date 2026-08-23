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

`EditorialBanner`, `BentoTile`, `TechnicalDrawer`, `PageHeader`, `Btn`, `TabBar`, `OpsCard`, `FixedBottomBar`, `StatusChip`, `Loading`/skeleton, `BtnLink`, `PageActions`

## Two-register sweep (v3.1)

| Register | Routes | Motion |
|----------|--------|--------|
| **Premium hub** | `/`, `/login`, `/hom-nay` | T1–T2 editorial |
| **Ops utilitarian** | all other authenticated routes | T0 functional, shared kit |

## Typography — self-host, không CDN

Font nạp qua `next/font` trong `apps/web/src/ui/fonts.ts`, **không** dùng
`<link>` tới `fonts.googleapis.com`.

| Vai trò | Font | Subset |
|---|---|---|
| Display | Fraunces 400/600 | latin, latin-ext, **vietnamese** |
| Body | Source Sans 3 400/600 | latin, latin-ext, **vietnamese** |
| Mono | IBM Plex Mono 400/500 | latin, latin-ext |

Hai lý do, cả hai đều là ràng buộc cứng:

1. **Cổng ra Sprint 8 (§14.9)** yêu cầu demo chạy trọn 10 phút khi đã rút mạng.
   Font CDN làm chữ rơi về Georgia/system-ui ngay giữa buổi bảo vệ.
2. **Phải có subset `vietnamese`.** Thiếu nó thì chữ có dấu render bằng font
   fallback, và cả trang trông chắp vá dù token màu/khoảng cách vẫn đúng.

Kiểm lại sau mỗi lần đổi font:

```
cd apps/web ; npx next build
# .next/static/media phải có file .woff2
# HTML đã render phải có 0 tham chiếu fonts.googleapis / fonts.gstatic
```

## Icon

`apps/web/src/ui/icons.tsx` — SVG inline, 24×24, `currentColor`, stroke 1.5.
Không thêm dependency icon, không dùng emoji (xem mục cấm). Icon mang
`aria-hidden` vì nhãn chữ luôn đi kèm; `iconForHref()` suy icon từ route.

## Changelog

- 2026-08-23 — Font self-host qua `next/font` (+ subset vietnamese) sửa cổng demo offline; bộ icon SVG inline cho nav + thanh dưới; skip-link; `<main id="nq-content">`; `viewport.maximumScale=5` để không chặn zoom
- 2026-08-23 — v3.1 full-site sweep: PageHeader/Btn/TabBar on all 19 routes; phieu run-form + roster table CSS
- 2026-08-23 — v3 Premium Ops (international studio bar, bento, disclosure, motif)
