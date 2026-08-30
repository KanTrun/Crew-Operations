---
title: "Phase 02 — Adapter Apify client + TikTok source"
description: "Tạo module apify_client (HTTP wrapper + polling) và tiktok_apify_source (map schema → TrendItem)."
status: planned
priority: P2
effort: "45min"
tags: [apify, adapter, phase-02, code]
created: 2026-08-30
blockedBy: [phase-01]
blocks: [phase-03]
---

# Phase 02 — Adapter Apify client + TikTok source

## Mục tiêu

Có 2 module mới sạch, độc lập với `ag_trend.py`, có thể gọi test được ngay.

```
packages/agents/src/ca_agents/
├── clients/
│   ├── __init__.py
│   └── apify_client.py          # ← MỚI: HTTP wrapper + polling
├── sources/
│   ├── __init__.py
│   └── tiktok_apify_source.py   # ← MỚI: schema mapping
└── ag_trend.py                  # (chưa đụng ở phase này)
```

## File 1: `packages/agents/src/ca_agents/clients/apify_client.py`

### API công khai

```python
class ApifyError(Exception):
    """Raised khi actor fail / timeout / quota hết / token sai."""

def run_actor_sync(
    actor_id: str,
    payload: dict[str, Any],
    timeout_s: int = 90,
) -> list[dict[str, Any]]:
    """
    Start run → poll → trả dataset items.
    
    Raises:
        ApifyError: token missing, start fail, status FAIL/ABORT/TIMEOUT,
                    poll timeout, dataset rỗng.
    """
```

### Behavior yêu cầu

| Tình huống | Hành vi |
|---|---|
| `APIFY_TOKEN` rỗng trong env | Raise `ApifyError("APIFY_TOKEN chưa cấu hình")` |
| Start run fail (HTTP 401/403/500) | Raise `ApifyError(f"Không start được actor: {e}")` |
| Polling timeout (> timeout_s) | Raise `ApifyError(f"Apify run {run_id} timeout sau {timeout_s}s")` |
| Status = SUCCEEDED, items = [] | Raise `ApifyError("Apify trả về dataset rỗng")` |
| Status = FAILED/ABORTED/TIMED-OUT | Raise `ApifyError(f"Apify run {run_id} status={status}")` |
| Thành công | Return `list[dict]` |

### Implementation lưu ý

- Dùng `urllib.request` (đồng nhất với TikWM hiện tại, không cần thêm dep)
- Không log full payload (có thể chứa token) — chỉ log `actor_id`, `run_id`, `status`, `items_count`
- Polling interval: 2s
- Timeout per HTTP call: 10s (start), 5s (poll), 10s (dataset fetch)

### Test yêu cầu cho file này

| Test | Cách test |
|---|---|
| Test thiếu token | `monkeypatch.delenv("APIFY_TOKEN")` → expect `ApifyError` |
| Test start fail | Mock `urllib.request.urlopen` raise `URLError` → expect `ApifyError` |
| Test run SUCCEEDED | Mock 3 calls: POST → {id: "r1"}; GET status → SUCCEEDED; GET items → [{...}] |
| Test run TIMED-OUT | Mock status = "TIMED-OUT" → expect `ApifyError` |
| Test empty dataset | Mock status SUCCEEDED, items = [] → expect `ApifyError("...rỗng")` |
| Test polling timeout | Mock luôn return status = "RUNNING", fake `time.monotonic` → expect `ApifyError` |

## File 2: `packages/agents/src/ca_agents/sources/tiktok_apify_source.py`

### API công khai

```python
def scrape_tiktok_apify(
    keyword: str = "",
    count: int = 12,
    mode: str = "search",          # "search" | "hashtag" | "profile"
    nguon_goc: str = "tiktok_vn",  # "tiktok_vn" | "tiktok_global"
) -> list[TrendItem]:
    """
    Cào TikTok qua Apify actor clockworks/tiktok-scraper.
    
    Raises:
        ApifyError: nếu Apify fail (caller sẽ fallback TikWM).
    """
```

### Input payload (theo schema Apify)

```python
def _build_input(keyword, count, mode) -> dict:
    base = {
        "maxItems": count,
        "downloadVideo": False,           # tiết kiệm CU
        "proxyCountryCode": "VN",
    }
    if mode == "search":
        base["searchQueries"] = [keyword] if keyword else []
    elif mode == "hashtag":
        base["hashtags"] = [keyword.lstrip("#")] if keyword else []
    elif mode == "profile":
        base["profiles"] = [keyword.lstrip("@")] if keyword else []
    return base
```

### Mapping (xác nhận lại sau khi có schema sample từ Phase 1)

| TrendItem field | Apify field | Fallback |
|---|---|---|
| `id` | `f"apify_tiktok_{idx}_{item['id']}"` | |
| `tieu_de` | `f"🎵 [TIKTOK VIRAL] {item['text'][:65]}..."` | "Video TikTok" nếu text rỗng |
| `cum_tu_khoa_viral` | `keyword` (nếu có) hoặc `extract_core_tiktok_keyword(item['text'])` | |
| `tiktok_url` | `item['webVideoUrl']` | `f"https://www.tiktok.com/@{author}/video/{video_id}"` |
| `tiktok_tag_url` | `f"https://www.tiktok.com/tag/{clean_tag}"` | `video_url` |
| `nguon_goc` | truyền vào qua param | |
| `nguon_goc_chi_tiet` | `f"Apify actor {ACTOR_ID} lúc {now_str}."` | |
| `luot_tiep_can` | `f"{play:,} views | {digg:,} tim"` | |
| `binh_luan_that_tiktok` | `comments[:5]` format | `[]` nếu field không có |
| `tu_khoa_hashtag` | extract regex `#\w+` từ `text` | `[f"#{author}", "#xuhuongtiktok"]` |

### Logging

```python
logger.info(
    "apify_tiktok_source",
    extra={
        "source": "apify",
        "mode": mode,
        "keyword": keyword[:50],     # truncate để tránh log quá dài
        "items_count": len(items_out),
        "duration_ms": int((time.monotonic() - start) * 1000),
    },
)
```

### Test yêu cầu cho file này

| Test | Setup |
|---|---|
| Test happy path | Mock `run_actor_sync` return 12 items valid → assert 12 TrendItem |
| Test items rỗng (đã raise ở client) | Mock raise `ApifyError` → propagate lên |
| Test text quá dài | Item có text 200 chars → tieu_de có prefix + 65 chars + "..." |
| Test missing fields | Item thiếu `videoMeta` → không crash, dùng 0 |
| Test nguon_goc=global | Param `nguon_goc="tiktok_global"` → TrendItem.nguon_goc đúng |
| Test comment format | Mock 7 comments → chỉ lấy 5, format chuẩn `@u: "t" (❤️ N tim)` |
| Test hashtag extract | Text `"#fyp #xuhuong hay quá"` → tu_khoa_hashtag có `#fyp`, `#xuhuong` |

## Imports cần có

```python
# apify_client.py
import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any

# tiktok_apify_source.py
import logging
import os
import re
import time
from datetime import datetime

from ca_agents.ag_trend import TrendItem, extract_core_tiktok_keyword
from ca_agents.clients.apify_client import run_actor_sync, ApifyError
```

## Kiểm tra "Phase done"

- [ ] 2 file mới tạo đúng path
- [ ] `__init__.py` cho 2 folder mới
- [ ] 6 test cho `apify_client.py` pass
- [ ] 7 test cho `tiktok_apify_source.py` pass
- [ ] `python -c "from ca_agents.clients.apify_client import run_actor_sync"` không ImportError
- [ ] `python -c "from ca_agents.sources.tiktok_apify_source import scrape_tiktok_apify"` không ImportError
- [ ] Code không log full payload / token

## Reference

- Apify API v2: https://docs.apify.com/api/v2
- Actor clockworks: https://apify.com/clockworks/tiktok-scraper/schema
- Existing pattern: `packages/agents/src/ca_agents/ag_trend.py::_scrape_direct_tiktok_videos`