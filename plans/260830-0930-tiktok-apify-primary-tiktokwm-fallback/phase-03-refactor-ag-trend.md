---
title: "Phase 03 — Refactor ag_trend.py với fallback"
description: "Sửa call sites TikTok trong ag_trend.py: thay TikWM trực tiếp bằng _scrape_tiktok_smart (Apify → TikWM fallback)."
status: planned
priority: P2
effort: "30min"
tags: [ag-trend, refactor, fallback, phase-03, code]
created: 2026-08-30
blockedBy: [phase-02]
blocks: [phase-04]
---

# Phase 03 — Refactor ag_trend.py với fallback

## Mục tiêu

Sửa `ag_trend.py` để mọi call site TikTok đều đi qua `_scrape_tiktok_smart()`, đảm bảo Apify là primary, TikWM chỉ chạy khi cần.

## Trước khi sửa: khảo sát call sites

Cần đọc lại `packages/agents/src/ca_agents/ag_trend.py` để xác định chính xác các điểm đang gọi TikWM.

| Call site hiện tại (dự kiến) | Dòng tham chiếu | Hành động |
|---|---|---|
| `if platform_filter == "tiktok_vn":` | ~447 | Đổi sang `_scrape_tiktok_smart` |
| `elif platform_filter == "tiktok_global":` | ~460 | Đổi sang `_scrape_tiktok_smart` |
| `_scrape_direct_tiktok_videos(...)` được gọi nội bộ | đầu file | Đổi tên thành `_scrape_tiktokwm_fallback` |

## Hàm mới thêm vào `ag_trend.py`

```python
def _scrape_tiktok_smart(
    keyword: str = "",
    count: int = 12,
    nguon_goc: str = "tiktok_vn",
) -> list[TrendItem]:
    """
    Apify primary → TikWM fallback duy nhất.
    
    Decision matrix:
        Apify OK                → return Apify results
        Apify raise ApifyError  → log + return TikWM results
        Apify raise Exception   → log + return TikWM results
        TikWM cũng fail/empty   → return [] (giữ behavior cũ)
    """
    start = time.monotonic()
    try:
        items = scrape_tiktok_apify(
            keyword=keyword,
            count=count,
            mode="search",
            nguon_goc=nguon_goc,
        )
        logger.info(
            "tiktok_source_apify",
            extra={
                "source": "apify",
                "nguon_goc": nguon_goc,
                "items_count": len(items),
                "duration_ms": int((time.monotonic() - start) * 1000),
            },
        )
        return items
    except ApifyError as e:
        reason = f"apify_error:{type(e).__name__}"
        logger.warning(
            "tiktok_source_fallback",
            extra={
                "source": "tiktokwm",
                "reason": reason,
                "error_msg": str(e)[:200],
            },
        )
    except Exception as e:  # noqa: BLE001
        reason = f"unexpected:{type(e).__name__}"
        logger.warning(
            "tiktok_source_fallback",
            extra={
                "source": "tiktokwm",
                "reason": reason,
                "error_msg": str(e)[:200],
            },
        )

    # Fallback duy nhất
    return _scrape_tiktokwm_fallback(keyword=keyword, count=count)
```

## Đổi tên TikWM cũ

```python
# Cũ:
def _scrape_direct_tiktok_videos(keyword: str = "", count: int = 12) -> list[TrendItem]:

# Mới:
def _scrape_tiktokwm_fallback(keyword: str = "", count: int = 12) -> list[TrendItem]:
    """FALLBACK ONLY — gọi khi Apify fail. Không nên dùng trực tiếp."""
```

**Không đổi logic** bên trong TikWM — chỉ rename để đảm bảo grep thấy.

## Sửa call sites

### Site 1: `tiktok_vn`

```python
# Trước:
if platform_filter == "tiktok_vn":
    results = _scrape_direct_tiktok_videos(keyword=keyword)

# Sau:
if platform_filter == "tiktok_vn":
    results = _scrape_tiktok_smart(
        keyword=keyword,
        count=12,
        nguon_goc="tiktok_vn",
    )
```

### Site 2: `tiktok_global`

```python
# Trước:
elif platform_filter == "tiktok_global" or platform_filter == "predictive_global":
    tt = _scrape_direct_tiktok_videos(keyword=keyword, count=8)

# Sau:
elif platform_filter == "tiktok_global" or platform_filter == "predictive_global":
    tt = _scrape_tiktok_smart(
        keyword=keyword,
        count=8,
        nguon_goc="tiktok_global",
    )
```

## Import cần thêm

```python
# Đầu file ag_trend.py (nếu chưa có)
import time
from ca_agents.clients.apify_client import ApifyError
from ca_agents.sources.tiktok_apify_source import scrape_tiktok_apify
```

## Metric (optional, làm sau nếu có hạ tầng)

Nếu repo có sẵn Prometheus client (kiểm tra `apps/api/src/.../metrics*.py`):

```python
# Counter
TIKTOK_SOURCE_TOTAL = Counter(
    "tiktok_source_total",
    "Số lần scrape TikTok theo source",
    labelnames=["source", "nguon_goc", "status"],   # status: ok|empty|error
)
TIKTOK_FALLBACK_TOTAL = Counter(
    "tiktok_fallback_total",
    "Số lần rơi vào TikWM fallback",
    labelnames=["reason"],
)
```

Increment ở các điểm:
- Sau khi Apify return OK → `TIKTOK_SOURCE_TOTAL.labels(source="apify", ...).inc()`
- Khi vào fallback → `TIKTOK_SOURCE_TOTAL.labels(source="tiktokwm", ...).inc()` + `TIKTOK_FALLBACK_TOTAL.labels(reason=...).inc()`

Nếu chưa có Prometheus infra → bỏ qua metric, chỉ giữ logger (đã đủ cho debug).

## Kiểm tra "Phase done"

- [ ] `_scrape_direct_tiktok_videos` đã rename thành `_scrape_tiktokwm_fallback`
- [ ] `_scrape_tiktok_smart` đã thêm với logic Apify → TikWM
- [ ] 2 call sites đã sửa đúng
- [ ] Không còn chỗ nào gọi `_scrape_direct_tiktok_videos` (grep confirm)
- [ ] `import` mới đã thêm, không thừa
- [ ] `python -c "from ca_agents.ag_trend import scrape_trends"` không ImportError
- [ ] Smoke: gọi `scrape_trends(platform_filter="tiktok_vn")` không crash dù Apify fail (TikWM đỡ)

## Rollback plan

Nếu Phase 4 test fail nặng:
1. Revert import mới (giữ nguyên TikWM)
2. `_scrape_tiktok_smart` để nguyên không xóa (sẽ dùng ở phase sau)
3. Đổi call sites về gọi `_scrape_tiktokwm_fallback` trực tiếp
4. Re-run test xác nhận codebase vẫn pass

## Reference

- File: `packages/agents/src/ca_agents/ag_trend.py`
- Phase 2 output: `sources/tiktok_apify_source.py`
- Phase 2 output: `clients/apify_client.py`