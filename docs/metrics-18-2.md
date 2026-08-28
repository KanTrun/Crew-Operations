# AG-TKB Accuracy Metrics

| Date | Correct | Total | Accuracy | Blur items |
|------|---------|-------|----------|------------|
| 2026-08-28 | 51 | 53 | 96.23% | 2 |

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
| 2026-08-28 | 197 | 200 | 98.50% |

Hard/medium subset: 74/77 = 96.10%

Rows = gold, cols = predicted. Classifier is keyword tier-1; unmatched → `khac` (tier 2 fallback). **Not an LLM.** Golden texts in `data/golden/messages/` largely restates those keywords, so high accuracy is expected and is not independent evidence of NLU. Replay only, no live network.

| gold \ pred | doi_ca | nhan_ca | bao_tre | cap_nhat_tkb | xin_nghi | khac |
|---|---|---|---|---|---|---|
| doi_ca | 34 | 0 | 0 | 0 | 0 | 0 |
| nhan_ca | 0 | 29 | 0 | 0 | 0 | 1 |
| bao_tre | 0 | 0 | 32 | 0 | 0 | 0 |
| cap_nhat_tkb | 0 | 0 | 0 | 33 | 0 | 1 |
| xin_nghi | 0 | 0 | 0 | 0 | 28 | 1 |
| khac | 0 | 0 | 0 | 0 | 0 | 41 |

## Override demo tuần 1 (nhóm A)

| Tuần | Quyết định | Bị sửa | Không cần sửa | Nguồn |
|------|------------|--------|---------------|-------|
| W01 fixture | 49 | 30 | 38.8% | `data/seed/sample.json` `mo_phong_fixture` |

Đường cong W1→W8: **ngoài phạm vi bài thi** (nhóm B).


## VF escalate (fixture demo)

| Cổng | Lần đẩy lên người (fixture) |
|------|---------------------------|
| VF-SCHEMA | 0 |
| VF-TRACE | 1 |
| VF-CONF | 2 |
| **Tổng** | **3** |

Replay fixture — không traffic quán thật.
