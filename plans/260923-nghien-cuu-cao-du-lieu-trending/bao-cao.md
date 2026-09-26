# Nghiên Cứu & Kiểm Chứng: Cào Dữ Liệu Trending (AG-TREND)

> **Ngày:** 2026-09-23 (cập nhật 2026-09-24) · **Phạm vi:** `packages/agents` (AG-TREND), `apps/api/trends.py`, `apps/web/page-quan`
> **Phương pháp:** chạy thật từng nguồn (probe live, read-only) — không chấp nhận "code complete"
> **Nguyên tắc áp dụng:** ADR-008 (chống tín hiệu giả), fail-closed
> **Trạng thái:** ✅ ĐÃ SỬA — xem §9 để biết các thay đổi đã triển khai

---

## 1. Tóm tắt điều hành

Hệ thống AG-TREND có **6 nguồn cào trending** với kiến trúc tier-fallback khá tốt, nhưng kiểm chứng bằng chạy thật cho thấy **nhiều lỗi sản xuất nghiêm trọng** khiến phần lớn nguồn không trả được dữ liệu thật:

| # | Bug | Mức độ | Hệ quả thật | Trạng thái |
|---|---|---|---|---|
| **B1** | TikWM: `timeout=6s` quá ngắn (thực tế 0.4–9.3s) + không thử host dự phòng + không kiểm tra `code` | 🔴 Chặn | TikWM **luôn trả []** dù nguồn sống → mọi request TikTok rớt xuống Apify (tốn quota) | ✅ Đã sửa |
| **B2** | SerpApi Google Trends thiếu `data_type=RELATED_QUERIES` | 🔴 Chặn | `fetch_fnb_trends_serpapi()` **luôn trả []** → tầng SerpApi vô dụng, tốn quota vô ích | ✅ Đã sửa |
| **B3** | Apify actor TikTok FAILED 7/8 run + payload rỗng + poll timeout 5s bỏ luôn run | 🔴 Chặn | Không có tầng thật nào cho TikTok → UI hiển thị **6 chủ đề tĩnh giả** | ✅ Đã sửa |
| **B4** | `.env` trỏ `APIFY_THREADS_ACTOR_ID=apify/threads-scraper` **không tồn tại** (HTTP 404) | 🟡 Nên sửa | Tầng Apify cho Threads là dead code | ✅ Đã sửa |
| **B5** | Threads Bridge **bịa link** `@threads_creator` + gán nhãn "Meta Threads" cho tin báo chí | 🟡 Nên sửa | UI trỏ tới hồ sơ không tồn tại; nguồn bị gán nhãn sai | ✅ Đã sửa |

**Hệ quả tổng hợp:** dữ liệu TikTok trên UI là **100% tĩnh (hard-code)** — 6/84 item của radar có `is_live_scraped=False`.

### 1.1. Đính chính chẩn đoán B1 (quan trọng)

Bản báo cáo đầu tiên kết luận B1 là *"code đọc sai shape `data`"*. **Sau khi đo kỹ lại (3–4 lần lặp/host), chẩn đoán đúng là:**

| Quan sát | Kết luận |
|---|---|
| `data` **luôn là list phẳng** | Code cũ **xử lý ĐÚNG** shape (`isinstance(raw_data, dict)` → else dùng list) |
| Thời gian phản hồi **0.4s – 9.3s**, hay vượt 6s | `timeout=6` cắt ngang phần lớn request → `TimeoutError: read operation timed out` |
| Có lúc trả **HTTP 531** | Lỗi tạm thời của hạ tầng TikWM |
| Cả `tikwm.com` và `www.tikwm.com` đều sống, lỗi khác nhau theo thời điểm | Cần thử **cả hai** host |
| Request thứ 2 liên tiếp → `code=-1 "Free Api Limit: 1 request/second."` | Rate limit 1 req/s; code cũ **không kiểm tra `code`** và dùng timeout comment 2s |

**Bài học:** chẩn đoán dựa trên 1 lần probe có thể sai. Phải lặp nhiều lần để tách *lỗi tạm thời* khỏi *lỗi logic*.

---

## 2. Kiến trúc thực tế (đã xác minh)

### 2.1. Luồng end-to-end

```
UI: apps/web/src/app/page-quan/page.tsx
  → GET /api/v1/trends/radar?region=&category=&keyword=&mode=
  → fetch_trend_radar()            [ag_trend.py]
  → chuỗi source theo platform → list[TrendItem] → JSON
```

### 2.2. Chuỗi tier theo platform

| Platform | Chuỗi (mode `auto`) | Trạng thái chạy thật |
|---|---|---|
| `tiktok_vn` | TikWM → Camoufox → Apify → **static tĩnh** | 🔴 rớt hết → static |
| `threads_vn` | Official API → Google Bridge → Jina Direct → Camoufox(Trending) → Apify → RSS GenZ | 🟡 Bridge chạy, nhưng link bị bịa |
| `google_vn` | SerpApi Trends → **RSS trực tiếp** | 🟡 RSS OK, SerpApi chết |
| `star_vn` | RSS Kenh14 scrape trực tiếp | 🟢 OK (50 item thật) |
| `tiktok_global` | RSS Google Trends US | 🟢 OK (10 item thật) |

### 2.3. 4 mode cào

`auto` (mặc định) · `direct_only` (khóa Apify+Camoufox) · `apify_force` · `browser` (Camoufox first).

---

## 3. Bằng chứng chạy thật (2026-09-23)

### 3.1. Bảng kết quả probe live

| Nguồn | Thời gian | Kết quả | Có thật? |
|---|---|---|---|
| Google Trends VN (RSS) | 3.01s | 10 items | ✅ thật |
| Google Trends Global (RSS) | 0.59s | 10 items | ✅ thật |
| Showbiz & KOLs (Kenh14) | 0.36s | 50 items | ✅ thật |
| **TikTok (auto)** | 13.95s | 6 items | ❌ **tĩnh, is_live_scraped=False** |
| **TikWM trực tiếp** | 6.12s | **0 items** | ❌ bug B1 |
| **Threads (auto)** | 1.33s | 8 items | ⚠️ link bịa |
| Threads Google Bridge | 0.48s | 6 items | ⚠️ link bịa |
| Threads Official API | — | `is_configured()=False` | ⚪ chưa có token |
| Threads Direct (Jina) | 0.94s | 0 items | ❌ HTTP 403 |
| **SerpApi Trends F&B** | 2.88s | **0 items** | ❌ bug B2 |
| Camoufox | — | `is_available()=False` | ⚪ chưa cài |
| **Radar tổng hợp (all)** | 16.34s | **84 items**, 14 item tĩnh | — |

### 3.2. Bug B1 — TikWM timeout quá ngắn + không thử host dự phòng (bằng chứng)

**Đo thời gian thật (4 lần lặp/host, timeout=6s như code cũ):**

| Host | Kết quả |
|---|---|
| `www.tikwm.com` | 6.12s TIMEOUT · 6.09s TIMEOUT · 0.42s `code=-1` · 0.45s `code=-1` |
| `tikwm.com` | 6.34s OK (21 video) · 6.12s TIMEOUT · 6.09s TIMEOUT · 5.30s OK (16 video) |

**Cùng 2 host đó với timeout=20s:**

| Host | Kết quả |
|---|---|
| `www.tikwm.com` | 7.52s OK (20 video, region VN) · 6.14s **HTTP 531** · 6.06s OK (21 video) |
| `tikwm.com` | 6.31s **HTTP 531** · 5.75s OK (20 video) · 9.30s OK (21 video) |

**⇒ Kết luận:** nguồn **hoàn toàn sống**, nhưng:
1. Thời gian phản hồi thật (0.4–9.3s) **thường xuyên vượt `timeout=6`** → request bị cắt ngang.
2. Cả hai host đều hay lỗi tạm (timeout/HTTP 531) → cần **thử lần lượt cả hai**.
3. Code cũ **không kiểm tra `code`** — payload `{"code": -1, "msg": "Free Api Limit: 1 request/second."}` vẫn đi tiếp vào vòng lặp.
4. Comment dùng `timeout=2` (quá ngắn) và **gọi liên tiếp** → chạm rate limit 1 req/s → luôn rỗng.

**Bằng chứng rate limit:** request comment thứ nhất OK (`code=0`, 3 comment), request thứ hai liên tiếp ngay sau → `code=-1 "Free Api Limit: 1 request/second."`

**Test hiện có không bắt được** vì `test_tiktok_smart_fallback.py` mock toàn bộ `_scrape_tiktokwm_fallback` → không bao giờ chạm HTTP thật. Đây là lỗ hổng kiểm thử: **thiếu test cho tầng HTTP/parse của nguồn bên thứ ba**.

### 3.3. Bug B2 — SerpApi thiếu `data_type` (bằng chứng)

| `data_type` | Trả về | rising | top |
|---|---|---|---|
| *(mặc định / TIMESERIES)* | `interest_over_time` | **0** | **0** |
| `RELATED_QUERIES` | `related_queries` | **20** | **25** |

Code gọi `search_serpapi("google_trends", {"q":…, "geo":…, "date":…})` — không truyền `data_type` ⇒ SerpApi mặc định TIMESERIES ⇒ payload **không có `related_queries`** ⇒ `parse_gtrends_to_trend_items()` trả [] ⇒ `fetch_fnb_trends_serpapi()` trả [].

**Xác minh:** gọi thẳng SerpApi với `data_type=RELATED_QUERIES` + parse bằng chính hàm của hệ thống → **8 TrendItem thật** ("trà sữa viên viên hà nội" +600%, "trà sữa tam hảo" +300%…).

**Tác động kép:** (1) tầng SerpApi vô dụng cho keyword cụ thể; (2) vẫn **tốn 1 request quota** cho mỗi lần gọi thất bại (quota hiện 13/250). Cache L2 đang giữ payload TIMESERIES đã hỏng nên lỗi "dính" thêm 12h.

### 3.4. Bug B3 — Apify TikTok FAILED + payload rỗng + poll timeout (bằng chứng)

**Run history `clockworks/tiktok-scraper`:**

| Thời điểm | Status |
|---|---|
| 2026-09-23 11:05 | FAILED |
| 2026-09-23 11:05 | FAILED |
| 2026-09-22 09:52 | FAILED |
| 2026-09-22 09:27 | FAILED |
| 2026-09-21 07:29 | FAILED |
| 2026-09-21 04:18 | FAILED |
| 2026-09-19 04:54 | FAILED |
| 2026-09-17 14:55 | SUCCEEDED |

= **7/8 run gần nhất FAILED** (từ 2026-09-19). Mỗi run vẫn tiêu ~$0.0037.

**Ba nguyên nhân độc lập được xác định:**

1. **Payload rỗng khi keyword rỗng.** `_build_input("", 10, "search")` cũ trả `{"maxItems":10, "downloadVideo":False, "proxyCountryCode":"VN"}` — **không có `searchQueries`**. Actor fail ngay mà vẫn tốn CU.
2. **Poll timeout 5s bỏ luôn cả run.** `_HTTP_TIMEOUT_POLL_S=5`; khi poll gặp `TimeoutError: read operation timed out` thì code cũ `raise ApifyError` **ngay lập tức** — dù actor vẫn đang chạy phía Apify. Đo thật: 1 run `SUCCEEDED` sau **3 phút** (`11:15:32 → 11:18:42`) nhưng lần poll đầu đã timeout.
3. **Run thật đã SUCCEEDED gần đây** (`WIgFmc3opsAXHbXQ0` 11:16, `n7RZz6eq03idx8sGu` 11:15) → actor **không chết**, đường ống mới là vấn đề.

### 3.5. Bug B4 — Actor Threads không tồn tại

Đo live `GET /v2/acts/<actor>`:

| Actor | Kết quả |
|---|---|
| `apify/threads-scraper` | ❌ **HTTP 404** "Actor with this name was not found" |
| `curious_coder/threads-scraper` | ✅ OK — title `'Meta threads scraper'`, id `LnCvmgElmmlHN1gvZ` |
| `louisdeconinck/threads-scraper` | ❌ 404 |
| `automation-lab/threads-scraper` | ✅ OK — title `'Threads Scraper'` |

`.env` đang trỏ `apify/threads-scraper` (không tồn tại) **ghi đè** default đúng trong code (`curious_coder/threads-scraper`) ⇒ tầng Apify Threads là dead code.

### 3.6. Vấn đề B5 — Link Threads Bridge bị bịa

`parse_google_rss_xml()` nhánh `if "threads.net" not in final_url` dựng link giả:
```python
author = author_m.group(1) if author_m else "threads_creator"
final_url = f"https://www.threads.net/@{clean_kw}"
```
→ 8 item Threads đều có `link = https://www.threads.net/@threads_creator` (không trỏ tới bài thật).

Kiểm chứng: Google News RSS `site:threads.net …` trả **0 item** (`RSS len=1216, items=0`) — nên dữ liệu Threads của radar thực tế đến từ **query fallback không `site:`** (kết quả báo chí, không phải bài Threads).

### 3.7. Vấn đề B6 — Không có trần tương tác, ảo giác ưu tiên

- 50/84 item là `star_vn` (báo giải trí) → **lấn át** tín hiệu F&B.
- `_scrape_google_trends_global` trả tin Mỹ (thời tiết, "Daylight Savings") gắn `nguon_goc="tiktok_global"` — **gán nhãn sai nền tảng**, không liên quan F&B VN.

---

## 4. Nguồn trending bổ sung (đã probe)

| Nguồn | Kết quả probe | Đánh giá |
|---|---|---|
| **SerpApi `google_trends_trending_now`** | HTTP 200, **25 trending thật** VN (xổ số miền trung 500K, u-23 VN-TL +1000%, himass…) kèm `search_volume`, `increase_percentage`, `categories`, `trend_breakdown` | ⭐ **Nên thêm** — nguồn trending VN chất lượng cao, đúng "bảng xu hướng" |
| TikTok `challenge/detail` (công khai) | HTTP 200: `#xuhuong` 6.15K tỷ views, `#cafe` 108 tỷ, `#matcha` 64 tỷ, `#cafemuoi` 298M | ⭐ **Nên thêm** — đo "sức nóng tuyệt đối" hashtag F&B, không cần key |
| TikWM `feed/list` (đã có) | HTTP 200, 5–10 video/region thật (play/digg thật) | ⚠️ Đang có bug B1 |
| TikTok Creative Center API | **401 "no permission"** | ❌ Cần đăng nhập/cookie, không dùng được |
| TikTok `challenge/item_list` | HTTP 200 nhưng **len=0** | ❌ Đã bị đóng |
| Jina Reader (`r.jina.ai`) | **HTTP 403** | ❌ Đã chết cho Threads |

---

## 5. Đối chiếu plan ↔ code ↔ thực tế

| Nguồn lệch | Chi tiết |
|---|---|
| **Runbook tiktok-scraping.md** | Sơ đồ ghi chuỗi `TikWM → Camoufox → Apify` nhưng **thiếu nhánh static last-resort** trong hình (đã có ở mục "Nguyên tắc") |
| **Runbook camoufox-scraping.md** | Ghi `Threads: Official API → Google RSS → Jina → Camoufox → Apify → RSS` — Jina (403) và Apify (404) đều chết, sơ đồ mô tả năng lực không tồn tại |
| **`AGENT_NAMES` vs `.env`** | Docstring `threads_apify_source.py` ghi `curious_coder/threads-scraper`, `.env` ghi `apify/threads-scraper` (không tồn tại) |
| **Plan 260914 §4.2 (lifecycle)** | Đã code đầy đủ (`threads_trending_lifecycle.py`) nhưng **không có consumer** vì Camoufox chưa cài |
| **Plan 260910 §3.5** | Mode `browser` phụ thuộc Camoufox — chưa cài trên máy này |

---

## 6. Khuyến nghị (ưu tiên)

### P0 — Sửa ngay (chặn merge)

1. **B1 TikWM**: sửa đọc `data` dạng list phẳng:
   ```python
   raw_data = data.get("data") or []
   vids = raw_data.get("videos", []) if isinstance(raw_data, dict) else raw_data
   ```
   Thêm **test parse shape thật** (fixture JSON copy từ response thật) — không mock cả hàm.
2. **B2 SerpApi**: thêm `"data_type": "RELATED_QUERIES"` vào params `fetch_fnb_trends_serpapi`; **xóa cache L2** payload TIMESERIES đã hỏng (`data/cache/serpapi/*.json`).
3. **B3/B4**: xác định lại actor Apify (kiểm tra run log FAILED, thử actor khác hoặc `APIFY_TIKTOK_ACTOR_ID` hợp lệ); sửa `APIFY_THREADS_ACTOR_ID` hoặc bỏ tầng Threads Apify.

### P1 — Nên làm

4. **B5**: bỏ nhánh dựng link giả `@threads_creator`; nếu RSS không trả link `threads.net` thì `link_goc` để rỗng + `is_live_scraped=False`.
5. **Thêm SerpApi `google_trends_trending_now`** làm nguồn `google_vn` chính (25 trending VN thật).
6. **Thêm TikTok `challenge/detail`** để đo "sức nóng" hashtag F&B (viewCount thật).
7. **B6**: thêm trần số item/nguồn (ví dụ 10–12) và **ưu tiên F&B** khi gộp radar.

### P2 — Cải thiện cấu trúc

8. Cài Camoufox (`pip install camoufox[geoip]` + `camoufox fetch` + `scripts/threads_setup_login.py`) để kích hoạt tier Trending Now đã code xong.
9. Thêm `.env` keys `THREADS_ACCESS_TOKEN` (Official API tier 0) — đường đáng tin nhất cho Threads.
10. Test mới: **fixture-based parse test** cho mọi nguồn bên thứ ba (dùng `data/mock_external/` theo `docs/mock-external-data-test.md`).

---

## 7. Cách tái lập bằng chứng

```bash
# Probe live tất cả nguồn (read-only)
.venv312\Scripts\python.exe _tmp_probe_trending.py
.venv312\Scripts\python.exe _tmp_probe_trending2.py   # Apify run history + SerpApi payload
.venv312\Scripts\python.exe _tmp_probe_trending4.py   # data_type A/B test
.venv312\Scripts\python.exe _tmp_probe_trending5.py   # TikWM domain + nguồn thay thế
```

**Lưu ý:** các script trên là file TẠM, đã xóa sau khi hoàn tất nghiên cứu.

---

## 8. Ghi chú môi trường

- `.env` gốc **đã được khôi phục** (trước đây memory ghi bị mất): có `APIFY_TOKEN`, `SERPAPI_API_KEY`, `OPENROUTER_API_KEY`, FB tokens, SMTP, JEV.
- `THREADS_ACCESS_TOKEN`, `CA_CAMOUFOX_*`, `CA_THREADS_USER_DATA_DIR` **chưa set**.
- Apify quota: `Sin21` · Free ($10/tháng) · đã dùng **$0.4131 / $10** (4.1%), hết hạn chu kỳ 2026-09-29.
- SerpApi quota: **13/250** request tháng 2026-09.
- Camoufox: **chưa cài** trong `.venv312` lẫn `.venv`.
- Interpreter chính: `.venv312` (Python 3.12.10) — `.venv` thiếu `httpx`.

---

## 9. Thay đổi đã triển khai (2026-09-24)

### 9.1. Bảng file thay đổi

| File | Thay đổi |
|---|---|
| `packages/agents/src/ca_agents/ag_trend.py` | Thêm `parse_tikwm_feed()` (hàm thuần), `_fetch_tikwm_feed()` (thử 2 host), `_fetch_tikwm_comments()` (chờ nhịp 1 req/s), `_prioritize_vn_videos()`, `_is_fnb_title()`; timeout 6s→20s; tách `_scrape_google_trends_vn_rss()`; thêm tầng Trending Now vào đầu chuỗi `_scrape_google_trends_vn()` |
| `packages/agents/src/ca_agents/text_util.py` | **MỚI** — `match_any_keyword()`: so khớp từ khoá theo **ranh giới từ** (sửa bug `"ăn"` khớp trong `"xăng"`) |
| `packages/agents/src/ca_agents/sources/gtrends_trending_now_source.py` | **MỚI** — nguồn `google_trends_trending_now` (bảng xếp hạng cấp quốc gia), TTL riêng 1h; phân loại theo TÊN category |
| `packages/agents/src/ca_agents/sources/gtrends_serpapi_source.py` | Thêm `data_type=RELATED_QUERIES` (bắt buộc); `include_timeline=True` gọi thêm request TIMESERIES riêng |
| `packages/agents/src/ca_agents/sources/threads_google_bridge_source.py` | Bỏ link bịa `@threads_creator`; `author=""` khi RSS không có; nhãn nguồn đúng (`Báo chí (Google News)` vs `Meta Threads`) |
| `packages/agents/src/ca_agents/sources/tiktok_apify_source.py` | `_build_input()` luôn điền truy vấn mặc định cho cả 3 mode |
| `packages/agents/src/ca_agents/clients/apify_client.py` | Poll chịu lỗi mạng tạm thời (`_MAX_POLL_ERRORS=3`); log `statusMessage` khi run FAILED |
| `packages/agents/src/ca_agents/clients/serpapi_client.py` | `SERPAPI_CACHE_TTL_TRENDING_NOW_HOURS` (mặc định 1h) cho engine mới |
| `packages/agents/tests/test_trending_scraping_regressions.py` | **MỚI** — 19 test hồi quy, fixture copy từ **payload THẬT** |
| `apps/api/tests/unit/test_tiktok_apify_source.py` | Cập nhật test "keyword rỗng" theo hành vi ĐÚNG (trước đó đóng băng hành vi sai) |
| `apps/api/tests/unit/test_threads_apify_source.py` | **Sửa test pollution**: reset circuit breaker `_CB_JINA` (state module-level) — test PASS khi chạy riêng nhưng FAIL trong full suite |
| `apps/api/.env.example` | Tài liệu hoá `APIFY_THREADS_ACTOR_ID` + cảnh báo payload rỗng tốn CU |
| `.env.example` | Thêm `SERPAPI_CACHE_TTL_TRENDING_NOW_HOURS` |
| `.env` | `APIFY_THREADS_ACTOR_ID`: `apify/threads-scraper` → `curious_coder/threads-scraper` |
| `data/cache/serpapi/*.json` | Xoá 4 cache chứa payload TIMESERIES hỏng (thiếu `related_queries`) |
| `docs/runbooks/tiktok-scraping.md` | Sơ đồ đủ 4 tầng; bảng đặc tính TikWM đo thật; cảnh báo payload rỗng |
| `docs/runbooks/camoufox-scraping.md` | Bảng trạng thái từng tầng (Jina 403, Bridge không phải bài Threads…) |

### 9.2. Nguyên tắc giữ nguyên (không phá vỡ)

- **ADR-008**: mọi hàm parse **từ chối dữ liệu không đáng tin** (`code != 0` → `[]`) thay vì bịa.
- **Fail-closed**: nguồn lỗi → trả `[]` để chuỗi rớt tầng, không ném exception ra ngoài.
- **Hàm parse tách khỏi I/O** để test được bằng fixture tĩnh (không cần mạng).
- **Không đổi schema** `TrendItem` (ADR-003) — chỉ dùng lại các trường sẵn có.

### 9.3. Kiểm thử

| Gate | Kết quả |
|---|---|
| `test_trending_scraping_regressions.py` (mới) | **19/19 pass** |
| Nhóm test agents + API trending | **1326 passed, 1 skipped, 0 failed** |
| Full suite (`pytest -q` từ ROOT) | **2328 passed, 1 skipped** (trước các fix bổ sung) |
| `ruff check packages/agents/src` + test đã sửa | **All checks passed** |
| `mypy --strict` các file đã sửa | **Success: no issues found in 8 source files** |
| `tsc --noEmit` (apps/web) | **sạch** |

### 9.3.1. Xác minh LIVE sau khi sửa (bằng chứng chạy thật)

| Nguồn | Trước | Sau |
|---|---|---|
| TikWM `_scrape_tiktokwm_fallback()` | **0 items** | **8 items thật** (`is_live_scraped=True` 8/8), có comment thật, 10s |
| SerpApi `fetch_fnb_trends_serpapi('trà sữa')` | **0 items** | **8 items** (`tiệm trà nhỏ game +5000%`, `trà sữa trường lạc +3900%`…) |
| Trending Now (nguồn mới) | *(chưa có)* | **12 items** (`xổ số miền bắc` 500.000 lượt, `giá xăng dầu hôm nay` 10.000…) |
| Threads Bridge link bịa | 8 items link `@threads_creator` | **0 link bịa**, `link_goc=""`, nhãn `Báo chí (Google News)` |
| `fetch_trend_radar()` | 84 items, **14 tĩnh**, 16.3s | 88 items, **8 tĩnh**, **1.8s** |
| Phân loại `giá xăng dầu hôm nay` | sai → `am_thuc_fnb` | đúng → `tam_ly_lifestyle` |

### 9.3.2. Bug phát sinh khi viết test (đã sửa)

1. **`"ăn"` khớp substring trong `"xăng"`** → `giá xăng dầu hôm nay` bị gán `am_thuc_fnb`.
   Sửa bằng `ca_agents/text_util.match_any_keyword()` (ranh giới từ), áp dụng cho cả
   `_FNB_TITLE_KEYWORDS` trong `ag_trend.py` (2 chỗ).
2. **Test pollution ở `test_threads_apify_source.py`**: `_CB_JINA` là circuit breaker
   **module-level process-wide**; chạy trong full suite thì các test khác đã gọi Jina
   thật (403) ≥3 lần → mạch OPEN 5 phút → test mock bị chặn. Đây đúng là pattern
   "test PASS khi chạy riêng nhưng FAIL trong full suite = test pollution" đã ghi
   trong hướng dẫn repo. Sửa: reset `_CB_JINA` trong test.

### 9.4. Còn lại (chưa làm — cần quyết định của người vận hành)

1. **Nguồn TikTok `challenge/detail`** — đã probe thành công (viewCount thật: `#xuhuong` 6.15K tỷ, `#cafe` 108 tỷ) nhưng **chưa nối vào chuỗi**. Đây là nguồn mới, nên tách PR riêng để review được thay đổi phạm vi nguồn.
2. **Cài Camoufox** (`pip install camoufox[geoip]` + `camoufox fetch` + `scripts/threads_setup_login.py`) → kích hoạt tier Trending Now đã code xong từ plan 260914.
3. **Set `THREADS_ACCESS_TOKEN`** → kích hoạt tier 0 (đường đáng tin nhất cho Threads).
4. **`_scrape_google_trends_global`** gắn `nguon_goc="tiktok_global"` cho dữ liệu Google Trends US — nhãn nền tảng gây hiểu nhầm, nên đổi riêng (thay đổi này ảnh hưởng filter UI nên cần chốt với người dùng trước).
5. **Trần số item/nguồn** khi gộp radar — hiện 50/88 item là `star_vn`, vẫn lấn át tín hiệu F&B.
6. **Feed TikWM trả lẫn region** (MM/US/PK/TH) dù yêu cầu `region=VN`. Đã **ưu tiên VN lên đầu** nhưng chưa lọc hẳn (lọc hẳn có nguy cơ rỗng khi feed toàn region khác).
7. **Hai bộ `_detect_category()` còn so khớp substring** (`threads_apify_source.py`, `threads_direct_source.py`, `threads_google_bridge_source.py`, `threads_official_api_source.py`). Cùng lớp bug với #9.3.2 mục 1 nhưng **chưa sửa** vì nằm ngoài phạm vi 5 bug của báo cáo — nên làm thành PR refactor riêng dùng `text_util.match_any_keyword`.
