# 2026-08-27 — Auth width + form contrast

## What broke
Login/register looked ~480px narrow; native `<select>` opened white/grey with cream ink; Alert used red text on dark surface — unreadable on /tkb and auth.

## Root cause
`.nq-login-card { max-width: 480px }` overrode Tailwind `max-w-4xl/5xl`. No global `select`/`option`/`color-scheme` theme. Alert set `color: red` on `bg-surface`.

## Fix
Widen login card; `color-scheme: dark` + themed inputs/selects/options; Alert cream-on-tinted; toast ink-on-solid kept on danger/ok.

## Verify
`npm run typecheck` green. Hard-refresh `/login`, `/dang-ky`, `/tkb` select list.
