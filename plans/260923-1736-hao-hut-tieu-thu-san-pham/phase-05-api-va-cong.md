---
phase: 5
title: "API & cá»•ng"
status: completed
priority: P1
effort: "0.5 ngÃ y"
dependencies: [4]
---

# Phase 5: API & cá»•ng

## Overview

Má»Ÿ bá» máº·t HTTP cho hao há»¥t, khai capability theo cá»•ng PR13, vÃ  vÃ¡ hai lá»— Ä‘Ã£ xÃ¡c
nháº­n á»Ÿ phase 1 (thiáº¿u audit, `worker` Ä‘á»c sai khoÃ¡ thá»i gian).

## Requirements

- Functional: `GET /api/v1/hao-hut` tráº£ `LossSummary` tá»« dá»¯ liá»‡u tháº­t.
- Functional: `POST /api/v1/hao-hut` ghi má»™t dÃ²ng hao há»¥t **cÃ³ audit**.
- Functional: `GET /api/v1/hao-hut/nguong` Ä‘á»c ngÆ°á»¡ng Ä‘ang Ã¡p dá»¥ng (Ä‘á»ƒ UI giáº£i thÃ­ch).
- Functional: vÃ¡ `worker._tong_ket_ngay` Ä‘á»c Ä‘Ãºng `luc`/`created_at`.
- Non-functional: quyá»n theo Ä‘Ãºng house style (`_require_role` / `_require_manager`).
- Non-functional: cá»•ng PR13 xanh â€” route má»›i pháº£i khai capability hoáº·c exclusion.

## Architecture

`GET` lÃ  hÃ m Ä‘á»c thuáº§n: gom ba nguá»“n â†’ gá»i engine con â†’ `LossSummary.model_dump()`.
`POST` dÃ¹ng `kv_mutate` theo máº«u `waste_ghi` nhÆ°ng **thÃªm** `_audit`.

```text
GET  /api/v1/hao-hut      â†’ dá»±ng map mat_hang â†’ engine â†’ LossSummary
POST /api/v1/hao-hut      â†’ chuáº©n hoÃ¡ + kv_mutate("waste_notes") + _audit
GET  /api/v1/hao-hut/nguong â†’ config/nguong-hao-hut.yaml Ä‘Ã£ resolve
```

Giá»¯ `POST/GET /api/v1/waste` cÅ© cháº¡y nguyÃªn váº¹n Ä‘á»ƒ UI cÅ© vÃ  e2e khÃ´ng vá»¡; `/hao-hut`
lÃ  bá» máº·t má»›i, Ä‘áº§y Ä‘á»§ hÆ¡n.

## Related Code Files

- Create: `apps/api/src/ca_api/interfaces/http/hao_hut.py`
- Modify: `apps/api/src/ca_api/interfaces/http/main.py` (gáº¯n router)
- Modify: `apps/api/src/ca_api/interfaces/http/sprint45.py` (thÃªm `_audit` cho `waste_ghi`)
- Modify: `apps/api/src/ca_api/worker.py` (`_tong_ket_ngay` Ä‘á»c Ä‘Ãºng khoÃ¡ thá»i gian)
- Modify: `packages/contracts/src/ca_contracts/__init__.py` (2 capability má»›i)
- Modify: `apps/api/tests/unit/test_capability_coverage.py` (chá»‰ khi cáº§n exclusion)
- Create: `apps/api/tests/unit/test_hao_hut_api.py`

## Implementation Steps

1. Viáº¿t `hao_hut.py`: Ä‘á»c `kiem_ke`, `menu_mon`, `waste_notes`; dá»±ng map; gá»i engine.
2. `POST` ghi hao há»¥t: chuáº©n hoÃ¡ `mat_hang`/`nguyen_nhan`, gá»i `_audit("hao_hut", ...)`.
3. `GET /nguong` tráº£ ngÆ°á»¡ng máº·c Ä‘á»‹nh + theo máº·t hÃ ng.
4. ThÃªm capability `GET_LOSS_SUMMARY` (R0_READ, deep-link `/hao-phi`) vÃ 
   `PROPOSE_LOSS_RECORD` (R2_CONFIRM, deep-link `/hao-phi`).
5. VÃ¡ `waste_ghi` thiáº¿u audit; vÃ¡ `_tong_ket_ngay` Ä‘á»c `luc`/`created_at`/`ngay`/`at`.
6. Test: rá»—ng â‡’ tá»•ng 0 dÃ²ng, khÃ´ng bá»‹a; cÃ³ dá»¯ liá»‡u â‡’ dÃ²ng khá»›p cÃ´ng thá»©c Â§4.3;
   thiáº¿u váº¿ â‡’ `thieu_du_lieu`; `POST` ghi váº¿t audit.

## Success Criteria

- [ ] `pytest apps/api -q` xanh, gá»“m `test_capability_coverage.py`.
- [ ] `GET /api/v1/hao-hut` vá»›i KV rá»—ng tráº£ `tong_dong: 0`, **khÃ´ng** raise.
- [ ] DÃ²ng `sua_tuoi` khá»›p sá»‘ vá»›i `kiem_ke` (test Ä‘á»c tháº³ng seed Ä‘á»ƒ Ä‘á»‘i chiáº¿u).
- [ ] `POST /api/v1/hao-hut` xuáº¥t hiá»‡n trong `/api/v1/vet` (audit cÃ³ ghi).
- [ ] `_tong_ket_ngay` Ä‘áº¿m Ä‘Ãºng sá»‘ báº£n ghi trong ngÃ y (test vá»›i `luc`).
- [ ] `GET` vÃ  `POST` cÅ© á»Ÿ `/api/v1/waste` váº«n xanh (test cÅ© khÃ´ng sá»­a).

## Risk Assessment

Rá»§i ro: `POST /api/v1/waste` khi thÃªm `_audit` lÃ m test seed Ä‘áº¿m audit lá»‡ch.
**TÃ­n hiá»‡u:** test seed/audit Ä‘á» vÃ¬ sá»‘ váº¿t tÄƒng. **Pháº£n á»©ng:** xem Ä‘Ã³ lÃ  hÃ nh vi
Ä‘Ãºng (ghi dá»¯ liá»‡u pháº£i cÃ³ váº¿t); cáº­p nháº­t ká»³ vá»ng trong test seed kÃ¨m ghi chÃº lÃ½ do,
khÃ´ng gá»¡ `_audit` Ä‘á»ƒ cho test xanh.

