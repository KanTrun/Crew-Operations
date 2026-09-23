---
phase: 4
title: "Agent máº¹â€“con"
status: completed
priority: P1
effort: "0.5 ngÃ y"
dependencies: [3]
---

# Phase 4: Agent máº¹â€“con

## Overview

Ná»‘i AG-COPILOT (máº¹) vá»›i AG-WASTE (con) qua Ä‘Ãºng kÃªnh cÃ³ sáºµn: `configure_data_sources()`
+ `ANALYZE_LOSS`. Máº¹ Ä‘iá»u phá»‘i vÃ  diá»…n giáº£i; con tÃ­nh. KhÃ´ng phÃ¡ cá»•ng kiáº¿n trÃºc.

## Requirements

- Functional: intent má»›i `ANALYZE_LOSS` tráº£ lá»i Ä‘Æ°á»£c "hao há»¥t tuáº§n nÃ y do Ä‘Ã¢u, nguyÃªn liá»‡u nÃ o".
- Functional: máº¹ truyá»n dá»¯ liá»‡u thÃ´ vÃ o con, con tráº£ sá»‘, máº¹ diá»…n giáº£i thÃ nh cÃ¢u tiáº¿ng Viá»‡t.
- Non-functional: `tool_registry.py` **khÃ´ng** import `ca_agents.ag_waste`, `ca_api`,
  `ca_playbook`, `ca_gates` â€” dá»¯ liá»‡u vÃ o báº±ng inject.
- Non-functional: khÃ´ng cÃ³ dá»¯ liá»‡u â‡’ tráº£ lá»i trung thá»±c, khÃ´ng bá»‹a sá»‘.
- Non-functional: má»i cÃ¢u tráº£ lá»i kÃ¨m `explanation` nÃ³i rÃµ nguá»“n.

## Architecture

Giá»¯ nguyÃªn máº«u Ä‘ang dÃ¹ng cho `ANALYZE_WASTE`: hÃ m con Ä‘Æ°á»£c inject vÃ o tool registry
dÆ°á»›i má»™t tÃªn trong `_SOURCES`, máº¹ gá»i qua `_src(...)`.

```text
main.py (API layer)
  configure_data_sources(..., loss_engine=ca_agents.ag_waste.so_hao_hut, ...)
        â”‚
        â–¼
ag_copilot/tool_registry.py    tool_loss_summary(intent=ANALYZE_LOSS)
        â”‚  _src("loss_engine") â†’ hÃ m thuáº§n cá»§a con
        â”‚  _kv_get("kiem_ke" / "waste_notes") â†’ dá»¯ liá»‡u tháº­t
        â–¼
ToolExecutionResult(data={dong, tong, nguyen_nhan_hang_dau}, summary, explanation)
```

Luá»“ng há»™i thoáº¡i: ngÆ°á»i dÃ¹ng há»i â†’ `intent_parser` nháº­n `ANALYZE_LOSS` â†’ máº¹ gá»i
`tool_loss_summary` â†’ máº¹ tráº£ lá»i kÃ¨m sá»‘ vÃ  nguá»“n. Máº¹ **khÃ´ng** tá»± tÃ­nh.

## Related Code Files

- Modify: `packages/agents/src/ca_agents/ag_copilot/intent_parser.py`
- Modify: `packages/agents/src/ca_agents/ag_copilot/tool_registry.py`
- Modify: `packages/agents/src/ca_agents/ag_copilot/system_prompt.md`
- Modify: `packages/agents/src/ca_agents/ag_copilot/PHAM_VI.md`
- Modify: `packages/contracts/src/ca_contracts/__init__.py` (`CopilotIntent.ANALYZE_LOSS`)
- Modify: `packages/contracts/schema/ActionProposal.json` (sinh láº¡i)
- Modify: `packages/agents/src/ca_agents/ag_copilot/profile.py` náº¿u cÃ³ (kiá»ƒm trÆ°á»›c)
- Modify: `apps/api/src/ca_api/interfaces/http/main.py` (inject nguá»“n má»›i)
- Modify: `apps/api/src/ca_api/interfaces/http/copilot.py` (deep-link intent)
- Create: `packages/agents/tests/test_ag_copilot_loss.py`

## Implementation Steps

1. ThÃªm `ANALYZE_LOSS` vÃ o `CopilotIntent`; cháº¡y `make contracts`.
2. ThÃªm `ANALYZE_LOSS` vÃ o `intent_parser` vá»›i cÃ¡c cá»¥m tá»« tháº­t ("hao há»¥t", "tháº¥t thoÃ¡t",
   "lá»‡ch kiá»ƒm kÃª", "tiÃªu hao nguyÃªn liá»‡u").
3. Viáº¿t `tool_loss_summary` theo máº«u `tool_get_waste_summary`: Ä‘á»c nguá»“n qua `_src`,
   rá»—ng thÃ¬ tráº£ `co_du_lieu: False` + cÃ¢u trung thá»±c.
4. ÄÄƒng kÃ½ `WHITELISTED_INTENTS["ANALYZE_LOSS"]`.
5. Inject `loss_engine` trong `main.configure_data_sources`.
6. Cáº­p nháº­t `system_prompt.md` báº£ng tool; cáº­p nháº­t `PHAM_VI.md`.
7. Test: intent parse Ä‘Ãºng; chÆ°a cáº¥u hÃ¬nh nguá»“n â‡’ bÃ¡o trung thá»±c; cÃ³ dá»¯ liá»‡u â‡’ cÃ³ sá»‘.

## Success Criteria

- [ ] `pytest packages/agents apps/api/tests -q` xanh.
- [ ] Cá»•ng `test_architecture.py` xanh (khÃ´ng import chÃ©o).
- [ ] Há»i "hao há»¥t tuáº§n nÃ y do Ä‘Ã¢u" qua API tráº£ `intent=ANALYZE_LOSS`.
- [ ] Khi KV rá»—ng, tool tráº£ `co_du_lieu: False` â€” test kháº³ng Ä‘á»‹nh Ä‘iá»u nÃ y.
- [ ] `explanation` luÃ´n nÃªu nguá»“n (`kiem_ke`, `menu_mon.bom`, `waste_notes`).

## Risk Assessment

Rá»§i ro: `ANALYZE_LOSS` vÃ  `ANALYZE_WASTE` dá»… khá»›p nháº§m cá»¥m tá»«, lÃ m intent cÅ© Ä‘á»•i
hÃ nh vi. **TÃ­n hiá»‡u:** test `test_ag_copilot.py:41` ("BÃ¡o cÃ¡o hao há»¥t sá»¯a hÃ´m nay")
Ä‘á»•i káº¿t quáº£. **Pháº£n á»©ng:** Ä‘áº·t `ANALYZE_LOSS` khá»›p **sau** cÃ¡c cá»¥m háº¹p hÆ¡n trong
`intent_parser`, vÃ  giá»¯ test cÅ© lÃ m chá»‘t canh; náº¿u test cÅ© Ä‘á»•i thÃ¬ sá»­a thá»© tá»± khá»›p,
khÃ´ng sá»­a test.

