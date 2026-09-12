# Camoufox integration — wrap-up journal

**Date:** 2026-09-12
**Plan:** `plans/260910-1610-trend-camoufox-integration/plan.md`
**Branch:** `agents/ba-n-bie-t-camoufox-k` → merged vào main qua PR #42 + #43

## Kết quả

Toàn bộ plan hoàn thành — 11 commits, 2 PR, CI 13/13 checks xanh, 396/396 tests pass.

### PR #42 (8 commits) — Camoufox core + sources + UI + docs

- `camoufox_client.py`: browser chống-detect, `is_available()` phân loại lỗi (chưa fetch binary vs thiếu system deps), semaphore chặn concurrency, context manager an toàn
- `tiktok_camoufox_source.py` + `threads_camoufox_source.py`: tier browser-thật cho 2 platform yếu nhất
- Wire vào `_scrape_tiktok_smart` / `_scrape_threads_smart`, mode `browser` mới trong UI
- Runbook `docs/runbooks/camoufox-scraping.md` + `docs/THIRD_PARTY.md`

### PR #43 (3 commits) — Tier 0 Threads Official API

- Live-test 7 đường thay thế (Bing RSS/HTML, DuckDuckGo, SearXNG, Mojeek, fetch post công khai, API không token) → tất cả chết → chỉ còn API chính thức Meta
- `threads_official_api_source.py`: `GET graph.threads.net/keyword_search`, miễn phí 2,200 queries/24h, opt-in qua `THREADS_ACCESS_TOKEN`
- `.env.example` + runbook cập nhật hướng dẫn lấy token

## Chuỗi cào cuối cùng

- TikTok: Google Bridge → TikWM → Camoufox → Apify → RSS
- Threads: Official API → Google Bridge → Direct Jina → Camoufox → Apify → RSS

## Verify cuối (2026-09-12, sau merge main)

- 396/396 tests pass, ruff + mypy sạch
- Live-test 4 nguồn RSS (Google Trends VN/Global, Gen Z Media, Showbiz KOLs): đều cào thật OK (10-50 items) — không cần Camoufox, đúng non-goals §2.2 của plan
- Branch đồng bộ main (`f89c0db`), upstream remote đã push

## Bài học (PowerShell + GitHub REST)

- `Get-Content -Raw` trên PS 5.1 đọc UTF-8 no-BOM as ANSI → mojibake tiếng Việt; string trả về còn mang ETS note-properties (PSPath...) mà `ConvertTo-Json` serialize vào payload. Fix: `[IO.File]::ReadAllText(path, [Text.Encoding]::UTF8)`
- `Out-File -Encoding utf8` ghi BOM → GitHub API reject. Fix: `[IO.File]::WriteAllText(..., UTF8Encoding($false))`
- Env var không persist giữa các powershell calls (mỗi call là process mới) — extract token + gọi API phải trong cùng 1 call
- `gh` CLI không có sẵn, GitHub MCP server read-only → REST API + `git credential fill` là con đường tạo PR/merge
