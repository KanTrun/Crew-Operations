---
phase: 3
title: "Äá»™ng cÆ¡ hao há»¥t"
status: completed
priority: P1
effort: "0.5 ngÃ y"
dependencies: [2]
---

# Phase 3: Äá»™ng cÆ¡ hao há»¥t

## Overview

Cho AG-WASTE kháº£ nÄƒng **tÃ­nh** hao há»¥t theo nguyÃªn liá»‡u, khÃ´ng chá»‰ gom cá»¥m ghi chÃº.
ToÃ¡n táº¥t Ä‘á»‹nh, thuáº§n, unit-test Ä‘Æ°á»£c (ADR-002).

## Requirements

- Functional: tÃ­nh lÆ°á»£ng lÃ½ thuyáº¿t tá»« BOM Ã— sá»‘ mÃ³n Ä‘Ã£ bÃ¡n.
- Functional: so vá»›i lÆ°á»£ng thá»±c táº¿ tá»« `kiem_ke`; ra lá»‡ch, tá»· lá»‡, má»©c Ä‘á»™.
- Functional: xáº¿p háº¡ng nguyÃªn nhÃ¢n tá»« `waste_notes` theo máº·t hÃ ng.
- Functional: **gá»™p nguyÃªn liá»‡u theo `mat_hang`** Ä‘á»ƒ ná»‘i Ä‘Æ°á»£c BOM â†” kiá»ƒm kÃª â†” ghi chÃº.
- Non-functional: hÃ m thuáº§n, khÃ´ng I/O, khÃ´ng Ä‘á»c DB, khÃ´ng gá»i máº¡ng.
- Non-functional: thiáº¿u má»™t váº¿ â‡’ `LossLevel.thieu_du_lieu`, cÃ¡c trÆ°á»ng sá»‘ lÃ  `None`.

## Architecture

Ba hÃ m thuáº§n trong `ag_waste`, Äƒn khá»›p há»£p Ä‘á»“ng phase 2:

```text
loc_theo_mat_hang(rows)        -> dict[mat_hang, float]      # gá»™p nhiá»u dÃ²ng cÃ¹ng máº·t hÃ ng
tinh_ly_thuyet(ban_theo_mon, bom_theo_mon) -> dict[mat_hang, float]
so_hao_hut(ly_thuyet, thuc_te, nguong)     -> list[LossLine]
xep_hang_nguyen_nhan(notes)                -> list[LossCauseRank]
```

`so_hao_hut` lÃ  trÃ¡i tim: vá»›i má»—i máº·t hÃ ng xuáº¥t hiá»‡n á»Ÿ **má»™t trong hai** váº¿, sinh
má»™t `LossLine`. Máº·t hÃ ng chá»‰ cÃ³ má»™t váº¿ â‡’ sá»‘ cá»§a váº¿ kia lÃ  `None` â‡’ `thieu_du_lieu`.

NgÆ°á»¡ng: máº·c Ä‘á»‹nh tá»« config, cho phÃ©p ghi Ä‘Ã¨ theo máº·t hÃ ng.

## Related Code Files

- Modify: `packages/agents/src/ca_agents/ag_waste/extract.py`
- Modify: `packages/agents/src/ca_agents/ag_waste/__init__.py`
- Modify: `packages/agents/src/ca_agents/ag_waste/PHAM_VI.md` (khai nÄƒng lá»±c má»›i)
- Create: `packages/agents/tests/test_ag_waste_loss.py`
- Modify: `packages/agents/tests/test_ag_waste.py` (giá»¯ nguyÃªn test cÅ© â€” pháº£i cÃ²n xanh)

## Implementation Steps

1. Viáº¿t `loc_theo_mat_hang`, `tinh_ly_thuyet` â€” thuáº§n cá»™ng dá»“n, Ã©p `float`, bá» giÃ¡ trá»‹ â‰¤ 0.
2. Viáº¿t `so_hao_hut` â€” xá»­ lÃ½ bá»‘n nhÃ¡nh má»©c Ä‘á»™, `None` cho váº¿ thiáº¿u, giá»¯ `ty_le` Ã¢m.
3. Viáº¿t `xep_hang_nguyen_nhan` â€” Ä‘áº¿m theo `nguyen_nhan`, gom `mat_hang` liÃªn quan, sáº¯p giáº£m dáº§n.
4. Test: hai váº¿ Ä‘á»§; chá»‰ má»™t váº¿; cáº£ hai rá»—ng; Ä‘áº¿m dÆ° (lá»‡ch Ã¢m); vÆ°á»£t ngÆ°á»¡ng nghiÃªm trá»ng;
   hai dÃ²ng cÃ¹ng máº·t hÃ ng Ä‘Æ°á»£c gá»™p; ngÆ°á»¡ng riÃªng theo máº·t hÃ ng tháº¯ng ngÆ°á»¡ng máº·c Ä‘á»‹nh.
5. Cáº­p nháº­t `PHAM_VI.md`: thÃªm nhiá»‡m vá»¥ tÃ­nh hao há»¥t; giá»¯ nguyÃªn dÃ²ng "Cáº¥m".

## Success Criteria

- [ ] `pytest packages/agents -q` xanh, test `test_ag_waste.py` cÅ© váº«n xanh.
- [ ] KhÃ´ng hÃ m nÃ o cháº¡m I/O â€” kiá»ƒm báº±ng cÃ¡ch Ä‘á»c mÃ£, vÃ  test cháº¡y khÃ´ng cáº§n fixture DB.
- [ ] `so_hao_hut` vá»›i hai dict rá»—ng tráº£ `[]`, khÃ´ng raise.
- [ ] Máº·t hÃ ng thiáº¿u váº¿ cÃ³ `muc_do == thieu_du_lieu` vÃ  trÆ°á»ng sá»‘ lÃ  `None`.
- [ ] `ruff check packages/agents` sáº¡ch.

## Risk Assessment

Rá»§i ro: tÃªn máº·t hÃ ng khÃ´ng khá»›p giá»¯a ba nguá»“n (`sua_tuoi` á»Ÿ kiá»ƒm kÃª vs `sua_ml` á»Ÿ
BOM). **TÃ­n hiá»‡u:** dÃ²ng hao há»¥t ra `thieu_du_lieu` hÃ ng loáº¡t dÃ¹ dá»¯ liá»‡u cÃ³ tháº­t.
**Pháº£n á»©ng:** thÃªm báº£ng bÃ­ danh (`ALIAS`) trong `ag_waste` vÃ  test riÃªng cho nÃ³;
khÃ´ng tá»± Ä‘á»™ng fuzzy-match vÃ¬ fuzzy sáº½ ghÃ©p sai im láº·ng.

