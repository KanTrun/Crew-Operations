# AG-TKB Accuracy Metrics

| Date | Correct | Total | Accuracy | Blur items |
|------|---------|-------|----------|------------|
| 2026-08-30 | 51 | 53 | 96.23% | 2 |

- % đẩy lên người (escalate): 3.8% (2/53)
- Hard/blur subset accuracy: 33.33% (1/3)

## Notes

- Mode: **replay** (golden JSON, no live LLM)
- Blur items (2) counted as incorrect (confidence < 0.7)
- Non-blur accuracy: 100.00% (51/51)
- Replay on clear fixtures = perfect recall by design; live vision will be lower.

## AG-MSG confusion (Sprint 3)

| Date | Correct | Total | Accuracy |
|------|---------|-------|----------|
| 2026-08-30 | 197 | 200 | 98.50% |

Hard/medium subset: 74/77 = 96.10%

Golden gồm ~40% hard/medium (`hard_cases.jsonl`). Classifier keyword tier-1; unmatched → `khac`. Replay only, no live network.

| gold \ pred | doi_ca | nhan_ca | bao_tre | cap_nhat_tkb | xin_nghi | khac |
|---|---|---|---|---|---|---|
| doi_ca | 34 | 0 | 0 | 0 | 0 | 0 |
| nhan_ca | 0 | 29 | 0 | 0 | 0 | 1 |
| bao_tre | 0 | 0 | 32 | 0 | 0 | 0 |
| cap_nhat_tkb | 0 | 0 | 0 | 33 | 0 | 1 |
| xin_nghi | 0 | 0 | 0 | 0 | 28 | 1 |
| khac | 0 | 0 | 0 | 0 | 0 | 41 |
