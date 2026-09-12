# Runbook: Camoufox scraping (browser thật chống-detect cho AG-TREND)

## Tổng quan

Camoufox là **Firefox custom build chống fingerprint** (spoof ở tầng C++/Rust, không phải JS inject), điều khiển qua Playwright API. Nó là tier cào **miễn phí, khó bị chặn** nằm giữa các nguồn free (Google Bridge / TikWM / Jina direct) và Apify (tốn tiền).

Chuỗi cào mới sau khi có Camoufox (plan §3.5):

```
TikTok:   Google Bridge → TikWM → [Camoufox nếu available] → Apify → RSS
Threads:  [Official API nếu có token] → Google RSS → Jina → [Camoufox nếu available] → Apify → RSS
```

Mode UI tương ứng:

| Mode UI | Hành vi |
|---|---|
| `auto` | Chuỗi đầy đủ ở trên — Camoufox chỉ chạy khi các nguồn free phía trước fail |
| `direct_only` | **Khóa hoàn toàn** Camoufox + Apify, chỉ nguồn free |
| `browser` | Camoufox **FIRST**; fail thì rớt xuống chuỗi cũ |
| `apify_force` | Apify first, bỏ qua Camoufox |

**Nguyên tắc:**
- Camoufox **không bao giờ là single point of failure** — `is_available()` check trước, fail thì rớt tầng
- Login-wall (TikTok/Threads đòi đăng nhập) → raise `CamoufoxUnavailable` → rớt tầng NGAY, **không cố vượt** (plan §2.3)
- Mỗi request chạy trong threadpool riêng + semaphore giới hạn đồng thời (default 2)

## Setup ban đầu

### 1. Cài package + browser

```bash
pip install "camoufox[geoip]"
camoufox fetch          # tải binary Firefox ~300MB, chạy 1 LẦN duy nhất
```

Verify binary đã tải:

```bash
python -c "from camoufox.pkgman import installed_verstr; print(installed_verstr())"
```

### 2. System dependencies (chỉ cần trên Linux server)

Camoufox là Firefox thật → cần libs GUI kể cả khi chạy headless. Trên **Debian/Ubuntu**:

```bash
sudo apt-get install -y \
  libgtk-3-0 libasound2 libdbus-glib-1-2 libx11-xcb1 \
  libxcomposite1 libxdamage1 libxrandr2 libatk1.0-0 libatk-bridge2.0-0 \
  libpango-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
  fonts-liberation fonts-noto-color-emoji
```

> Windows/macOS dev machine: không cần bước này.

### 3. Cấu hình `.env` (tùy chọn — mọi biến đều có default)

```bash
# packages/agents/.env hoặc .env của deployment
CA_CAMOUFOX_ENABLED=true          # default true; false = tắt hẳn tier Camoufox
CA_CAMOUFOX_MAX_CONCURRENT=2      # semaphore: số browser đồng thời tối đa
CA_CAMOUFOX_TIMEOUT_S=45           # timeout 1 lần load page
CA_CAMOUFOX_RETRIES=2              # số retry khi browser crash/timeout
CA_CAMOUFOX_CACHE_TTL_S=600       # TTL cache kết quả (10 phút)
```

### 4. Verify từ code

```bash
python -c "from ca_agents.clients.camoufox_client import is_available; print(is_available())"
```

- `True` → tier Camoufox sẽ tự kích hoạt trong chuỗi `auto`
- `False` → kiểm tra `pip show camoufox` và `camoufox fetch`

## Threads Official API (Tier 0 — nguồn chính thức miễn phí)

Meta đã mở **keyword search trên Threads API chính thức** — đây là đường đáng tin nhất để cào Threads, miễn phí, không cần browser.

### Cách hoạt động

- Endpoint: `GET https://graph.threads.net/v1.0/keyword_search`
- Params: `q` (bắt buộc), `search_type` (TOP|RECENT), `search_mode` (KEYWORD|TAG), `limit` (max 100), `since`/`until`, `author_username`
- Rate limit: **2,200 queries / 24h** (queries trả 0 kết quả không tốn quota)
- Permissions: `threads_basic` + `threads_keyword_search`

### Cấu hình

```bash
# packages/agents/.env
THREADS_ACCESS_TOKEN=<token từ Graph API Explorer>
```

- **Chưa set token** → `is_configured()` trả False → tier bị skip hoàn toàn (không import, không delay)
- **Có token** → tier 0 chạy TRƯỚC Google Bridge trong mode `auto`/`apify_force`; mode `direct_only` khóa cả Official API; mode `browser` vẫn Camoufox first

### Cách lấy token

1. Tạo app tại https://developers.facebook.com/ → thêm product Threads
2. Thêm permissions `threads_basic` + `threads_keyword_search`
3. Test nhanh: dùng Graph API Explorer (https://developers.facebook.com/tools/explorer/) sinh short-lived token
4. **Lưu ý App Review:** app chưa qua review → chỉ search được posts của chính user; sau review → search toàn bộ public posts

### Sự cố thường gặp

| Triệu chứng | Nguyên nhân | Xử lý |
|---|---|---|
| `threads_official_api` log warning rồi rớt tầng | Token hết hạn / sai | Sinh token mới, update `THREADS_ACCESS_TOKEN` |
| Luôn trả `[]` | App chưa qua App Review → chỉ thấy posts của mình | Submit App Review cho `threads_keyword_search` |
| HTTP 400 Invalid OAuth | Token không hợp lệ | Kiểm tra token trong Graph API Explorer |

## Theo dõi hàng ngày

### Log cần quan sát

| Log event | Ý nghĩa |
|---|---|
| `tiktok_source_camoufox` | Camoufox OK cho TikTok, đếm `items_count` + `duration_ms` |
| `threads_source_camoufox` | Camoufox OK cho Threads, đếm `items_count` + `duration_ms` |
| `tiktok_camoufox_tier_failed_trying_apify` | Camoufox TikTok fail → rơi vào Apify |
| `threads_camoufox_tier_failed_trying_apify` | Camoufox Threads fail → rơi vào Apify |
| `camoufox_unavailable` | Package/binary chưa cài → tier bị skip |

### Metric đề xuất (nếu có Prometheus)

| Metric | Ý nghĩa | Alert khi |
|---|---|---|
| `camoufox_scrape_total{source="tiktok"\|threads"}` | Số lần Camoufox OK | — |
| `camoufox_scrape_duration_ms` | Latency 1 lần scrape | p95 > 30s |
| `camoufox_fail_total{reason="login_wall"}` | Bị đẩy về trang login | > 10 / 1h (nguồn siết chặn) |
| `camoufox_fail_total{reason="timeout"}` | Browser timeout | > 5 / 1h |
| `camoufox_fail_total{reason="crash"}` | Browser crash | ≥ 1 / 1h |

### Health check nhanh

```bash
# Trên server, kiểm tra tier có sống không
python -c "
from ca_agents.clients.camoufox_client import is_available
print('camoufox:', 'OK' if is_available() else 'NOT INSTALLED')
"
```

## Sự cố thường gặp

### 🔴 Log: `camoufox_unavailable` / `is_available()=False`

**Nguyên nhân:** Chưa `pip install camoufox[geoip]` hoặc chưa chạy `camoufox fetch`

**Cách xử lý:**
1. `pip show camoufox` — nếu không có → install
2. `camoufox fetch` — tải binary (~300MB, chạy 1 lần)
3. Verify lại bằng lệnh health check ở trên
4. Trong lúc đó hệ thống **vẫn hoạt động bình thường** — tier bị skip, rơi xuống Apify

### 🔴 Log: `CamoufoxUnavailable: ... yêu cầu đăng nhập (login-wall)`

**Nguyên nhân:** TikTok/Threads redirect về trang login — nguồn đang siết chặn anonymous scraping

**Cách xử lý:**
1. **KHÔNG cố vượt** — đây là ranh giới phạm vi đã chốt (plan §2.3)
2. Kiểm tra tần suất: nếu thưa dần → nguồn đang A/B test, chờ 1-2h
3. Nếu dày đặc (>10 lần/giờ) → nguồn siết chặn thật, dựa vào Apify tạm thời
4. Theo dõi issue Camoufox: https://github.com/daijro/camoufox/issues

> **Lưu ý Threads (live-test 2026-09-10):** Threads search hiện **login-wall mềm** —
> URL vẫn ở `/search` nhưng trang chỉ hiển thị link "Log in with username instead",
> không render post nào cho khách chưa đăng nhập. Code đã có fast-fail: chờ post
> HOẶC login-link, nếu login-link thắng → grace-wait 3s xác nhận → raise
> `CamoufoxUnavailable` ngay (~10s thay vì 30s). Đây là hành vi **đúng thiết kế** —
> tier Threads rớt xuống Apify, không phải bug.

### 🟡 Log: `camoufox timeout` / scrape > 45s

**Nguyên nhân:** Máy chủ yếu (Camoufox nặng hơn HTTP client ~10x) hoặc mạng chậm

**Cách xử lý:**
1. Tăng `CA_CAMOUFOX_TIMEOUT_S=90` trong `.env`
2. Giảm `CA_CAMOUFOX_MAX_CONCURRENT=1` nếu CPU nghẽn
3. Kiểm tra RAM: mỗi browser instance ~500MB-1GB
4. Nếu server < 2GB RAM → cân nhắc tắt tier: `CA_CAMOUFOX_ENABLED=false`

### 🔴 Browser crash liên tục (`reason="crash"`)

**Nguyên nhân:** Thiếu system libs (Linux) hoặc binary version mismatch

**Cách xử lý:**
1. Chạy lại lệnh apt-get install ở mục Setup §2
2. `camoufox fetch` lại để cập nhật binary
3. Test thủ công:
   ```bash
   python -c "
   from camoufox.sync_api import Camoufox
   with Camoufox(headless=True) as browser:
       page = browser.new_page()
       page.goto('https://example.com')
       print('OK:', page.title())
   "
   ```

### 🟡 Kết quả Camoufox rỗng nhưng không lỗi

**Nguyên nhân:** DOM của TikTok/Threads thay đổi → selector cũ không match

**Cách xử lý:**
1. Mở URL search bằng tay, inspect DOM mới
2. Update selector trong:
   - `packages/agents/src/ca_agents/sources/tiktok_camoufox_source.py` (`_VIDEO_SELECTOR`)
   - `packages/agents/src/ca_agents/sources/threads_camoufox_source.py` (`_POST_SELECTOR`)
3. Chạy test fixture: `pytest packages/agents/tests/test_tiktok_camoufox_source.py -q`

> **⚠️ Bẫy serialization attr (phát hiện live-test 2026-09-10):** `page.content()`
> của Playwright serialize attribute bằng **nháy kép** `data-e2e="..."`. Mọi
> regex/split HTML trong source PHẢI dùng nháy kép — nháy đơn sẽ không match
> dù DOM đúng. Selector cho `wait_for_selector` (CSS) thì vẫn dùng nháy đơn
> như bình thường.

> **DOM TikTok search live 2026-09-10 (đã verify hoạt động):** khối video là
> `data-e2e="search_top-item"` (không còn `search_video-item`); caption trong
> `data-e2e="search-card-video-caption"`; views trong `data-e2e="video-views"`;
> display name trong `data-e2e="search-card-user-unique-id"`. Search page
> CHỈ hiển thị views — likes/comments được ước lượng (~10%/~2% views) và đánh
> dấu "ước lượng" trong `diem_nhan_dac_biet`.

### 🔴 CPU/RAM server nghẽn khi bật browser mode

**Nguyên nhân:** Nhiều user cùng chọn mode `browser` + semaphore lỏng

**Cách xử lý:**
1. Giảm `CA_CAMOUFOX_MAX_CONCURRENT` (default 2 → 1)
2. Giảm `CA_CAMOUFOX_RETRIES` (default 2 → 1)
3. Tắt hẳn nếu cần: `CA_CAMOUFOX_ENABLED=false` — UI vẫn hiện nút nhưng sẽ rớt tầng

## Khi nào cần dev can thiệt

| Tình huống | Action của dev |
|---|---|
| DOM TikTok/Threads đổi → selector fail | Update `_POST_SELECTOR` + fixture HTML trong test |
| Camoufox release mới đổi API | Update `camoufox_client.py` (layer duy nhất gọi Camoufox) |
| Cần nguồn mới (Instagram, X,...) | Copy pattern `threads_camoufox_source.py`: fetch/extract tách bạch, tái dùng `_parse_count`, `_detect_category` |
| Cần geo-spoof theo IP proxy | Mở rộng `scrape_page()` với param `proxy=` của Camoufox |
| Server không đủ RAM | Cân nhắc chuyển sang Camoufox trên worker riêng / container riêng |

## Cost & performance reference

| Hoạt động | Chi phí | Latency |
|---|---|---|
| 1 lần scrape Camoufox | **0đ** | ~3-10s (chậm hơn HTTP client ~10x) |
| 1 lần scrape Apify | ~0.5-2 CU ($5 free/tháng) | ~10-30s |

**Đánh đổi:** Camoufox miễn phí + khó chặn, đổi lại nặng RAM (~500MB-1GB/instance) và chậm. Đó là lý do nó là tier **trung gian**, không phải primary.

## Reference

- Plan: `plans/260910-1610-trend-camoufox-integration/plan.md`
- Code client: `packages/agents/src/ca_agents/clients/camoufox_client.py`
- Code TikTok: `packages/agents/src/ca_agents/sources/tiktok_camoufox_source.py`
- Code Threads: `packages/agents/src/ca_agents/sources/threads_camoufox_source.py`
- Code Threads Official API: `packages/agents/src/ca_agents/sources/threads_official_api_source.py`
- Wire: `packages/agents/src/ca_agents/ag_trend.py::_scrape_tiktok_smart` + `::_scrape_threads_smart`
- Test: `packages/agents/tests/test_camoufox_client.py`, `test_tiktok_camoufox_source.py`, `test_threads_camoufox_source.py`, `test_threads_official_api_source.py`
- Threads keyword search docs: https://developers.facebook.com/docs/threads/keyword-search
- Camoufox docs: https://camoufox.com/
- Camoufox repo: https://github.com/daijro/camoufox

## Lịch sử thay đổi

| Ngày | Tác giả | Thay đổi |
|---|---|---|
| 2026-09-10 | AI assistant | Tạo runbook (kèm plan tích hợp Camoufox vào AG-TREND) |
| 2026-09-10 | AI assistant | Live-test: TikTok DOM mới `search_top-item` (đã hoạt động, 5 items thật); Threads login-wall mềm → fast-fail ~10s; ghi chú bẫy serialization nháy kép |
| 2026-09-10 | AI assistant | Thêm Tier 0 Threads Official API keyword search (graph.threads.net, miễn phí 2,200 queries/24h) — live-test 7 đường thay thế đều chết, chỉ Official API là khả thi |
