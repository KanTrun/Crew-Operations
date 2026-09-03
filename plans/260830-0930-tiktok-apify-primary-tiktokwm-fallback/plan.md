---
title: "TikTok Apify primary + TikWM fallback duy nhất"
description: "Đổi nguồn cào TikTok chính sang Apify (clockworks/tiktok-scraper), giữ TikWM làm fallback duy nhất khi Apify fail. Có log/metric/runbook/test đầy đủ."
status: completed
priority: P2
effort: "0.5d"
tags: [ag-trend, tiktok, scraper, apify, fallback, refactor]
created: 2026-08-30
blockedBy: []
blocks: []
---

# TikTok Apify primary + TikWM fallback duy nhất

## Context

`ag_trend.py::_scrape_direct_tiktok_videos()` hiện đang gọi trực tiếp **TikWM** — một proxy scraping TikTok không chính thức, có 3 vấn đề:

1. **Không có SLA** — TikWM có thể chết bất cứ lúc, đổi schema JSON không báo trước.
2. **Bị giới hạn tính năng** — không crawl được hashtag listing, profile người dùng, music trending.
3. **Lỗi bị nuốt** — comment dùng `except Exception: pass`, không ai biết khi nào fail.

Trong khi đó Apify có **free $5/tháng** cho account mới, có actor `clockworks/tiktok-scraper` ổn định, hỗ trợ đủ các use case (search, hashtag, profile, video URL), có retry + captcha handling built-in.

**Quyết định kiến trúc:**
- Apify = primary (đường chính duy nhất)
- TikWM = fallback (chỉ chạy khi Apify raise error / trả rỗng)
- Không chain dài kiểu Apify → A2 → A3 → TikWM

## Brainstorm contract

| Field | Value |
|-------|-------|
| **Outcome** | Mọi call site TikTok trong `ag_trend.py` ưu tiên Apify; khi fail → TikWM fallback; có log/metric phân biệt rõ. |
| **Constraints** | Giữ interface `scrape_trends()` không đổi; giữ schema `TrendItem` không đổi; `.env` pattern đồng nhất với Facebook (`APIFY_TOKEN`); test song song với code (TDD-friendly). |
| **Non-goals** | Đổi sang TikTok Official API; tự host proxy rotation; viết Apify actor riêng; migrate sang actor khác ngoài `clockworks/tiktok-scraper`. |
| **Acceptance** | Apify là primary path; TikWM chỉ chạy khi Apify fail; có metric Prometheus `apify_call_total` + `apify_fallback_total`; test unit+integration xanh; runbook ghi rõ khi nào đổi token/quota. |

## Phases

| # | Phase | Status | Depends |
|---|-------|--------|---------|
| 1 | [Chuẩn bị Apify & schema mapping](./phase-01-chuan-bi-apify.md) | Completed | — |
| 2 | [Adapter Apify client + TikTok source](./phase-02-adapter-apify-client.md) | Completed | 1 |
| 3 | [Refactor ag_trend.py với fallback](./phase-03-refactor-ag-trend.md) | Completed | 2 |
| 4 | [Test unit + integration + smoke](./phase-04-test-day-du.md) | Completed | 3 |
| 5 | [Runbook + rollout](./phase-05-runbook-rollout.md) | Completed | 4 |

## Success Criteria

- [x] TikWM chỉ chạy khi Apify raise `ApifyError` hoặc dataset rỗng
- [x] Có log JSON phân biệt `source=apify` vs `source=tiktokwm` kèm `duration_ms`
- [x] Metric Prometheus / log: `apify_call_total{status}` + `apify_fallback_total{reason}`
- [x] Test unit mock Apify response ≥ 90% coverage cho `sources/tiktok_apify_source.py` (19 unit tests pass)
- [x] Test integration gọi thật 1 keyword VN xanh
- [x] Test fallback path (giả lập Apify fail → verify TikWM được gọi, 3 tests pass)
- [x] Runbook `docs/runbooks/tiktok-scraping.md` liệt kê: token hết hạn, quota, schema break
- [x] `.env.example` có đủ `APIFY_TOKEN`, `APIFY_TIKTOK_ACTOR_ID`, `TIKTOK_APIFY_TIMEOUT_S`
- [x] Không phá vỡ API cũ: `platform_filter=tiktok_vn|global` vẫn hoạt động
- [ ] Apify trả về ≥80% tổng số TrendItem TikTok (metric cần chạy quán thật 7 ngày)

## Risks

| Risk | Signal | Response |
|------|--------|----------|
| Hết Apify $5 giữa tháng | `apify_call_total{status=quota_exceeded}` tăng | Fallback TikWM đang chạy; có alert Prometheus; doc trong runbook |
| Apify actor đổi schema | Items count = 0 + log "ApifyError: empty dataset" | Pin version actor: `clockworks/tiktok-scraper~1.0.0` trong `.env` |
| TikWM chết đột ngột | Fallback fail, list rỗng | Giữ mock data dự phòng (giữ behavior cũ); warning log |
| Apify latency > 90s | Polling timeout | Tăng `TIKTOK_APIFY_TIMEOUT_S` trong `.env`; cân nhắc async dispatch |
| Token lộ trong log | Lint fail hoặc GitHub secret scan | Mask trong logger; không log full payload |

## Out of scope

- Thay đổi call sites ngoài `ag_trend.py`
- Thêm use case mới (hashtag deep, KOL profile) — Phase 2 chỉ mapping use case search/feed hiện có
- Tối ưu chi phí Apify compute units
- Viết test cho các nguồn khác (Google Trends, Threads, Showbiz)

<!-- slug: tiktok-apify-primary-tiktokwm-fallback -->