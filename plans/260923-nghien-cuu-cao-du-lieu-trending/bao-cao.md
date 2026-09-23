# Nghiên Cứu & Kiểm Chứng: Cào Dữ Liệu Trending (AG-TREND)

> **Ngày:** 2026-09-23 · **Phạm vi:** `packages/agents` (AG-TREND), `apps/api/trends.py`, `apps/web/page-quan`
> **Phương pháp:** chạy thật từng nguồn (probe live, read-only) — không chấp nhận "code complete"
> **Nguyên tắc áp dụng:** ADR-008 (chống tín hiệu giả), fail-closed

---

## 1. Tóm tắt điều hành

Hệ thống AG-TREND có **6 nguồn cào trending** với kiến trúc tier-fallback khá tốt, nhưng kiểm chứng bằng chạy thật cho thấy **3 bug sản xuất nghiêm trọng** khiến 4/6 nguồn không trả được dữ liệu thật:

| # | Bug | Mức độ | Hệ quả thật |
|---|---|---|---|
| **B1** | Đọc sai shape response TikWM (`data` là **list phẳng**, code đọc `data["videos"]` luôn `[]`) | 🔴 Chặn | TikWM **luôn trả [] dù nguồn sống** → mọi request TikTok rớt xuống Apify (tốn quota) |
| **B2** | SerpApi Google Trends thiếu `data_type=RELATED_QUERIES` | 🔴 Chặn | `fetch_fnb_trends_serpapi()` **luôn trả []** → tầng SerpApi vô dụng, tốn quota vô ích |
| **B3** | Apify actor TikTok **FAILED 7/8 run gần nhất** | 🔴 Chặn | Không có tầng thật nào cho TikTok → UI hiển thị **6 chủ đề tĩnh giả** |
| **B4** | `APIFY_THREADS_ACTOR_ID=apify/threads-scraper` **không tồn tại** (HTTP 404) | 🟡 Nên sửa | Tầng Apify cho Threads là dead code |

**Hệ quả tổng hợp:** dữ liệu TikTok trên UI hiện tại là **100% tĩnh (hard-code)** — 6/84 item của radar có `is_live_scraped=False`. Vi phạm tinh thần ADR-008 dù đã có cờ đánh dấu.

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

### 3.2. Bug B1 — TikWM đọc sai shape (bằng chứng)

Response thật của TikWM:
```json
{"code":0, "msg":"success", "data": [ {"video_id":"...","region":"VN","title":"...","play_count":666097,"digg_count":27277,"author":{"unique_id":"thuybunfood"}}, ... ]}
```

Code hiện tại (`ag_trend.py`, `_scrape_tiktokwm_fallback`):
```python
raw_data = data.get("data", [])
vids = raw_data.get("videos", []) if isinstance(raw_data, dict) else raw_data
#            ^^^^^^^^^^^^^^^^^^^^^^^ chỉ chạy khi data là DICT, nhưng thực tế là LIST
```

⇒ Nhánh đọc `["videos"]` **không bao giờ chạy** → `videos = []` → hàm trả `[]`.

**Xác minh chéo:** `_scrape_tiktokwm_fallback()` chạy trực tiếp = **0 items**, nhưng gọi HTTP thủ công cùng endpoint = **5–10 video thật** (region=VN, play_count hàng trăm nghìn). Nguồn sống, code đọc sai.

**Test hiện có không bắt được** vì `test_tiktok_smart_fallback.py` mock toàn bộ `_scrape_tiktokwm_fallback` → không bao giờ chạm shape thật. Đây là lỗ hổng kiểm thử: **thiếu test parse shape thật của response bên thứ ba**.

### 3.3. Bug B2 — SerpApi thiếu `data_type` (bằng chứng)

| `data_type` | Trả về | rising | top |
|---|---|---|---|
| *(mặc định / TIMESERIES)* | `interest_over_time` | **0** | **0** |
| `RELATED_QUERIES` | `related_queries` | **20** | **25** |

Code gọi `search_serpapi("google_trends", {"q":…, "geo":…, "date":…})` — không truyền `data_type` ⇒ SerpApi mặc định TIMESERIES ⇒ payload **không có `related_queries`** ⇒ `parse_gtrends_to_trend_items()` trả [] ⇒ `fetch_fnb_trends_serpapi()` trả [].

**Xác minh:** gọi thẳng SerpApi với `data_type=RELATED_QUERIES` + parse bằng chính hàm của hệ thống → **8 TrendItem thật** ("trà sữa viên viên hà nội" +600%, "trà sữa tam hảo" +300%…).

**Tác động kép:** (1) tầng SerpApi vô dụng cho keyword cụ thể; (2) vẫn **tốn 1 request quota** cho mỗi lần gọi thất bại (quota hiện 13/250). Cache L2 đang giữ payload TIMESERIES đã hỏng nên lỗi "dính" thêm 12h.

### 3.4. Bug B3 — Apify actor TikTok FAILED liên tục

Run history `clockworks/tiktok-scraper`:

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

= **7/8 run gần nhất FAILED** (từ 2026-09-19). Mỗi run vẫn tiêu ~$0.0037. Run #8 SUCCEEDED trùng thời điểm fix trước → actor bị TikTok chặn proxy sau đó.

### 3.5. Bug B4 — Actor Threads không tồn tại

`GET https://api.apify.com/v2/acts/apify~threads-scraper` → **HTTP 404 "Actor with this name was not found"**.
Trong khi `AGENT_NAMES`/docstring lại ghi `curious_coder/threads-scraper`. `.env` đang trỏ vào actor không tồn tại ⇒ tầng Apify Threads là dead code.

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
