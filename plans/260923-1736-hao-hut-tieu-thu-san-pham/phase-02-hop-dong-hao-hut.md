---
phase: 2
title: "Há»£p Ä‘á»“ng hao há»¥t"
status: completed
priority: P1
effort: "0.5 ngÃ y"
dependencies: [1]
---

# Phase 2: Há»£p Ä‘á»“ng hao há»¥t

## Overview

Äá»‹nh hÃ¬nh `LossLine` / `LossSummary` / `LossCauseRank` vÃ  **ngÆ°á»¡ng hao há»¥t cÃ³
nguá»“n** trÆ°á»›c khi viáº¿t báº¥t ká»³ logic nÃ o (ADR-003).

## Requirements

- Functional: mÃ´ táº£ Ä‘Æ°á»£c má»™t dÃ²ng hao há»¥t theo nguyÃªn liá»‡u; má»™t tá»•ng; má»™t háº¡ng má»¥c
  nguyÃªn nhÃ¢n.
- Functional: ngÆ°á»¡ng láº¥y tá»« `config/` â€” khÃ´ng hard-code trong mÃ£ nghiá»‡p vá»¥.
- Non-functional: schema JSON sinh ra Ä‘Æ°á»£c, TS sinh ra Ä‘Æ°á»£c, round-trip pydantic.
- Non-functional: enum `LossLevel` pháº£i cÃ³ nhÃ¡nh `thieu_du_lieu` â€” khÃ´ng cho phÃ©p
  biá»ƒu diá»…n "khÃ´ng biáº¿t" báº±ng sá»‘ 0.

## Architecture

Enum vÃ  model thuáº§n dá»¯ liá»‡u, **khÃ´ng** chá»©a suy luáº­n (ADR-002). NgÆ°á»¡ng lÃ  tham sá»‘
cáº¥u hÃ¬nh truyá»n vÃ o hÃ m, khÃ´ng pháº£i háº±ng sá»‘ trong model.

```text
ca_contracts/loss.py
  LossLevel      = dat | canh_bao | nghiem_trong | thieu_du_lieu
  LossBasis      = ke_hoach_kiem_ke | don_quay_thuc_te | hon_hop
  LossLine       mat_hang, ten, don_vi, ly_thuyet*, thuc_te*, lech*,
                 ty_le_phan_tram*, muc_do, co_so, ghi_chu
  LossCauseRank  nguyen_nhan, so_lan, mat_hang_lien_quan, ty_le_tong
  LossSummary    ky, tong_dong, so_nghiem_trong, so_canh_bao, so_thieu_du_lieu,
                 ty_le_trung_binh, dong[], nguyen_nhan_hang_dau[],
                 nguon, co_du_lieu_mau
```

`*` = `float | None`. `None` nghÄ©a lÃ  **chÆ°a cÃ³ dá»¯ liá»‡u**, khÃ¡c háº³n `0.0`.

## Related Code Files

- Create: `packages/contracts/src/ca_contracts/loss.py`
- Create: `packages/contracts/tests/test_loss_contracts.py`
- Create: `config/nguong-hao-hut.yaml`
- Modify: `packages/contracts/src/ca_contracts/__init__.py` (import + `CONTRACTS` + `__all__`)
- Modify: `packages/contracts/tests/test_contracts.py` (bá»• sung tÃªn vÃ o set ká»³ vá»ng)
- Modify: `packages/contracts/schema/index.json` + `packages/contracts/ts/contracts.ts` (sinh tá»± Ä‘á»™ng)

## Implementation Steps

1. Viáº¿t `loss.py` vá»›i 3 enum + 3 model, `Field` cÃ³ rÃ ng buá»™c (`ge=0`, mÃ´ táº£ tiáº¿ng Viá»‡t).
2. Viáº¿t test há»£p Ä‘á»“ng: round-trip, `None` khÃ¡c `0.0`, `ty_le_phan_tram` Ã¢m há»£p lá»‡
   (hao há»¥t Ã¢m = Ä‘áº¿m dÆ°), tá»« chá»‘i giÃ¡ trá»‹ ngoÃ i enum.
3. ÄÄƒng kÃ½ vÃ o `CONTRACTS`, `__all__`, vÃ  set ká»³ vá»ng trong `test_contracts.py`.
4. Viáº¿t `config/nguong-hao-hut.yaml` theo house style cá»§a `tham-so-lao-dong.yaml`
   (cÃ³ `phien_ban`, `ngay_kiem`, `nguon`, `ghi_chu`).
5. Cháº¡y `make contracts`; kiá»ƒm `contracts.ts` cÃ³ interface má»›i, khÃ´ng cÃ³ `unknown` stub.

## Success Criteria

- [ ] `pytest packages/contracts -q` xanh.
- [ ] `test_contracts_registered` xanh sau khi thÃªm tÃªn.
- [ ] `make contracts` cháº¡y láº¡i khÃ´ng táº¡o drift (cháº¡y hai láº§n, `git diff` rá»—ng láº§n hai).
- [ ] `config/nguong-hao-hut.yaml` parse Ä‘Æ°á»£c báº±ng `yaml.safe_load`, cÃ³ ngÆ°á»¡ng máº·c Ä‘á»‹nh + theo máº·t hÃ ng.

## Risk Assessment

Rá»§i ro: sá»­a `test_contracts.py` (set ká»³ vá»ng cá»©ng) cÃ³ thá»ƒ va cháº¡m náº¿u nhÃ¡nh khÃ¡c
cÅ©ng thÃªm contract. **TÃ­n hiá»‡u:** `git status` tháº¥y file nÃ y Ä‘Ã£ Ä‘á»•i trÆ°á»›c khi mÃ¬nh
sá»­a. **Pháº£n á»©ng:** Ä‘á»c láº¡i file ngay trÆ°á»›c khi sá»­a, chÃ¨n theo thá»© tá»± chá»¯ cÃ¡i trong
khá»‘i, khÃ´ng viáº¿t láº¡i cáº£ set.

