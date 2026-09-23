---
phase: 6
title: "Danh má»¥c sáº£n pháº©m & hÃ¬nh"
status: completed
priority: P1
effort: "1 ngÃ y"
dependencies: [5]
---

# Phase 6: Danh má»¥c sáº£n pháº©m & hÃ¬nh

## Overview

BÆ¡m Ä‘áº§y danh má»¥c sáº£n pháº©m (cÃ  phÃª, trÃ , nÆ°á»›c Ä‘Ã³ng chai, nguyÃªn liá»‡u, bÃ¡nh) vÃ 
**sinh áº£nh táº¡i mÃ¡y** cho má»i mÃ³n â€” cháº¡y Ä‘Æ°á»£c khi rÃºt máº¡ng, chi phÃ­ 0 Ä‘á»“ng.

## Requirements

- Functional: danh má»¥c â‰¥ 45 máº·t hÃ ng, phá»§ Ä‘á»§ nhÃ³m: cÃ  phÃª, trÃ , nÆ°á»›c Ä‘Ã³ng chai,
  nguyÃªn liá»‡u pha cháº¿, bÃ¡nh, ly/á»‘ng hÃºt.
- Functional: má»—i mÃ³n cÃ³ `bom` Ä‘Ãºng Ä‘Æ¡n vá»‹ theo `BOM_INGREDIENTS`.
- Functional: sinh áº£nh cho má»i mÃ³n trong menu; áº£nh táº¥t Ä‘á»‹nh (cÃ¹ng input â‡’ cÃ¹ng byte).
- Non-functional: **khÃ´ng gá»i máº¡ng, khÃ´ng API áº£nh** â€” rÃ ng buá»™c demo offline Â§14.9.
- Non-functional: idempotent â€” cháº¡y láº¡i khÃ´ng nhÃ¢n báº£n, khÃ´ng Ä‘Ã¨ áº£nh ngÆ°á»i dÃ¹ng tá»± táº£i.
- Non-functional: áº£nh pháº£i theo há»‡ mÃ u quÃ¡n (`--nq-*`: copper `#c4a574`, ná»n tá»‘i).

## Architecture

Hai cÃ´ng cá»¥ tÃ¡ch biá»‡t, Ä‘á»u lÃ  script váº­n hÃ nh (khÃ´ng pháº£i mÃ£ cháº¡y lÃºc phá»¥c vá»¥):

```text
scripts/seed_danh_muc.py
  - Ä‘á»c data/seed/danh-muc.json (nguá»“n duy nháº¥t)
  - upsert menu_mon theo id, gáº¯n nguon="danh_muc_chuan"
  - giá»¯ nguyÃªn mÃ³n do quÃ¡n tá»± thÃªm

scripts/sinh_anh_mon.py
  - Ä‘á»c tá»«ng mÃ³n tá»« menu_mon
  - sinh áº£nh PNG/WEBP táº¥t Ä‘á»‹nh báº±ng Pillow (khÃ´ng máº¡ng)
  - ghi data/menu_images/<mon_id>.png
  - Bá»Ž QUA náº¿u áº£nh Ä‘Ã£ do quÃ¡n táº£i lÃªn (Ä‘Ã¡nh dáº¥u trong hinh_url)
```

VÃ¬ sao táº¡i mÃ¡y: `docs/THIRD_PARTY.md` ghi free tier cloud "dá»… thu há»“i", vÃ  Â§14.9
buá»™c demo cháº¡y trá»n khi rÃºt máº¡ng. API áº£nh Ä‘Ã¡m mÃ¢y vá»«a tá»‘n quota vá»«a lÃ m buá»•i demo
phá»¥ thuá»™c máº¡ng. Pillow Ä‘Ã£ cÃ³ trong venv (`12.3.0`) vÃ  trong CI.

áº¢nh sinh ra lÃ  **áº£nh tháº» sáº£n pháº©m**: ná»n gradient tá»‘i theo há»‡ mÃ u quÃ¡n, khá»‘i hÃ¬nh
há»c Ä‘áº¡i diá»‡n nhÃ³m (ly/trÃ /chai/bÃ¡nh), chá»¯ tÃªn mÃ³n + Ä‘Æ¡n giÃ¡ báº±ng font há»‡ thá»‘ng.
Táº¥t Ä‘á»‹nh: má»i tham sá»‘ suy tá»« `mon_id` báº±ng hash, khÃ´ng dÃ¹ng `random`.

## Related Code Files

- Create: `data/seed/danh-muc.json` (nguá»“n danh má»¥c, Ä‘Æ°á»£c git theo dÃµi nhÆ° `sample.json`)
- Create: `scripts/seed_danh_muc.py`
- Create: `scripts/sinh_anh_mon.py`
- Modify: `data/seed/.gitignore` (cho phÃ©p `danh-muc.json`)
- Modify: `apps/api/src/ca_api/persist.py` (`_MENU_MAC_DINH` â€” bá»• sung nÆ°á»›c Ä‘Ã³ng chai)
- Modify: `apps/api/src/ca_api/interfaces/http/pos.py` (fallback áº£nh sinh táº¡i mÃ¡y khi chÆ°a upload)
- Modify: `Makefile` (`seed-danh-muc`, `sinh-anh`)
- Modify: `docs/THIRD_PARTY.md` (ghi Pillow náº¿u chÆ°a cÃ³ dÃ²ng tÆ°Æ¡ng á»©ng)
- Create: `apps/api/tests/unit/test_sinh_anh_mon.py`

## Implementation Steps

1. Soáº¡n `data/seed/danh-muc.json`: id, tÃªn, giÃ¡, nhÃ³m, `bom`, `hinh_mo_ta` (mÃ´ táº£
   hÃ¬nh Ä‘á»ƒ sinh áº£nh). Äá»§ â‰¥ 45 mÃ³n.
2. Viáº¿t `seed_danh_muc.py` idempotent theo `id`; in báº£ng Ä‘áº¿m theo nhÃ³m.
3. Viáº¿t `sinh_anh_mon.py` báº±ng Pillow: táº¥t Ä‘á»‹nh, khÃ´ng máº¡ng, cÃ³ cháº¿ Ä‘á»™ `--dry-run`.
4. Cho `GET /api/v1/menu/{mon_id}/anh` fallback sang áº£nh sinh táº¡i mÃ¡y khi chÆ°a upload.
5. ThÃªm target Makefile; cáº­p nháº­t `THIRD_PARTY.md` náº¿u Pillow chÆ°a Ä‘Æ°á»£c khai.
6. Test: sinh áº£nh hai láº§n cho ra byte giá»‘ng nhau; áº£nh lÃ  PNG/WEBP há»£p lá»‡; sá»‘ áº£nh â‰¥ sá»‘ mÃ³n.

## Success Criteria

- [ ] `python scripts/seed_danh_muc.py` rá»“i `GET /api/v1/menu/quan-tri` tráº£ â‰¥ 45 mÃ³n.
- [ ] Cháº¡y script hai láº§n: sá»‘ mÃ³n **khÃ´ng** tÄƒng; mÃ³n quÃ¡n tá»± thÃªm cÃ²n nguyÃªn.
- [ ] `python scripts/sinh_anh_mon.py` sinh áº£nh cho **má»i** mÃ³n; cháº¡y láº¡i ra cÃ¹ng byte.
- [ ] `GET /api/v1/menu/{id}/anh` tráº£ 200 áº£nh há»£p lá»‡ cho má»i mÃ³n, **khi táº¯t máº¡ng**.
- [ ] CÃ³ nÆ°á»›c Ä‘Ã³ng chai trong danh má»¥c máº·c Ä‘á»‹nh cá»§a `persist.py`.
- [ ] `ruff check scripts` sáº¡ch.

## Risk Assessment

Rá»§i ro 1: ghi tháº³ng vÃ o `data/menu_images/` (Ä‘ang gitignore) khiáº¿n áº£nh khÃ´ng tá»“n
táº¡i á»Ÿ mÃ¡y khÃ¡c / CI. **TÃ­n hiá»‡u:** CI cháº¡y e2e mÃ  áº£nh 404. **Pháº£n á»©ng:** áº£nh sinh
theo yÃªu cáº§u táº¡i chá»— phá»¥c vá»¥ (fallback á»Ÿ bÆ°á»›c 4), nÃªn CI tá»± sinh láº¡i; khÃ´ng cáº§n
commit áº£nh nhá»‹ phÃ¢n.

Rá»§i ro 2: Pillow váº½ font tiáº¿ng Viá»‡t cáº§n font cÃ³ dáº¥u. **TÃ­n hiá»‡u:** chá»¯ ra Ã´ vuÃ´ng.
**Pháº£n á»©ng:** dÃ¹ng font há»‡ thá»‘ng Ä‘Ã£ dÃ¹ng cho web náº¿u tÃ¬m tháº¥y; khÃ´ng tháº¥y thÃ¬ váº½
khá»‘i hÃ¬nh há»c + chá»¯ khÃ´ng dáº¥u dáº¡ng mÃ£, vÃ  ghi rÃµ giá»›i háº¡n trong docs â€” khÃ´ng bá»‹a font.

