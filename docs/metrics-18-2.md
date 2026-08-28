# AG-TKB Accuracy Metrics

| Date | Correct | Total | Accuracy | Blur items |
|------|---------|-------|----------|------------|
| 2026-08-22 | 50 | 51 | 98.04% | 1 |

## Notes

- Mode: **replay** (golden JSON, no live LLM)
- Blur items (1) counted as incorrect (confidence < 0.7)
- Non-blur accuracy: 100.00% (50/50)
- Replay on clear fixtures = perfect recall by design; live vision will be lower.

## AG-MSG confusion (Sprint 3)

| Date | Correct | Total | Accuracy |
|------|---------|-------|----------|
| 2026-08-22 | 200 | 200 | 100.00% |

Rows = gold, cols = predicted. Classifier is keyword tier-1; unmatched → `khac` (tier 2 fallback). **Not an LLM.** Golden texts in `data/golden/messages/` largely restates those keywords, so high accuracy is expected and is not independent evidence of NLU. Replay only, no live network.

| gold \ pred | doi_ca | nhan_ca | bao_tre | cap_nhat_tkb | xin_nghi | khac |
|---|---|---|---|---|---|---|
| doi_ca | 34 | 0 | 0 | 0 | 0 | 0 |
| nhan_ca | 0 | 34 | 0 | 0 | 0 | 0 |
| bao_tre | 0 | 0 | 33 | 0 | 0 | 0 |
| cap_nhat_tkb | 0 | 0 | 0 | 33 | 0 | 0 |
| xin_nghi | 0 | 0 | 0 | 0 | 33 | 0 |
| khac | 0 | 0 | 0 | 0 | 0 | 33 |
