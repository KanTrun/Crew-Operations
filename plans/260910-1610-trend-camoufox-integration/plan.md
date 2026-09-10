# Kế hoạch — Tích hợp Camoufox vào AG-TREND (cào dữ liệu xu hướng bằng browser thật chống-detect)

> **Ngày:** 2026-09-10 · **Bản:** v2 (đã review kỹ thuật) · **Nhánh đề xuất:** `feat/agents-camoufox-integration`
> **Bám chuẩn:** ADR-002 (điều phối tất định) · ADR-003 (contracts-first) · ADR-008 (chống tín hiệu giả, người quyết)
> **Vùng sở hữu:** C (agents, sources) + B (API trends) + D (web page-quan)
> **Trạng thái:** Đề xuất — chờ duyệt trước khi PR 1

---

## Đổi so với bản gốc (v1 → v2)

| # | Vấn đề trong v1 | Sửa trong v2 |
|---|-----------------|--------------|
| 1 | Chưa chốt mô hình sync/async cho browser launch | §3.2 chốt: sync + threadpool riêng, không đụng route FastAPI |
| 2 | Không giới hạn số browser launch song song | Thêm semaphore `CA_CAMOUFOX_MAX_CONCURRENT` |
| 3 | Thiếu rủi ro pháp lý/ToS | Thêm vào bảng rủi ro §VI, cần người duyệt chấp nhận |
| 4 | Thiếu system deps cho headless Firefox trong container | Thêm vào runbook + PR 1 |
| 5 | Extractor không tách bạch khỏi browser → khó test selector | Tách `fetch()` / `extract()`, test bằng fixture HTML |
| 6 | Không có retry trong tier trước khi rớt tầng | Thêm retry 1 lần có backoff ngắn |
| 7 | Cache TTL trùng chu kỳ scan → cache vô dụng | Tách TTL riêng cho Camoufox (10–15 phút) |
| 8 | Ước lượng PR lạc quan | Điều chỉnh 1–2 ngày cho PR 2/3 |
| 9 | TikTok source không nói rõ tái dùng helper chung | Nhất quán với Threads ở §3.3 |
| 10 | Observability chỉ có counter | Thêm latency histogram + phân loại lỗi |

---

# PHẦN I — NGỮ CẢNH

## 1.1. Dự án

**NHỊP QUÁN** (repo KanTrun/Crew-Operations) — hệ sinh thái AI agent vận hành quán cà phê. Monorepo: `apps/api` (FastAPI), `apps/web` (Next.js PWA), `packages/agents` (10 agent Lô 1), `packages/contracts` (JSON Schema/TS types). Triết lý cốt lõi: orchestration tất định không LLM (ADR-002), contracts-first (ADR-003), agent chỉ trích xuất — người quyết (ADR-008).

## 1.2. Chức năng cào dữ liệu hiện tại (AG-TREND)

**Luồng end-to-end:**

```
UI page-quan/page.tsx (mode selector 3 nút)
  → GET /api/v1/trends/radar?region=&category=&keyword=&mode=
  → fetch_trend_radar()  [ag_trend.py:781]
  → chuỗi source theo platform → list[TrendItem] → serialize về UI
```

**Chuỗi source hiện tại:**

| Platform | Chuỗi (thứ tự gọi) | Vị trí code |
|----------|--------------------|-------------|
| TikTok VN | TikWM (primary, 0đ) → Apify (backup, tốn CU) | `ag_trend.py:118` `_scrape_tiktok_smart` |
| Threads VN | Google News RSS bridge → Jina Reader (`r.jina.ai`) → Apify → RSS fallback | `ag_trend.py:682` `_scrape_threads_smart` |
| Google Trends VN / Global | `urllib` + RSS trực tiếp | `_scrape_google_trends_vn`, `_scrape_google_trends_global` |
| Showbiz & KOLs | `urllib` scrape trực tiếp | `_scrape_showbiz_kols_vn` |

**3 scrape_mode hiện có** (UI `page.tsx:655-700`): `auto` (Tự động), `direct_only` (100% miễn phí, khóa Apify), `apify_force` (ép Apify).

**File nguồn liên quan:**

- `packages/agents/src/ca_agents/ag_trend.py` — orchestrator + TrendItem dataclass
- `packages/agents/src/ca_agents/sources/` — `tiktok_apify_source.py`, `threads_apify_source.py`, `threads_direct_source.py`, `threads_google_bridge_source.py`
- `packages/agents/src/ca_agents/clients/apify_client.py` — pattern client tham chiếu
- `apps/api/src/ca_api/interfaces/http/trends.py` — router `/api/v1/trends/radar`
- `apps/web/src/app/page-quan/page.tsx` — UI mode selector
- `docs/runbooks/tiktok-scraping.md` — runbook chuỗi cào hiện tại

## 1.3. Điểm yếu hiện tại — lý do cần Camoufox

1. **Không có browser thật**: toàn bộ cào bằng `urllib` + `User-Agent: Chrome/122` hard-code (`threads_direct_source.py:26-33`), thậm chí `ssl.CERT_NONE`. Threads/Meta/TikTok có bot-detection mạnh → 403/captcha bất kỳ lúc nào.
2. **Không render được JS**: TikTok search page và Threads search là SPA — `urllib` chỉ thấy HTML rỗng.
3. **Phụ thuộc trung gian**: Jina Reader (rate-limit, không SLA) và Apify (tốn CU, free $5/tháng).
4. **Dữ liệu Threads hiện phần lớn là fallback curated hard-code** (nhóm `curated_hot_threads` trong `threads_direct_source.py`) — không phải dữ liệu thật.

## 1.4. Camoufox là gì

Firefox custom build chống fingerprint-detection: spoof ở mức **C++/Rust** (canvas, WebGL, fonts, navigator, screen) chứ không chỉ JS-injection như Puppeteer/Playwright thường. API Python chính thức qua Playwright.

- Cài: `pip install camoufox[geoip]` + `camoufox fetch` (tải binary ~300MB)
- License MPL-2.0 (browser) — dùng như tool bên ngoài, không sửa source
- `geoip=True` tự đồng bộ fingerprint với IP VN; `humanize=True` mô phỏng chuyển động chuột người

**Lưu ý deploy quan trọng (bổ sung v2):** `camoufox fetch` chỉ tải binary Firefox custom — không cài các system library mà Firefox headless cần để *chạy được* trên Linux server (`libgtk-3-0`, `libasound2`, `libdbus-glib-1-2`, `libx11-xcb1`, fonts...). Đây là điểm chặn thực tế phổ biến hơn "chưa tải binary". `is_available()` (§3.2) cần phân biệt hai lỗi này để log hướng dẫn đúng.

---

# PHẦN II — MỤC TIÊU & NON-GOALS

## 2.1. Mục tiêu

1. Thêm tier cào **browser-thật, miễn phí, khó bị chặn** cho 2 platform yếu nhất: **TikTok** và **Threads**.
2. Giảm phụ thuộc Apify (tiết kiệm CU) và Jina Reader.
3. Graceful degradation: chưa cài Camoufox → chuỗi fallback chạy y như cũ, **không phá CI/Docker/test hiện tại**.

## 2.2. Non-goals

- Không thay Google Trends/Showbiz (RSS đã ổn, không cần browser).
- Không cào có login (Threads/TikTok đều dùng public search, không tài khoản).
- Không đổi schema `TrendItem` (ADR-003: không cần DTO mới).
- Không bake binary Camoufox vào Docker image mặc định (image phình +300MB).
- Không giữ browser singleton v1 (tránh thread-safety với FastAPI threadpool — tối ưu phase sau).
- **Không cào nội dung sau login-wall hoặc dữ liệu không public** (bổ sung v2 — ranh giới rõ cho §2.3 dưới).

## 2.3. Ràng buộc phạm vi cào (bổ sung v2)

Vì Camoufox né được bot-detection tốt hơn hẳn `urllib`, cần chốt ranh giới rõ ràng để tránh "vì làm được nên làm":

- Chỉ cào **search page public**, không đăng nhập, không lưu cookie/session giữa các lần chạy.
- Tôn trọng nhịp độ hợp lý: không cào dồn dập hơn chu kỳ scan hiện có (≥ 5 phút/lần theo keyword).
- Không retry vô hạn khi bị chặn — rớt tầng ngay theo chuỗi fallback, không cố "vượt" captcha.
- Quyết định bật mode `browser` trong môi trường production là quyết định của người vận hành (ADR-008), không phải mặc định.

---

# PHẦN III — THIẾT KẾ

## 3.1. Kiến trúc chèn (theo đúng pattern source hiện có)

```
packages/agents/src/ca_agents/
├── clients/
│   ├── apify_client.py          # (có sẵn — pattern tham chiếu)
│   └── camoufox_client.py       # MỚI — lifecycle browser, availability, timeout, concurrency
└── sources/
    ├── tiktok_camoufox_source.py    # MỚI — fetch_tiktok_page() + extract_tiktok_items()
    └── threads_camoufox_source.py   # MỚI — fetch_threads_page() + extract_threads_items()
```

**Chuỗi mới sau tích hợp:**

```
TikTok:   TikWM → [Camoufox nếu có] → Apify
Threads:  Google RSS → Jina → [Camoufox nếu có] → Apify → RSS
Mode mới: browser — Camoufox FIRST, TikWM/Jina làm backup
```

## 3.2. `camoufox_client.py` — thiết kế chi tiết

```
"""Camoufox browser lifecycle wrapper — optional dependency.

Public API:
    CamoufoxUnavailable        -- raise khi chưa cài `camoufox`, chưa `camoufox fetch`,
                                   HOẶC thiếu system deps để launch (phân biệt rõ trong message).
    is_available() -> bool     -- check nhanh: import + binary + thử launch/close rỗng, cache kết quả 1 lần/process.
    scrape_page(url, extractor, timeout_s) -> Any
                                  -- launch browser → goto → extractor(page) → close, có retry + concurrency guard.
"""
```

**Điểm chính (v2 — bổ sung so với v1):**

- **Mô hình thực thi:** hàm `scrape_page` là **sync** và được gọi từ code sync hiện có trong `ag_trend.py`. Route FastAPI gọi `fetch_trend_radar()` phải chạy qua threadpool riêng (không dùng threadpool mặc định của Starlette — pool đó không được thiết kế cho tác vụ nặng như launch trình duyệt). Dùng một `ThreadPoolExecutor` chuyên biệt kích thước nhỏ (khớp với `CA_CAMOUFOX_MAX_CONCURRENT`) để offload. Quyết định này chốt ngay ở PR 1, không để "phase sau" vì nó quyết định chữ ký hàm.
- **Concurrency guard:** `threading.Semaphore(CA_CAMOUFOX_MAX_CONCURRENT)` (default 2) bao quanh phần launch browser. Vượt giới hạn → chờ hoặc timeout sớm với lỗi rõ ràng, không launch vô hạn Firefox process song song (rủi ro OOM worker).
- **Retry nội tại:** 1 lần retry với backoff ngắn (~1s) cho lỗi timeout/network trước khi raise ra ngoài để chuỗi rớt tầng — tránh rớt xuống Apify (tốn CU) chỉ vì 1 lần flake mạng.
- **Lazy import** `camoufox` trong hàm → `ImportError` map thành `CamoufoxUnavailable` (lý do: "chưa cài package") → tier chuỗi skip sang nguồn kế tiếp, log `camoufox_unavailable_skipping` kèm lý do cụ thể (chưa cài / chưa fetch binary / thiếu system deps / launch lỗi khác).
- **Env config**: `CA_CAMOUFOX_ENABLED` (default `1` nếu đã cài), `CA_CAMOUFOX_HEADLESS` (default `1`), `CA_CAMOUFOX_TIMEOUT_S` (default `45`), `CA_CAMOUFOX_MAX_CONCURRENT` (default `2`), `CA_CAMOUFOX_CACHE_TTL_S` (default `600` — xem §3.3).
- **Launch per-call** v1 (đơn giản, đúng tinh thần fail-closed): `Camoufox(headless=..., geoip=True, humanize=True)`. Đóng browser trong `finally`, kể cả khi extractor raise.

## 3.3. `tiktok_camoufox_source.py`

- Vào `https://www.tiktok.com/search?q={keyword}` (hoặc `/tag/{hashtag}`), chờ selector video, extract từ DOM: caption, author, stats (play/like/comment), link.
- **Tách bạch fetch/extract (bổ sung v2):** `fetch_tiktok_page(page, keyword)` chỉ điều hướng + chờ selector, trả về HTML/DOM handle. `extract_tiktok_items(html_or_dom) -> list[TrendItem]` là hàm **thuần**, không phụ thuộc Playwright — test được bằng fixture HTML tĩnh (`tests/fixtures/tiktok_search_sample.html`) mà không cần mock sâu vào Playwright API. Khi TikTok đổi DOM, chỉ cần cập nhật fixture + extractor, không đụng phần browser lifecycle.
- **Map field thống nhất với Apify (bổ sung v2):** tái dùng cùng hàm parse số liệu dạng "12.3K"/"1.2M" và `_detect_category`/lifecycle helper đang dùng trong `tiktok_apify_source.py` — không viết lại logic parse riêng cho tier này (nhất quán với cách Threads Camoufox tái dùng ở §3.4).
- Cache in-memory theo `CA_CAMOUFOX_CACHE_TTL_S` (mặc định 10 phút — xem lý do ở §3.3-bis dưới), key gồm keyword + region.

### 3.3-bis. Cache TTL (sửa v2)

Bản v1 dùng chung pattern cache 5 phút như `_TIKTOKWM_CACHE`, nhưng chu kỳ auto-scan cũng ~5 phút → cache gần như luôn miss đúng lúc cần, mất tác dụng cho tier tốn kém nhất (launch browser). v2 tách `CA_CAMOUFOX_CACHE_TTL_S` riêng, mặc định 10 phút, độc lập với TTL của TikWM/Jina.

## 3.4. `threads_camoufox_source.py`

- Vào `https://www.threads.net/search?q={keyword}&serp_type=default` — Threads public search render được không cần login (Camoufox vượt checkpoint Meta tốt hơn urllib).
- Cùng cấu trúc tách `fetch_threads_page()` / `extract_threads_items()` như TikTok ở §3.3.
- Extract: username, text post, post URL, like/reply count → `TrendItem`, tái dùng `_detect_category` + `_assess_trend_lifecycle` (import từ `threads_direct_source` — không copy code).
- Nếu Threads redirect về màn login (một số vùng/IP có thể ép login) → coi là `CamoufoxUnavailable` cho lần gọi đó, rớt tầng ngay, **không cố đăng nhập hay vượt qua** (đúng §2.3).

## 3.5. Wire vào `ag_trend.py` + mode mới

- `_scrape_tiktok_smart`: chèn block Camoufox **giữa TikWM và Apify** (chỉ khi `is_available()`), chạy qua threadpool riêng (§3.2).
- `_scrape_threads_smart`: chèn **giữa Jina direct và Apify**.
- Thêm mode `"browser"`: Camoufox first → chuỗi cũ làm backup.
- **Ngân sách timeout tổng (bổ sung v2):** vì chuỗi mới có thể xếp chồng TikWM (timeout ngắn) → Camoufox (45s) → Apify (timeout riêng), cần đặt trần tổng thời gian cho toàn bộ `fetch_trend_radar()` mỗi platform (đề xuất 90s) để tránh request UI treo quá lâu khi rớt qua nhiều tầng liên tiếp.

## 3.6. UI — thêm nút mode thứ 4

`page.tsx:655-700`: thêm option `browser` — "🦊 Camoufox (Browser thật)" desc "Cào bằng Firefox chống-detect, miễn phí, khó bị chặn — chậm hơn (~3-10s/lượt)". Sửa type `scrapeMode` state (dòng 146, 207) thêm `"browser"`. Text status quét thêm nhánh hiển thị mode, và hiển thị rõ khi server trả rỗng do `camoufox_unavailable` (khác với "không có kết quả").

---

# PHẦN IV — KẾ HOẠCH THỰC THI THEO PR

## PR 1 — `feat/agents-camoufox-client` (nền tảng, ~1–1.5 ngày)

1. Tạo `clients/camoufox_client.py` (`CamoufoxUnavailable` với lý do phân loại rõ, `is_available()`, `scrape_page()` có semaphore + retry, threadpool executor riêng).
2. Unit test: mock `camoufox` module — test ImportError path, thiếu-binary path, launch-lỗi-system-deps path, timeout path, retry path, extractor được gọi, browser luôn đóng kể cả khi lỗi, concurrency guard chặn đúng số lượng.
3. Ghi `docs/THIRD_PARTY.md` thêm dòng Camoufox (MPL-2.0, binary ~300MB, optional — cài: `pip install camoufox[geoip] && camoufox fetch`), kèm ghi chú system deps Linux cần thêm cho container.
4. `.env.example` thêm 5 var `CA_CAMOUFOX_*` (bao gồm `MAX_CONCURRENT`, `CACHE_TTL_S`).

## PR 2 — `feat/agents-tiktok-camoufox-source` (~1.5–2 ngày)

1. `sources/tiktok_camoufox_source.py` (fetch/extract tách bạch) + fixture HTML mẫu + export trong `sources/__init__.py`.
2. Wire vào `_scrape_tiktok_smart` (giữa TikWM → Apify) + log event `tiktok_source_camoufox` theo pattern log hiện có, kèm latency + lý do lỗi nếu rớt tầng.
3. Test: mock `scrape_page` cho phần lifecycle; test `extract_tiktok_items` bằng fixture HTML tĩnh (không mock Playwright); test chuỗi skip khi unavailable; test `browser` mode gọi Camoufox first; test tái dùng hàm parse số liệu/category chung với Apify source (không trùng logic).

*(Thời gian tăng so với bản gốc do selector SPA thực tế thường cần vài vòng tinh chỉnh trước khi ổn định.)*

## PR 3 — `feat/agents-threads-camoufox-source` (~1.5–2 ngày)

1. `sources/threads_camoufox_source.py` + wire vào `_scrape_threads_smart` (giữa Jina → Apify).
2. Xử lý case redirect-login theo §3.4 (rớt tầng ngay, không cố vượt).
3. Test tương tự PR 2 + verify `_detect_category`/lifecycle tái dùng, không copy code.

## PR 4 — `feat/web-trends-browser-mode` (~nửa buổi)

1. UI mode selector thêm nút `browser`, sửa type, status text, phân biệt "rỗng vì chưa cài" vs "rỗng vì không có kết quả".
2. Chạy `apps/web` e2e hiện có (`playwright.config.ts`) không vỡ.

## PR 5 — Docs & runbook (~nửa buổi đến 1 ngày)

1. `docs/runbooks/camoufox-scraping.md`: setup local/Docker (opt-in volume mount binary hoặc build stage riêng, **kèm danh sách system packages cần cài trên Debian/Ubuntu base image**), log events, metric `trends_source_total{source="camoufox"}` + `trends_source_latency_seconds{source="camoufox"}` (histogram) + `trends_source_error_total{source="camoufox",reason=}` (phân loại timeout/selector_empty/blocked/unavailable), troubleshooting (chưa fetch binary, thiếu system deps, timeout, bị checkpoint).
2. Cập nhật `docs/runbooks/tiktok-scraping.md` sơ đồ chuỗi mới.
3. Ghi rõ ranh giới phạm vi cào (§2.3) vào runbook để người vận hành sau này không mở rộng phạm vi mà không cân nhắc.

**Thứ tự phụ thuộc:** PR 1 → (PR 2, PR 3 song song) → PR 4, PR 5.

---

# PHẦN V — RÀNG BUỘC PHẢI TUÂN THỦ

| Ràng buộc | Cách đáp ứng |
|-----------|--------------|
| ADR-003 contracts-first | Không thêm DTO — `TrendItem` có sẵn, serialize `trends.py` không đổi |
| ADR-008 người quyết | Bật mode `browser` ở production là quyết định vận hành, không mặc định; ranh giới phạm vi cào ở §2.3 |
| `docs/THIRD_PARTY.md` khi thêm lib | PR 1 ghi dòng Camoufox + ngày kiểm |
| Test không gọi browser thật | Mock lifecycle; extractor test bằng fixture HTML tĩnh (tách bạch — §3.3); `test_trends_api.py` hiện có phải xanh không sửa |
| CI không tải binary 300MB | Camoufox là optional dep — CI không cài, test mock; import lỗi → skip tier |
| Không launch browser vô hạn song song | Semaphore `CA_CAMOUFOX_MAX_CONCURRENT` bắt buộc, có test |
| Code style | ruff (line 100), mypy strict, không `Any` mới trong domain |
| Conventional Commits, squash merge, max 3 ngày/tuổi nhánh | Theo operating model |
| Docker demo toàn tuyến | Không đổi image mặc định; runbook ghi opt-in + system deps cần thiết |

---

# PHẦN VI — RỦI RO & GIẢI PHÁP

| Rủi ro | Khả năng | Giải pháp |
|--------|-----------|-----------|
| Threads hiện login-wall với search mới | Trung bình | Camoufox là công cụ tốt nhất hiện có để vượt; nếu vẫn chặn → tier tự rơi về Apify/RSS như cũ (§3.4), không cố đăng nhập |
| TikTok chặn cả browser thật | Thấp | Chuỗi vẫn có TikWM + Apify sau lưng; Camoufox chỉ là tier thêm vào |
| Chậm (launch browser 3-10s/lần quét) | Cao | Chấp nhận v1; cache TTL 10 phút riêng (§3.3-bis) giảm số lần launch thực tế; timeout tổng chuỗi có trần (§3.5) |
| **Nhiều browser launch song song gây OOM worker** *(bổ sung v2)* | Trung bình–Cao | Semaphore `CA_CAMOUFOX_MAX_CONCURRENT` bắt buộc từ PR 1, có test riêng |
| **Event loop bị block nếu gọi sync launch từ route async** *(bổ sung v2)* | Trung bình | Chốt threadpool executor riêng ở PR 1 (§3.2), không dùng threadpool mặc định của framework |
| **Rủi ro pháp lý/ToS khi né bot-detection của TikTok/Meta** *(bổ sung v2)* | Trung bình | Chỉ cào public search, không login, nhịp độ hợp lý (§2.3); người duyệt PR cần xác nhận đã cân nhắc rủi ro này trước khi merge, không phải quyết định kỹ thuật thuần túy |
| Binary 300MB không có trên máy deploy | Chắc chắn xảy ra ở đâu đó | `is_available()` + log hướng dẫn phân loại rõ (chưa cài/chưa fetch/thiếu system deps) + UI hiện "Camoufox chưa cài" khi chọn mode browser mà server trả rỗng |
| **Thiếu system deps Linux cho headless Firefox trong container** *(bổ sung v2)* | Cao (điểm chặn thực tế phổ biến) | Runbook liệt kê rõ package cần cài (libgtk, libasound2, libdbus, fonts); `is_available()` phân biệt lỗi này với "chưa tải binary" |
| Selector DOM vỡ khi TikTok/Threads đổi giao diện | Cao theo thời gian | Tách extractor thuần khỏi browser lifecycle (§3.3) để cập nhật nhanh; metric `error_total{reason="selector_empty"}` cảnh báo sớm khi extract ra 0 item liên tục |
| Memory browser trong worker API | Trung bình | Launch per-call + close trong `finally` + timeout 45s + semaphore concurrency |

---

# PHẦN VII — ĐỊNH NGHĨA HOÀN THÀNH (Definition of Done)

- [ ] PR 1-5 merge, CI xanh, không test cũ nào đỏ.
- [ ] Máy dev có cài Camoufox (đủ cả binary + system deps): chọn mode `browser` → cào thật TikTok + Threads ra `TrendItem` có `is_live_scraped=True`.
- [ ] Máy không cài: mọi mode chạy y như cũ (auto/direct_only/apify_force), log có `camoufox_unavailable_skipping` kèm lý do phân loại.
- [ ] Test concurrency: xác nhận semaphore chặn đúng số browser launch song song, không launch vô hạn.
- [ ] Test extractor chạy độc lập bằng fixture HTML, không cần Playwright thật.
- [ ] `docs/THIRD_PARTY.md` + runbook mới cập nhật, bao gồm system deps container và ranh giới phạm vi cào (§2.3).
- [ ] Người duyệt PR xác nhận đã cân nhắc rủi ro ToS/pháp lý trước khi merge PR 2/3.
- [ ] Demo 10 phút
