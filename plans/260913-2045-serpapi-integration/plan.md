# Kế hoạch Tích hợp SerpApi Toàn diện — Hệ điều hành F&B NHỊP QUÁN

> **Mã kế hoạch:** `260913-2045-serpapi-integration`
> **Phiên bản:** **v2.0** — Kiến trúc mở rộng, chuẩn SOTA (Production-Grade Architecture)
> **Kế thừa từ:** v1.0 (Architecture & Implementation Plan)
> **Tuân thủ chuẩn Nhịp Quán:**
> - **ADR-002 (Deterministic Core):** Dữ liệu thu thập từ SerpApi được chuẩn hóa thành Pydantic model tất định; mọi phép tính định giá ($P_{50}$, AMBI, Bayesian rating) là hàm thuần túy, không side-effect.
> - **ADR-003 (Contracts-First):** Dùng schema chia sẻ trong `ca_contracts` (`StoreCandidate`, `TrendItem`, `MenuSnapshot`); mọi thay đổi schema phải qua PR review + bump `schema_version`.
> - **ADR-008 (Agent trích xuất, Người phê duyệt):** Agent chỉ trích xuất dữ liệu khách quan; **fail-closed** tuyệt đối khi hết quota, lỗi API, hoặc dữ liệu không qua được validation.

---

## 0. Tóm tắt điều hành (Executive Summary)

Bản v1.0 đã xác định đúng vấn đề cốt lõi (nợ kỹ thuật hardcode rating/review, thiếu nguồn Trends chính thức) và chọn đúng 4 API SerpApi cần dùng. Bản **v2.0** này nâng cấp kế hoạch lên chuẩn triển khai production bằng cách bổ sung:

| Hạng mục còn thiếu ở v1.0 | Bổ sung ở v2.0 |
|---|---|
| Chưa có resilience pattern rõ ràng (retry, circuit breaker) | Mục 6 — Resilience Engineering đầy đủ với code mẫu |
| Chưa định nghĩa NFR (latency, availability) | Mục 2 — Yêu cầu phi chức năng có số đo cụ thể |
| Chưa có observability/alerting | Mục 8 — Observability & Alerting (metrics, log schema) |
| Chưa xét bảo mật dữ liệu cá nhân trong review | Mục 7 — Bảo mật & Tuân thủ (Nghị định 13/2023/NĐ-CP) |
| Roadmap thiếu effort estimate & exit criteria | Mục 10 — Roadmap có story-point, DoD từng giai đoạn |
| Risk matrix thiếu owner/probability/impact | Mục 11 — Risk matrix mở rộng dạng RAID |
| Chưa có kế hoạch rollout/rollback | Mục 9 — Chiến lược Rollout & Rollback |
| Chưa có KPI đo thành công sau go-live | Mục 12 — Success Metrics |

**Nguyên tắc bất biến giữ nguyên từ v1.0:** SerpApi **không bao giờ** chạy trong cronjob tần suất cao; mọi lệnh gọi phải qua Cache → Quota Guard → Circuit Breaker trước khi chạm mạng.

---

## 1. Bối cảnh & Phân tích Hiện trạng

### 1.1. Vấn đề của từng nguồn dữ liệu hiện tại

| Phân hệ | Nguồn hiện tại | Vấn đề cốt tử |
|---|---|---|
| `ag_pricing` (Catchment Radar) | `gmaps_menu_source.py` qua Camoufox | Bị chặn Captcha/bot thường xuyên, ngốn RAM/CPU, **hardcode tạm** `rating=4.5, review_count=100` (nợ kỹ thuật đã ghi trong `IMPLEMENTATION_STATUS.md`) |
| `ag_trend` (Trend Radar) | `threads_google_bridge_source.py` (RSS XML / Apify TikTok) | Không có nguồn Google Trends chính thức cho thị trường VN; dữ liệu nhiễu, không có time-series chuẩn |
| `ag_voc` (Customer Voice) | Chưa có nguồn tự động | Không phát hiện được lỗi vận hành lặp lại ≥3 lần để nạp vào Playbook 8 bước |

### 1.2. Đặc thù hạn ngạch SerpApi Free Tier

- **250 lượt tìm kiếm/tháng** (~8 lượt/ngày) — đây là **ràng buộc thiết kế cứng (hard constraint)**, không phải gợi ý.
- Nguyên tắc bắt buộc (giữ nguyên từ v1.0, không đổi):
  - ❌ Tuyệt đối không cronjob/worker chạy tự động theo phút hoặc crawl hàng loạt.
  - ✅ Chỉ dùng cho: (1) yêu cầu chủ động on-demand từ Chủ quán/Quản lý; (2) batch định kỳ tần suất thấp (1 lần/tuần).
  - 🛡️ Bắt buộc có: Local TTL Cache (24h Maps / 7 ngày Menu Photos / 12h Trends), Quota Guard, Fallback tự động.

---

## 2. Mục tiêu, Phạm vi & Yêu cầu Phi chức năng (NFR)

### 2.1. Mục tiêu đo được (Objectives)

1. Loại bỏ 100% giá trị hardcode `rating=4.5 / review_count=100` trong `ag_pricing` trước ngày kết thúc Giai đoạn 3.
2. Cung cấp time-series Google Trends thực cho ≥10 từ khóa F&B trọng điểm theo tuần.
3. Không vượt quá **77/250** request/tháng ở kịch bản vận hành bình thường (xem Mục 4), giữ ≥65% quota dự trữ.
4. Không có sự cố "hết quota giữa tháng gây gián đoạn UI" trong 3 tháng đầu vận hành (đo bằng số lần `SerpApiQuotaExceededError` lọt ra ngoài fallback).

### 2.2. Ngoài phạm vi (Out of scope)

- Các engine SerpApi khác (Flights, Hotels, Patents, Zillow, Shopping...).
- Nâng cấp lên gói SerpApi trả phí (sẽ đánh giá lại sau khi có dữ liệu sử dụng thực tế 2 tháng, xem Mục 12).
- Thay thế hoàn toàn Camoufox — Camoufox vẫn giữ vai trò **fallback bắt buộc**, không bị xoá khỏi hệ thống.

### 2.3. Yêu cầu phi chức năng (NFR)

| NFR | Mục tiêu | Cách đo |
|---|---|---|
| **Latency (on-demand)** | p95 < 3.5s cho request "Khảo sát đối thủ quanh quán" (bao gồm cả Haversine + Pydantic validate) | Metric `serpapi_request_duration_seconds` |
| **Availability tính năng** | ≥99.5% (fallback tính là "còn hoạt động", chỉ tính downtime khi cả SerpApi lẫn Camoufox đều fail) | Uptime theo endpoint `/api/system/integrations/serpapi` |
| **Cache hit rate** | ≥60% sau tuần đầu vận hành ổn định | `serpapi_cache_hit_total / serpapi_request_total` |
| **Quota an toàn** | Không bao giờ vượt `MONTHLY_LIMIT - SAFETY_MARGIN` | Đếm `serpapi_quota_used_total` |
| **Toàn vẹn dữ liệu** | 100% response phải qua Pydantic validation trước khi lưu DB | Test coverage + runtime `ValidationError` = 0 lọt xuống tầng dưới |
| **Bảo mật khóa API** | API key không bao giờ xuất hiện trong log/response client | Kiểm tra bằng log-scan CI (regex mask) |

---

## 3. Lựa chọn API & Bản đồ Ánh xạ Nghiệp vụ

Giữ nguyên 4 API cốt lõi đã chọn ở v1.0, bổ sung cột "Giá trị/Quota" để định lượng ROI của từng lệnh gọi:

| SerpApi Engine | Phân hệ | Mục đích | Request tiết kiệm | Giá trị / Quota (điểm 1–5) |
|---|---|---|---|---|
| `engine=google_maps` | `ag_pricing` | Đối thủ F&B theo GPS: tên, rating thật, review thật, toạ độ | 1 search → 20 quán | ⭐⭐⭐⭐⭐ (xoá nợ kỹ thuật) |
| `engine=google_maps_photos` | `ag_pricing` (Dine-in Vision) | Ảnh menu để Vision AI OCR đọc giá | Chỉ Top 3–5 đối thủ | ⭐⭐⭐⭐ |
| `engine=google_trends` | `ag_trend` | Interest-over-time + breakout keyword tại VN | 1–2 lần/tuần | ⭐⭐⭐⭐ |
| `engine=google_maps_reviews` | `ag_voc` | Phát hiện phàn nàn lặp lại để nạp Playbook | 1–2 lần/tháng | ⭐⭐⭐ |

*(70+ API còn lại của SerpApi bị loại — không có nghiệp vụ tương ứng trong NHỊP QUÁN, tránh phân tán quota.)*

---

## 4. Kiến trúc Giải pháp Kỹ thuật

### 4.1. Sơ đồ thành phần (Component Diagram)

```
                       [NGƯỜI DÙNG: CHỦ QUÁN / QUẢN LÝ]
                                       │
                      (Web UI: Bấm khảo sát / Xem Trend)
                                       │
                                       ▼
                             [FastAPI / ca_api]  ── rate-limit theo user_id
                                       │
                                       ▼
                       [Agents: ag_pricing / ag_trend / ag_voc]
                                       │
           ┌───────────────────────────┴───────────────────────────┐
           ▼                                                       ▼
 [gmaps_serpapi_source]                                  [gtrends_serpapi_source]
           │                                                       │
           └───────────────────────────┬───────────────────────────┘
                                       ▼
                     ┌─────────────────────────────────────┐
                     │         SERPAPI CLIENT ENGINE        │
                     │                                       │
                     │ 1. Idempotency key (sha256 params)   │
                     │ 2. L1 Cache (in-memory, 5 phút)       │──(HIT)──▶ trả ngay
                     │ 3. L2 Cache (TTL file/sqlite)         │──(HIT)──▶ trả ngay
                     │ 4. Circuit Breaker state check         │──(OPEN)─▶ Fallback
                     │ 5. Quota Guard (used ≥ limit-margin?) │──(VƯỢT)─▶ Fallback
                     │ 6. HTTP Exec + Retry (backoff+jitter) │
                     │ 7. Pydantic Validate response          │──(FAIL)─▶ log + Fallback
                     │ 8. Ghi Quota Counter + Cache + Metric │
                     └─────────────────┬─────────────────────┘
                                       │
                                       ▼
                            [SerpApi REST Service]

Fallback chain (khi bước 4/5/7 chặn):
   gmaps_serpapi_source  ──▶  gmaps_menu_source (Camoufox)  ──▶  Cache cũ (stale-if-error) ──▶  báo lỗi UI có nhãn cảnh báo
```

### 4.2. Sơ đồ trình tự (Sequence) — Yêu cầu "Khảo sát đối thủ quanh quán"

```
User → WebUI     : Bấm "Khảo sát đối thủ"
WebUI → ca_api    : POST /catchment/survey {lat,lng,radius}
ca_api → ag_pricing: run_survey(lat,lng,radius)
ag_pricing → SerpApiClient: fetch_gmaps_competitors(lat,lng)
SerpApiClient → L1/L2 Cache: get(key)
  alt cache HIT
    Cache -->> SerpApiClient: cached StoreCandidate[]
  else cache MISS
    SerpApiClient → CircuitBreaker: allow_request()?
    alt breaker OPEN
      CircuitBreaker -->> SerpApiClient: reject
      SerpApiClient → Fallback: scrape_gmaps_menu_images_camoufox()
    else breaker CLOSED/HALF_OPEN
      SerpApiClient → QuotaGuard: can_spend(1)?
      alt quota còn
        SerpApiClient → SerpApi REST: GET /search?engine=google_maps...
        SerpApi REST -->> SerpApiClient: JSON local_results
        SerpApiClient → Pydantic: validate → StoreCandidate[]
        SerpApiClient → Cache: set(key, ttl=24h)
        SerpApiClient → QuotaGuard: commit(1)
      else quota hết
        SerpApiClient → Fallback: scrape_gmaps_menu_images_camoufox()
      end
    end
  end
SerpApiClient -->> ag_pricing: StoreCandidate[]
ag_pricing -->> ca_api: kết quả + nguồn dữ liệu (serpapi|camoufox|cache)
ca_api -->> WebUI: 200 OK + danh sách đối thủ
```

### 4.3. Data Contracts (Pydantic — `ca_contracts`)

```python
# packages/contracts/src/ca_contracts/catchment_survey.py
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class StoreCandidate(BaseModel):
    place_id: str
    name: str
    rating: float = Field(ge=0, le=5)
    review_count: int = Field(ge=0)
    address: str
    lat: float
    lng: float
    distance_km: float = Field(ge=0)
    data_source: Literal["serpapi", "camoufox", "cache"]
    fetched_at: datetime

# packages/contracts/src/ca_contracts/trend_item.py
class TrendItem(BaseModel):
    keyword: str
    interest_score: int = Field(ge=0, le=100)
    nguon_goc: Literal["google_vn"] = "google_vn"
    danh_muc: Literal["am_thuc_fnb"] = "am_thuc_fnb"
    vong_doi: Literal["moi_nhu", "dang_dinh", "thoai_trao"]
    is_breakout: bool
    window: Literal["now 7-d", "today 1-m"]
    fetched_at: datetime
```

Mọi thay đổi trường bắt buộc phải bump `schema_version` trong docstring module và cập nhật golden fixture tương ứng ở Mục 5.1.

---

## 5. Quản trị Quota & Cache đa tầng

### 5.1. Bảng phân bổ 250 request/tháng (giữ triết lý v1.0, làm rõ ngưỡng cảnh báo)

| Nghiệp vụ | Tần suất | Request/lần | Tổng/tháng |
|---|---|---|---|
| Quét đối thủ bán kính | 1 lần/tuần (hoặc khi đổi menu) | 2–3 queries | ~12 |
| Ảnh menu đối thủ top đầu | 1 lần/tháng (Top 5) | 5 queries | ~5 |
| Google Trends đồ uống VN | 2 lần/tuần, 5–10 keyword | 2 queries | ~16 |
| VOC — phản hồi khách hàng | 1 lần/2 tuần | 2 queries | ~4 |
| On-demand từ Copilot chat | Theo lệnh Quản lý | 1 query | ~20 |
| Dự phòng kiểm thử/staging | — | — | ~20 |
| **Tổng sử dụng dự kiến** | | | **~77** |
| **Dự trữ an toàn (>65%)** | | | **~173** |

### 5.2. Ngưỡng cảnh báo Quota (3 mức, mới ở v2.0)

| Mức | Ngưỡng đã dùng | Hành động tự động |
|---|---|---|
| **INFO** | 150/250 (60%) | Ghi log INFO, không thông báo |
| **WARN** | 200/250 (80%) | Gửi cảnh báo nội bộ (Slack/Telegram webhook nội bộ), giảm tần suất batch Trends xuống 1 lần/tuần |
| **CRITICAL** | 240/250 (96%, = `MONTHLY_LIMIT - SAFETY_MARGIN`) | **Fail-closed**: chặn mọi request mới, toàn bộ chuyển Fallback, banner cảnh báo trên UI Admin |

### 5.3. Cache đa tầng

- **L1 — In-memory (process-local):** TTL 5 phút, chống double-click trong cùng phiên, không tốn I/O.
- **L2 — Persistent TTL cache** (file JSON hoặc SQLite `ca_api.persist`):
  - Google Maps địa điểm: TTL 24h.
  - Google Maps Photos: TTL 7 ngày.
  - Google Trends: TTL 12h.
  - Google Maps Reviews: TTL 24h.
- **Key cache:** `sha256(engine + sorted(params))` — đảm bảo idempotency, tránh lệch cache do thứ tự tham số.
- **Stale-if-error:** Khi cả SerpApi lẫn Camoufox đều fail, trả cache cũ nhất còn có kèm nhãn `"data_source": "cache", "stale": true` thay vì lỗi trắng UI.

---

## 6. Resilience Engineering (mới ở v2.0)

### 6.1. Retry với Exponential Backoff + Jitter

```python
# packages/agents/src/ca_agents/clients/serpapi_client.py
import random, time

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
BASE_DELAY_SEC = 0.5

def call_with_retry(fn, *args, **kwargs):
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = fn(*args, **kwargs)
            if response.status not in RETRYABLE_STATUS:
                return response
        except (TimeoutError, ConnectionError):
            pass
        if attempt == MAX_RETRIES:
            raise SerpApiError("Đã hết số lần thử lại")
        delay = BASE_DELAY_SEC * (2 ** attempt) + random.uniform(0, 0.3)
        time.sleep(delay)
```

### 6.2. Circuit Breaker (3 trạng thái)

- **CLOSED** (bình thường): cho phép gọi, đếm số lỗi liên tiếp.
- **OPEN**: sau ≥3 lỗi liên tiếp (network/5xx) trong 60 giây → khoá 5 phút, mọi request chuyển thẳng Fallback không tốn quota.
- **HALF_OPEN**: sau thời gian khoá, cho 1 request thử nghiệm; thành công → CLOSED, thất bại → OPEN lại.

> Circuit Breaker bảo vệ quota khỏi bị "đốt" bởi retry storm khi SerpApi đang gặp sự cố diện rộng.

### 6.3. Timeout Budget

| Bước | Timeout |
|---|---|
| HTTP call tới SerpApi | 8s (connect 2s + read 6s) |
| Toàn bộ chuỗi (bao gồm 3 lần retry) | ≤ 20s trước khi tự động chuyển Fallback |
| Fallback Camoufox | 15s, nếu quá hạn → trả cache stale hoặc lỗi có kiểm soát |

### 6.4. Idempotency & Chống spam click

- Idempotency key = `sha256(engine + params)`, TTL trùng với cache TTL tương ứng → click lặp trong 24h không tốn quota (đã nêu ở Mục 5.3).
- Rate-limit tầng `ca_api`: tối đa **3 request on-demand/phút/user**, chặn bằng HTTP 429 kèm thông báo "Vui lòng đợi kết quả trước đó".

---

## 7. Bảo mật & Tuân thủ (mới ở v2.0)

| Hạng mục | Biện pháp |
|---|---|
| **Lưu trữ API Key** | Chỉ trong `.env` / secret manager; không commit, không log; CI có bước scan secret (gitleaks hoặc tương đương) |
| **Mask trong log** | Logger tự động thay `SERPAPI_API_KEY` bằng `ak_***masked***` trước khi ghi; kiểm tra bằng unit test log-format |
| **Không lộ key ra client** | Toàn bộ gọi SerpApi diễn ra ở backend (`ca_agents`), không bao giờ expose key qua response API hay bundle frontend |
| **Dữ liệu cá nhân trong Reviews** | Tên người review, ảnh đại diện là dữ liệu cá nhân theo Nghị định 13/2023/NĐ-CP (Bảo vệ dữ liệu cá nhân VN) — chỉ lưu nội dung review + rating phục vụ phân tích VOC, **ẩn danh hoá** (loại bỏ tên/avatar) trước khi lưu DB dài hạn |
| **Rate-limit chống lạm dụng** | Giới hạn theo user (Mục 6.4) ngăn 1 tài khoản đốt hết quota chung của hệ thống |
| **Kiểm soát truy cập tính năng** | Nút "Khảo sát đối thủ" chỉ hiển thị cho role Chủ quán/Quản lý, không cho role Nhân viên |

---

## 8. Observability & Alerting (mới ở v2.0)

### 8.1. Metrics (dạng Prometheus)

| Metric | Loại | Ý nghĩa |
|---|---|---|
| `serpapi_request_total{engine,result}` | Counter | Tổng số lệnh gọi, `result` ∈ {success, fallback, error} |
| `serpapi_request_duration_seconds{engine}` | Histogram | Latency để tính p95/p99 |
| `serpapi_quota_used_total` / `serpapi_quota_remaining` | Gauge | Theo dõi tiêu thụ quota realtime |
| `serpapi_cache_hit_total` / `serpapi_cache_miss_total` | Counter | Tính cache hit rate |
| `serpapi_circuit_breaker_state` | Gauge (0/1/2) | 0=CLOSED, 1=HALF_OPEN, 2=OPEN |
| `serpapi_fallback_triggered_total{reason}` | Counter | `reason` ∈ {quota_exceeded, circuit_open, validation_error, timeout} |

### 8.2. Cấu trúc log (structured JSON)

```json
{
  "ts": "2026-09-13T20:45:00Z",
  "level": "WARN",
  "component": "serpapi_client",
  "engine": "google_maps",
  "event": "quota_threshold_warn",
  "quota_used": 201,
  "quota_limit": 250,
  "request_id": "req_8f2a...",
  "api_key_masked": "ak_***masked***"
}
```

### 8.3. Quy tắc cảnh báo (Alert Rules)

| Điều kiện | Kênh | Mức độ |
|---|---|---|
| `serpapi_quota_remaining <= 50` | Slack/Telegram nội bộ | WARN |
| `serpapi_quota_remaining <= 10` | Slack/Telegram + banner Admin UI | CRITICAL |
| `serpapi_circuit_breaker_state == 2` kéo dài >10 phút | Slack nội bộ | WARN |
| Tỉ lệ `fallback_triggered / request_total` > 30% trong 1 giờ | Slack nội bộ | WARN — nghi ngờ SerpApi outage |

---

## 9. Chiến lược Rollout & Rollback (mới ở v2.0)

1. **Feature flag kép:** `SERPAPI_ENABLED` (toàn cục) + cờ theo tenant `tenant.serpapi_opt_in` — cho phép bật thử nghiệm cho 1–2 quán pilot trước khi bật toàn hệ thống.
2. **Canary tuần 1:** Chỉ bật cho môi trường staging + 1 quán pilot nội bộ, theo dõi metrics Mục 8 trong 7 ngày.
3. **Tiêu chí mở rộng (Go/No-Go):** Cache hit rate ≥50%, 0 lỗi `ValidationError` lọt xuống DB, quota tuần pilot < 30 request.
4. **Rollback tức thời:** Chỉ cần set `SERPAPI_ENABLED=false` → toàn hệ thống quay về Camoufox ngay lập tức, không cần deploy lại.
5. **Rollback dữ liệu:** Vì `StoreCandidate` có trường `data_source`, có thể lọc/loại bỏ dữ liệu từ nguồn lỗi mà không ảnh hưởng dữ liệu Camoufox cũ.

---

## 10. Roadmap Triển khai theo Giai đoạn (có effort estimate & Definition of Done)

| Giai đoạn | Nội dung | Effort ước tính | Definition of Done (DoD) |
|---|---|---|---|
| **G1 — Chuẩn bị** | `.env.example`, golden fixtures (`google_maps_coffee_hcm.json`, `google_trends_fnb_vn.json`), schema contracts | 1.5 ngày công | Fixtures được review; contracts pass `mypy`/`pydantic` strict mode |
| **G2 — SerpApi Client Core** | `serpapi_client.py`: cache L1/L2, Quota Guard, Circuit Breaker, Retry, mask log | 3 ngày công | Unit test coverage ≥95% với mock network; không có network call thật trong CI |
| **G3 — `ag_pricing` Integration** | `gmaps_serpapi_source.py` + Haversine + fallback Camoufox, nối `catchment_survey_service.py` | 2.5 ngày công | UI hiển thị rating/review thật; nợ kỹ thuật hardcode bị xoá hoàn toàn khỏi `IMPLEMENTATION_STATUS.md` |
| **G4 — `ag_trend` Integration** | `gtrends_serpapi_source.py`, gán `vong_doi` theo breakout logic | 2 ngày công | ≥10 keyword F&B có time-series thật trong Trend Radar |
| **G5 — Quota Dashboard & Observability** | Endpoint `GET /api/system/integrations/serpapi`, metrics + alert rules Mục 8 | 2 ngày công | Dashboard hiển thị đúng `used/limit/remaining`; alert WARN/CRITICAL bắn thử thành công |
| **G6 — Canary Rollout** | Bật cho staging + 1 pilot theo Mục 9 | 1 tuần theo dõi | Đạt tiêu chí Go/No-Go Mục 9.3 |
| **G7 — Full Rollout & Runbook** | Bật toàn hệ thống, hoàn thiện `docs/runbooks/serpapi-integration.md` | 1 ngày công | Runbook được vận hành viên không-phải-dev đọc và làm theo thành công (dry-run) |

**Tổng effort dự kiến:** ~12 ngày công kỹ thuật + 1 tuần canary theo dõi song song.

---

## 11. Ma trận Rủi ro (RAID — mở rộng từ v1.0)

| Rủi ro | Xác suất | Tác động | Owner | Biện pháp kiểm soát | Rủi ro tồn dư |
|---|---|---|---|---|---|
| Hết 250 request giữa tháng | Trung bình | Cao (mất tính năng khảo sát) | Backend lead | Quota Guard 3 mức (Mục 5.2) + Fallback Camoufox tự động | Thấp |
| Gọi trùng lặp do spam click | Cao | Thấp (lãng phí quota) | Backend lead | Cache TTL + Idempotency key (Mục 5.3, 6.4) | Rất thấp |
| Lộ API Key | Thấp | Rất cao (khoá tài khoản/lạm dụng) | DevOps | `.env` only + gitleaks CI + log mask (Mục 7) | Rất thấp |
| SerpApi đổi cấu trúc JSON | Trung bình | Trung bình | Backend lead | Pydantic strict validate + contract test + fallback khi parse lỗi | Thấp |
| SerpApi outage diện rộng | Thấp | Trung bình | Backend lead | Circuit Breaker (Mục 6.2) chặn retry storm, chuyển Fallback | Thấp |
| Dữ liệu cá nhân trong Reviews vi phạm luật | Thấp | Cao (pháp lý) | Compliance/PM | Ẩn danh hoá trước khi lưu (Mục 7) | Thấp |
| 1 user đốt hết quota chung | Trung bình | Trung bình | Backend lead | Rate-limit 3 req/phút/user (Mục 6.4) | Thấp |

---

## 12. Success Metrics — Đo lường sau Go-live

| KPI | Baseline (trước tích hợp) | Mục tiêu 30 ngày sau go-live |
|---|---|---|
| % dữ liệu rating/review là hardcode | 100% | 0% |
| Cache hit rate | — | ≥60% |
| Quota trung bình sử dụng/tháng | — | 60–90/250 (trong ngân sách G5.1) |
| Số sự cố gián đoạn UI do hết quota | — | 0 |
| Tỉ lệ fallback về Camoufox | — | <15% tổng request |
| Số keyword F&B có Trend time-series thật | 0 | ≥10 |
| Thời gian phản hồi p95 (on-demand survey) | — | <3.5s |

> Nếu sau 60 ngày quota trung bình vượt 200/250 đều đặn, đây là tín hiệu đánh giá nâng cấp gói SerpApi trả phí (quyết định thuộc PM, ngoài phạm vi kế hoạch kỹ thuật này).

---

## 13. Kế hoạch Xác minh & Kiểm thử

### 13.1. Kim tự tháp kiểm thử

| Tầng | Tỉ trọng | Nội dung |
|---|---|---|
| **Unit test** (không mạng, không tốn quota) | ~70% | Mock response Google Maps → đúng `StoreCandidate`; mock hết quota → `SerpApiQuotaExceededError` + Fallback; mock Circuit Breaker OPEN → không gọi HTTP |
| **Contract/Schema test** | ~15% | Golden fixture khớp 100% với Pydantic model; test khi SerpApi đổi field (thêm/xoá) không làm crash |
| **Integration test** (cờ `--live-serpapi`, chạy giới hạn) | ~10% | 1 query thật tại Quận 1, TP.HCM để xác thực key + schema thật |
| **E2E/Manual verification** | ~5% | Theo checklist Mục 13.2 |

### 13.2. Xác minh nghiệp vụ (Manual)

1. Vào **Market Radar** trên Web UI → bấm "Khảo sát đối thủ quanh quán".
2. Xác nhận danh sách hiển thị số sao/review **thật** (VD: `4.6 ⭐ (1.250 đánh giá)`) thay vì hardcode `4.5 ⭐ (100)`.
3. Kiểm tra `serpapi_quota.json` (hoặc bảng persist) tăng đúng `+1`.
4. Bấm lại nút khảo sát ngay lập tức lần 2 trong vòng 24h → xác nhận quota **không** tăng thêm (cache HIT).
5. Tắt tạm `SERPAPI_ENABLED=false` → xác nhận hệ thống chuyển Camoufox mượt, không lỗi UI.
6. Kiểm tra Quota Dashboard hiển thị đúng `{enabled, used_this_month, limit, remaining}`.

---

## 14. Phụ lục

### 14.1. Cấu hình môi trường đầy đủ (`.env.example`)

```bash
SERPAPI_API_KEY=
SERPAPI_ENABLED=true
SERPAPI_MONTHLY_LIMIT=250
SERPAPI_SAFETY_MARGIN=10
SERPAPI_WARN_THRESHOLD=200
SERPAPI_INFO_THRESHOLD=150
SERPAPI_CACHE_TTL_MAPS_HOURS=24
SERPAPI_CACHE_TTL_PHOTOS_DAYS=7
SERPAPI_CACHE_TTL_TRENDS_HOURS=12
SERPAPI_CIRCUIT_BREAKER_FAILURE_THRESHOLD=3
SERPAPI_CIRCUIT_BREAKER_OPEN_SECONDS=300
SERPAPI_ONDEMAND_RATE_LIMIT_PER_MIN=3
```

### 14.2. Checklist Runbook vận hành (rút gọn)

- [ ] Kiểm tra `GET /api/system/integrations/serpapi` mỗi sáng đầu tuần.
- [ ] Nếu `remaining < 50`: xem lại tần suất batch Trends, cân nhắc giảm xuống 1 lần/tuần.
- [ ] Nếu `remaining < 10`: xác nhận hệ thống đã tự chuyển Fallback, thông báo team.
- [ ] Đầu mỗi tháng: xác nhận bộ đếm quota tự reset đúng ngày chu kỳ billing SerpApi.
- [ ] Khi SerpApi đổi API/pricing: cập nhật golden fixture + chạy lại contract test trước khi merge.

### 14.3. Thuật ngữ (Glossary)

| Thuật ngữ | Giải thích |
|---|---|
| Fail-closed | Khi có lỗi/hết hạn ngạch, hệ thống mặc định từ chối/chuyển fallback thay vì cho qua không kiểm soát |
| Stale-if-error | Trả dữ liệu cache cũ (có gắn nhãn) khi nguồn thật và fallback đều lỗi, tốt hơn lỗi trắng |
| Circuit Breaker | Cơ chế ngắt mạch tạm thời khi hệ thống đích liên tục lỗi, tránh gọi lặp vô ích |
| Idempotency key | Khoá định danh duy nhất cho 1 tổ hợp tham số request, dùng để khử trùng lặp |
