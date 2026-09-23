---
phase: 8
title: "TÃ i liá»‡u, kiá»ƒm chá»©ng, commit"
status: completed
priority: P1
effort: "0.5 ngÃ y"
dependencies: [7]
---

# Phase 8: TÃ i liá»‡u, kiá»ƒm chá»©ng, commit

## Overview

Chá»‘t tÃ i liá»‡u, cháº¡y toÃ n bá»™ cá»•ng, vÃ  commit tá»«ng phase theo conventional commits.

## Requirements

- Functional: `docs/ui-surfaces.md` cáº­p nháº­t mÃ´ táº£ máº·t `waste`.
- Functional: `README.md` báº£ng endpoint cÃ³ `/api/v1/hao-hut` vÃ  intent `ANALYZE_LOSS`.
- Functional: ADR ghi quyáº¿t Ä‘á»‹nh "áº£nh sinh táº¡i mÃ¡y, khÃ´ng dÃ¹ng API áº£nh Ä‘Ã¡m mÃ¢y".
- Non-functional: cháº¡y háº¿t cá»•ng trÆ°á»›c khi commit cuá»‘i.
- Non-functional: commit khÃ´ng tham chiáº¿u AI; scope thuá»™c `commitlint.config.cjs`.

## Related Code Files

- Modify: `docs/ui-surfaces.md`
- Modify: `README.md`
- Create: `docs/adr/019-anh-san-pham-sinh-tai-may.md`
- Modify: `docs/THIRD_PARTY.md` (náº¿u phase 6 chÆ°a lÃ m)
- Modify: plan nÃ y (Ä‘Ã¡nh dáº¥u phase xong, cáº­p nháº­t `ak plan status`)

## Implementation Steps

1. Cáº­p nháº­t `ui-surfaces.md` + `README.md`.
2. Viáº¿t ADR-019 theo house style cÃ¡c ADR Ä‘Ã£ cÃ³ (Ä‘á»c 2 ADR gáº§n nháº¥t trÆ°á»›c Ä‘á»ƒ theo máº«u).
3. Cháº¡y chuá»—i cá»•ng: `ruff check apps/api/src packages scripts` â†’ `pytest` â†’
   `npm run lint` trong `apps/web` â†’ `npm run build` â†’ `npm run test:e2e`.
4. Kiá»ƒm `make contracts` khÃ´ng drift.
5. Commit tá»«ng phase (náº¿u chÆ°a commit á»Ÿ tá»«ng phase) báº±ng thÃ´ng Ä‘iá»‡p tiáº¿ng Viá»‡t qua
   `git commit -F <file>` (trÃ¡nh mojibake PowerShell â€” xem memory repo).
6. Cáº­p nháº­t tráº¡ng thÃ¡i phase trong plan; cháº¡y `ak plan status` Ä‘á»ƒ Ä‘á»‘i chiáº¿u.

## Success Criteria

- [ ] `ruff check apps/api/src packages scripts` sáº¡ch.
- [ ] `pytest` xanh toÃ n bá»™.
- [ ] `cd apps/web; npx tsc --noEmit` sáº¡ch.
- [ ] `npx next build` thÃ nh cÃ´ng, route `/hao-phi` cÃ³ trong output.
- [ ] e2e xanh (hoáº·c nÃªu rÃµ spec nÃ o Ä‘á» vÃ  vÃ¬ sao, kÃ¨m báº±ng chá»©ng).
- [ ] `make contracts` láº§n hai khÃ´ng Ä‘á»•i file nÃ o.
- [ ] `git log` cÃ³ commit cho tá»«ng phase, Ä‘Ãºng conventional commit + scope há»£p lá»‡.
- [ ] `docs/adr/019-*.md` tá»“n táº¡i vÃ  nÃªu rÃµ lÃ½ do chá»n sinh áº£nh táº¡i mÃ¡y.

## Risk Assessment

Rá»§i ro: e2e cáº§n `next build` + hai webServer; mÃ¡y dev khÃ´ng cÃ³ `py` launcher
(Ä‘Ã£ ghi trong memory repo). **TÃ­n hiá»‡u:** playwright config há»ng á»Ÿ bÆ°á»›c dá»±ng server.
**Pháº£n á»©ng:** cháº¡y thá»§ cÃ´ng `demo_api.py` rá»“i Ä‘á»ƒ playwright tÃ¡i dÃ¹ng cá»•ng, hoáº·c
nÃªu rÃµ giá»›i háº¡n mÃ´i trÆ°á»ng kÃ¨m báº±ng chá»©ng thay vÃ¬ tuyÃªn bá»‘ "Ä‘Ã£ xanh".

