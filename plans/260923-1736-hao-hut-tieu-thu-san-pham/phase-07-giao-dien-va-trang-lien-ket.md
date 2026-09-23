---
phase: 7
title: "Giao diá»‡n & trang liÃªn káº¿t"
status: completed
priority: P1
effort: "1 ngÃ y"
dependencies: [6]
---

# Phase 7: Giao diá»‡n & trang liÃªn káº¿t

## Overview

Dá»±ng láº¡i `/hao-phi` thÃ nh mÃ n hao há»¥t hoÃ n thiá»‡n, vÃ  **ná»‘i cÃ¡c trang Ä‘ang liÃªn
quan** Ä‘á»ƒ ngÆ°á»i dÃ¹ng Ä‘i Ä‘Æ°á»£c tá»« hao há»¥t sang tiÃªu thá»¥, menu, hÃ´m nay, báº£n Ä‘á»“ há»‡ thá»‘ng.

## Requirements

- Functional: báº£ng hao há»¥t theo nguyÃªn liá»‡u â€” lÃ½ thuyáº¿t, thá»±c táº¿, lá»‡ch, tá»· lá»‡, má»©c Ä‘á»™.
- Functional: xáº¿p háº¡ng nguyÃªn nhÃ¢n; dÃ²ng nÃ o `thieu_du_lieu` pháº£i nÃ³i rÃµ **thiáº¿u váº¿ nÃ o**.
- Functional: vÃ¹ng há»i agent máº¹ (AG-COPILOT) ngay trÃªn trang, gá»­i `ANALYZE_LOSS`.
- Functional: giá»¯ nguyÃªn kháº£ nÄƒng ghi ghi chÃº hao há»¥t (khÃ´ng bá» tÃ­nh nÄƒng cÅ©).
- Non-functional: má»i mÃ£ tráº¡ng thÃ¡i Ä‘i qua `present.ts`; khÃ´ng in mÃ£ thÃ´, khÃ´ng `[object Object]`.
- Non-functional: má»i lá»—i Ä‘i qua `viError()`; dÃ¹ng kit (`OpsCard`, `PageHeader`, `StatusChip`).
- Non-functional: token mÃ u/bo gÃ³c/bÃ³ng theo `docs/design-guidelines.md`; T0 cho route ops.
- Non-functional: e2e hiá»‡n cÃ³ cho `/hao-phi` (heading "Hao phÃ­") **khÃ´ng Ä‘Æ°á»£c vá»¡**.

## Architecture

Trang má»›i gá»“m bá»‘n khá»‘i, thá»© tá»± Ä‘á»c tá»« trÃªn xuá»‘ng:

```text
/hao-phi
  1. PageHeader            â€” kicker nÃ³i rÃµ Ä‘ang xem gÃ¬
  2. OpsCard "Hao há»¥t theo nguyÃªn liá»‡u"   â† báº£ng má»›i (tá»« GET /api/v1/hao-hut)
  3. OpsCard "NguyÃªn nhÃ¢n láº·p láº¡i"        â† xáº¿p háº¡ng (cÃ¹ng payload)
  4. OpsCard "Ghi chÃº trong ca"           â† giá»¯ form + cá»¥m cÅ© (GET/POST /api/v1/waste)
  5. VÃ¹ng há»i agent                        â† gá»­i intent ANALYZE_LOSS
```

Ná»‘i trang: `/tieu-thu` vÃ  `/menu` trá» sang `/hao-phi`; `/hom-nay` thÃªm tháº» hao há»¥t;
`/huong-dan/map-data.ts` cáº­p nháº­t mÃ´ táº£ `/hao-phi`.

## Related Code Files

- Modify: `apps/web/src/app/hao-phi/page.tsx`
- Modify: `apps/web/src/app/tieu-thu/page.tsx` (liÃªn káº¿t sang hao há»¥t)
- Modify: `apps/web/src/app/menu/page.tsx` (liÃªn káº¿t sang hao há»¥t)
- Modify: `apps/web/src/app/hom-nay/page.tsx` (tháº» hao há»¥t)
- Modify: `apps/web/src/app/huong-dan/map-data.ts`
- Modify: `apps/web/src/lib/present.ts` (nhÃ£n `LossLevel`, `LossBasis`, nguyÃªn nhÃ¢n má»›i)
- Modify: `apps/web/src/app/AppShell.tsx` náº¿u cáº§n Ä‘á»•i nhÃ£n nav (giá»¯ `/hao-phi`)
- Create: `apps/web/e2e/hao-hut.spec.ts`

## Implementation Steps

1. ThÃªm nhÃ£n tiáº¿ng Viá»‡t cho `LossLevel`/`LossBasis` vÃ o `present.ts` (theo máº«u `NGUYEN_NHAN`).
2. Dá»±ng láº¡i `hao-phi/page.tsx`: gá»i `GET /api/v1/hao-hut`, render báº£ng + xáº¿p háº¡ng.
3. Giá»¯ khá»‘i ghi chÃº cÅ© nguyÃªn chá»©c nÄƒng; Ä‘áº·t xuá»‘ng dÆ°á»›i báº£ng má»›i.
4. ThÃªm vÃ¹ng há»i agent (theo máº«u cÃ¡c trang Ä‘Ã£ cÃ³ paner AG-COPILOT).
5. Ná»‘i `/tieu-thu`, `/menu`, `/hom-nay`, `/huong-dan`.
6. Viáº¿t e2e `hao-hut.spec.ts`: báº£ng hiá»‡n, dÃ²ng thiáº¿u dá»¯ liá»‡u nÃ³i Ä‘Ãºng, khÃ´ng cÃ³ `[object Object]`.
7. Cháº¡y `tsc --noEmit`, `next build`, e2e cÅ©.

## Success Criteria

- [ ] `npm run lint` (tsc) sáº¡ch.
- [ ] `/hao-phi` hiá»ƒn thá»‹ báº£ng hao há»¥t theo nguyÃªn liá»‡u vá»›i sá»‘ tháº­t tá»« API.
- [ ] DÃ²ng `thieu_du_lieu` nÃ³i rÃµ thiáº¿u váº¿ nÃ o (lÃ½ thuyáº¿t hay thá»±c táº¿).
- [ ] Má»i mÃ³n á»Ÿ `/menu` hiá»‡n áº£nh (khÃ´ng rÆ¡i vá» chá»¯ cÃ¡i Ä‘áº§u).
- [ ] `/tieu-thu` â†’ `/hao-phi` vÃ  `/menu` â†’ `/hao-phi` báº¥m Ä‘Æ°á»£c.
- [ ] e2e `/hao-phi` cÅ© (flows.spec.ts) váº«n xanh; e2e má»›i xanh.
- [ ] KhÃ´ng cÃ³ `[object Object]` hay mÃ£ tráº¡ng thÃ¡i thÃ´ trÃªn UI.

## Risk Assessment

Rá»§i ro: e2e `flows.spec.ts` assert `getByRole("heading", { name: /Hao phÃ­/i })`.
**TÃ­n hiá»‡u:** test Ä‘á» vÃ¬ tiÃªu Ä‘á» Ä‘á»•i. **Pháº£n á»©ng:** giá»¯ tá»« "Hao phÃ­" trong tiÃªu Ä‘á»
chÃ­nh vÃ  kicker; náº¿u buá»™c Ä‘á»•i thÃ¬ sá»­a Ä‘Ãºng má»™t dÃ²ng test kÃ¨m lÃ½ do, khÃ´ng ná»›i lá»ng
assertion.

