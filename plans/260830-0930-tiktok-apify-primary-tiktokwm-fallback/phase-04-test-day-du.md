---
title: "Phase 04 — Test unit + integration + smoke"
description: "Viết test đầy đủ: unit mock Apify, integration gọi thật, test fallback path, smoke end-to-end qua API."
status: planned
priority: P2
effort: "30min"
tags: [test, pytest, integration, phase-04]
created: 2026-08-30
blockedBy: [phase-03]
blocks: [phase-05]
---

# Phase 04 — Test unit + integration + smoke

## Mục tiêu

3 tầng test:
1. **Unit** — mock toàn bộ HTTP, nhanh, chạy được kể cả không có token
2. **Integration** — gọi Apify thật (cần `APIFY_TOKEN`), chỉ chạy khi có marker
3. **Smoke** — gọi end-to-end qua API, verify UI nhận đúng data

## File 1: `apps/api/tests/unit/test_apify_client.py`

### Setup

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from ca_agents.clients.apify_client import run_actor_sync, ApifyError
```

### Test cases

| # | Tên test | Mock setup | Expect |
|---|----------|-----------|--------|
| 1 | `test_missing_token_raises` | `monkeypatch.delenv("APIFY_TOKEN")` | `ApifyError` |
| 2 | `test_start_run_fail_raises` | Mock `urlopen` raise `URLError("401")` | `ApifyError("Không start được actor")` |
| 3 | `test_run_succeeded_returns_items` | Mock 3 calls: POST → `{"data": {"id": "r1"}}`; GET status → `SUCCEEDED`; GET items → `[{"a": 1}, {"b": 2}]` | Return `[{"a":1}, {"b":2}]` |
| 4 | `test_run_failed_raises` | Mock status = `FAILED` | `ApifyError("status=FAILED")` |
| 5 | `test_run_aborted_raises` | Mock status = `ABORTED` | `ApifyError("status=ABORTED")` |
| 6 | `test_empty_dataset_raises` | Mock status SUCCEEDED, items = `[]` | `ApifyError("dataset rỗng")` |
| 7 | `test_polling_timeout_raises` | Mock status luôn `RUNNING`, fake `time.monotonic` tăng nhanh | `ApifyError("timeout sau")` |
| 8 | `test_polling_eventually_succeeds` | Mock status: 2 lần `RUNNING`, lần 3 `SUCCEEDED` | Return items |
| 9 | `test_no_token_leaked_in_logs` | Capture `caplog` records, assert token không xuất hiện | - |

### Helper function trong conftest

```python
@pytest.fixture
def mock_apify_success(monkeypatch):
    """Mock 3 calls Apify thành công trả 2 items."""
    items = [{"id": "v1", "text": "abc"}, {"id": "v2", "text": "def"}]
    
    responses = [
        json.dumps({"data": {"id": "run_123"}}).encode(),  # POST start
        json.dumps({"data": {"status": "RUNNING", "defaultDatasetId": "ds1"}}).encode(),
        json.dumps({"data": {"status": "SUCCEEDED", "defaultDatasetId": "ds1"}}).encode(),
        json.dumps(items).encode(),                          # GET dataset items
    ]
    
    iterator = iter(responses)
    
    def fake_urlopen(req, **kwargs):
        m = MagicMock()
        m.__enter__ = lambda s: s
        m.__exit__ = lambda s, *a: None
        m.read = lambda: next(iterator)
        return m
    
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return items
```

## File 2: `apps/api/tests/unit/test_tiktok_apify_source.py`

### Test cases

| # | Tên test | Setup | Expect |
|---|----------|-------|--------|
| 1 | `test_happy_path_returns_12_items` | Mock `run_actor_sync` return 12 items valid | 12 TrendItem, source=apify |
| 2 | `test_apify_error_propagates` | Mock raise `ApifyError("empty")` | Propagate lên caller |
| 3 | `test_text_truncated_to_65_chars` | Item text 200 chars | `tieu_de` có prefix + 65 chars + "..." |
| 4 | `test_missing_video_meta_uses_zero` | Item thiếu `videoMeta` | `luot_tiep_can` = "0 views \| 0 tim" |
| 5 | `test_nguon_goc_global_param` | Param `nguon_goc="tiktok_global"` | `TrendItem.nguon_goc == "tiktok_global"` |
| 6 | `test_comment_format_top_5` | Mock 7 comments | `len(binh_luan_that_tiktok) == 5` |
| 7 | `test_comment_skips_empty_text` | Mock 3 comments, 1 có text rỗng | List có 2 items |
| 8 | `test_hashtag_extraction` | Text `"#fyp #xuhuong hay"` | `tu_khoa_hashtag` có `#fyp`, `#xuhuong` |
| 9 | `test_tiktok_url_fallback` | Item không có `webVideoUrl` | Build URL từ `authorMeta.name` + `id` |
| 10 | `test_log_does_not_leak_payload` | Capture log, assert không có token | - |

## File 3: `apps/api/tests/unit/test_tiktok_smart_fallback.py`

### Test cases

| # | Tên test | Setup | Expect |
|---|----------|-------|--------|
| 1 | `test_apify_success_skips_tiktokwm` | Mock Apify return items, TikWM không được mock | Return Apify items |
| 2 | `test_apify_error_triggers_tiktokwm` | Mock Apify raise `ApifyError`, mock TikWM return items | Return TikWM items + warning log |
| 3 | `test_apify_unexpected_error_triggers_tiktokwm` | Mock Apify raise `ValueError` | Return TikWM items |
| 4 | `test_both_fail_returns_empty` | Mock Apify raise, TikWM raise | Return `[]` |
| 5 | `test_fallback_log_includes_reason` | Trigger fallback với `ApifyError("quota exceeded")` | Log có field `reason=apify_error:ApifyError` |
| 6 | `test_nguon_goc_passed_through` | Call `_scrape_tiktok_smart(nguon_goc="tiktok_global")` | Apify được gọi với `nguon_goc="tiktok_global"` |

## File 4: `apps/api/tests/integration/test_tiktok_live.py`

### Marker

```python
import pytest

pytestmark = pytest.mark.integration  # chỉ chạy khi: pytest -m integration
```

### Skip khi không có token

```python
@pytest.fixture(autouse=True)
def require_apify_token():
    import os
    if not os.getenv("APIFY_TOKEN"):
        pytest.skip("APIFY_TOKEN không có trong env — skip integration test")
```

### Test cases

| # | Tên test | Expect |
|---|----------|--------|
| 1 | `test_live_search_returns_items` | ≥ 5 items, mỗi item có `id`, `text`, `webVideoUrl` |
| 2 | `test_live_global_search` | Search keyword tiếng Anh, ≥ 3 items |
| 3 | `test_actor_actually_called` | Không skip, log có `apify_tiktok_source` |

### Chạy

```bash
# Local (cần APIFY_TOKEN trong .env)
cd apps/api
pytest -m integration tests/integration/test_tiktok_live.py -v -s

# CI (không có token → tất cả skip, không fail)
pytest -m integration tests/integration/test_tiktok_live.py -v
```

## File 5: `scripts/smoke_tiktok_apify.py`

### Mục đích

Manual smoke sau khi deploy, không cần pytest, in kết quả ra console để người vận hành xem.

### Flow

1. Load `.env`
2. Gọi `_scrape_tiktok_smart(keyword="xuhuong", count=5, nguon_goc="tiktok_vn")`
3. In ra:
   - Source đã dùng (apify/tiktokwm)
   - Số items
   - Top 3 tiêu đề + URL
4. Nếu source = tiktokwm → in WARNING đỏ: "⚠️  Apify fail, đang dùng fallback"

### Cách chạy

```bash
python scripts/smoke_tiktok_apify.py
```

## Coverage target

| File | Target |
|---|---|
| `clients/apify_client.py` | ≥ 90% |
| `sources/tiktok_apify_source.py` | ≥ 90% |
| `ag_trend.py::_scrape_tiktok_smart` | ≥ 85% |

Đo:
```bash
pytest --cov=ca_agents.clients.apify_client \
       --cov=ca_agents.sources.tiktok_apify_source \
       --cov=ca_agents.ag_trend \
       --cov-report=term-missing \
       apps/api/tests/unit/test_apify_client.py \
       apps/api/tests/unit/test_tiktok_apify_source.py \
       apps/api/tests/unit/test_tiktok_smart_fallback.py
```

## Kiểm tra "Phase done"

- [ ] `pytest apps/api/tests/unit/test_apify_client.py` — tất cả pass
- [ ] `pytest apps/api/tests/unit/test_tiktok_apify_source.py` — tất cả pass
- [ ] `pytest apps/api/tests/unit/test_tiktok_smart_fallback.py` — tất cả pass
- [ ] `pytest -m integration apps/api/tests/integration/test_tiktok_live.py` — pass khi có token, skip khi không
- [ ] `python scripts/smoke_tiktok_apify.py` — in ra ≥ 5 items từ Apify
- [ ] Coverage ≥ target cho 3 file

## Reference

- Existing pattern: `apps/api/tests/unit/test_trends_api.py`
- Existing conftest: `apps/api/tests/conftest.py`
- Phase 3 output: `_scrape_tiktok_smart` trong `ag_trend.py`