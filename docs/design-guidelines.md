# NHỊP QUÁN — Design Guidelines v4 (Enterprise / Awwwards)

**Authority for all `apps/web` work.** Branch reference: `redesign/enterprise-ui-v3`.

## Product

Cafe ops PWA — **Product Premium** on hub/login/showcase; **utilitarian density** on phiếu/roster/ops. Same tokens, different motion intensity.

## References (2025–2026)

Dark-first SaaS (Linear, Vercel, Stripe, Raycast): true-grey/teal-black surfaces, single accent, hairline borders, high information density, motion that clarifies state (≤320ms on ops). Avoid card-spam, rainbow gradients, emoji chrome, glass-on-glass.

## Dials

| Dial | Hub/Login/Showcase | Ops (phiếu, roster) |
|------|--------------------|---------------------|
| DESIGN_VARIANCE | 5 — bento, editorial type | 3 — lưới đều |
| MOTION_INTENSITY | T2 chapter / T1 ambient | T0 ack / T1 settle |
| VISUAL_DENSITY | 6 — grain, soft glow | 7 — compact, hairline |

## Color

Atmosphere: **đêm quán / xanh đen + vàng gold** — grain ~4%, gold hairline, accent scale `--nq-accent-50..900`.

| Token | Role |
|-------|------|
| `--nq-bg` `#070d12` | Page floor |
| `--nq-surface` / `-2` / `-3` | Panel elevation ladder |
| `--nq-accent` (`--nq-accent-500` `#b8942f`) | CTA / brand fill — muted gold, not neon |
| `--nq-accent-ink-text` | Small brand text on dark |
| `--nq-st-*` | Status only (ok/warn/danger/info) — never brand |

Aliases: `--nq-panel` → surface, `--nq-border` → line. No copper/teal brand leftovers.

## Z-index scale

`--nq-z-sticky` 20 · `--nq-z-header` 40 · `--nq-z-dropdown` 50 · `--nq-z-drawer` 200 · `--nq-z-modal` 400 · `--nq-z-toast` 500 · `--nq-z-tour` 600.

Do **not** invent `z-[…]` in TSX.

## Layout

- `--nq-max`: `min(1600px, 100%)`
- 12-col grid; bento rhythm (uneven tile sizes) on hub
- Progressive disclosure: human line first; technical → `TechnicalDrawer`

## Shape & depth

| Token | Value | Where |
|---|---|---|
| `--nq-radius` | 6px | input, select, dense tables |
| `--nq-radius-bubble` | 18px | card, tile, alert, empty |
| `--nq-radius-pill` | 999px | button, tab, chip, nav |
| `--nq-radius-sheet` | 24px | large sheets |
| `--nq-elev-*` | layered cool shadows | elevation, not flat black |

Glass only on chrome (header/drawer/modal). Data surfaces stay solid.

## Motion

CSS beats: ack 120ms · settle 200ms · focus 320ms · chapter 560ms · ease `cubic-bezier(0.2, 0.8, 0.2, 1)`.

JS presets: `src/ui/motion/presets.ts` — single source. Prefer `transform`/`opacity` only. Respect `prefers-reduced-motion`.

Lenis smooth scroll: public routes only (`/`, `/huong-dan`). Ops keep native scroll for sticky tables.

## Disclosure rules

- No credentials on prod login UI
- JSON / VF codes / solver dumps → `TechnicalDrawer` (closed by default)
- Errors via `viError()` / `safeText()` — Vietnamese, no raw HTTP/JSON
- Status keys via `present.ts` / `labels.ts`

## Kit (`src/ui/kit.tsx`)

`Btn`, `Table`, `Badge`, `Dialog`, `Drawer`, `DataList`, `Empty`, `PageHeader`, `OpsCard`, `TechnicalDrawer`, `FixedBottomBar`, `Loading`/`Skeleton`, motion wrappers (`Reveal`, `Presence`).

## Typography — self-host

| Role | Font |
|---|---|
| Display | Space Grotesk |
| Body | IBM Plex Sans |
| Mono / numbers | IBM Plex Mono + `tabular-nums` |

No Google Fonts CDN. Vietnamese subsets required.

## Performance budgets

LCP < 2.5s · CLS < 0.05 · INP < 200ms · 60fps transitions · LazyMotion + dynamic 3D/Lenis.

## Roster / Lịch tuần grid

Calendar-dense week matrix (Deputy / When I Work / nurse roster), not chip collage.

- **Structure:** sticky day headers + sticky `Khung` column; stronger `--nq-line-strong` borders; 3 shift rows fill viewport (`--roster-rows`).
- **Cell hierarchy:** left status accent (ok/warn/empty) → count `Đủ · 4/4` → one-column crew names → `+N nữa`.
- **Names:** `shortNameOf()` — never take `(` as initial; role in parens stays intact (`Nam (pha chế)`); tooltip = full name. No 2-col micro chips.
- **Motion:** cell hover lift 1px + border; respect `prefers-reduced-motion`.
- **Narrow:** horizontal scroll under 860px — do not crush names.
- **E2E:** keep `.nq-roster-slot-btn` (21 cells when 3×7).
