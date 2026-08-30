# Runbook: TikTok scraping (Apify + TikWM fallback)

## Tổng quan

Hệ thống cào TikTok có **2 nguồn**, hoạt động theo thứ tự ưu tiên:

```
┌─────────────────┐
│  User request   │
│  /trends?p=tiktok│
└────────┬────────┘
         ▼
┌─────────────────────────────┐
│  PRIMARY: Apify actor       │
│  clockworks/tiktok-scraper  │ ─── fail / quota / rỗng ───┐
│  (~$X/tháng, free $5)       │                              │
└────────┬────────────────────┘                              │
         │ OK                                                │
         ▼                                                   ▼
   ┌──────────┐                                  ┌──────────────────────┐
   │  Return  │                                  │  FALLBACK: TikWM     │
   │  items   │                                  │  (proxy miễn phí,    │
   └──────────┘                                  │   không có SLA)      │
                                                 └──────────┬───────────┘
                                                            │ OK / fail
                                                            ▼
                                                   ┌─────────────┐
                                                   │  Return []  │
                                                   └─────────────┘
```

**Nguyên tắc:**
- Apify = primary, chạy cho **mọi** request TikTok
- TikWM = fallback **duy nhất**, chỉ chạy khi Apify lỗi
- Không có chain dài nhiều tầng

## Setup ban đầu

### 1. Đăng ký Apify

1. Vào https://console.apify.com/sign-up
2. Đăng ký bằng email (free tier $5/tháng)
3. Vào **Settings → Integrations → Token** → copy token

### 2. Cấu hình `.env`

Thêm 3 dòng vào `apps/api/.env` (không commit file này):

```bash
APIFY_TOKEN=apify_api_xxxxxxxxxxxxxxxx
APIFY_TIKTOK_ACTOR_ID=clockworks/tiktok-scraper
TIKTOK_APIFY_TIMEOUT_S=90
```

### 3. Verify

```bash
python scripts/smoke_tiktok_apify.py
```

Kết quả mong đợi:
- `✅ Apify returned N items in Xms`
- In 3 tiêu đề + URL đầu tiên

## Theo dõi hàng ngày

### Log cần quan sát

| Log event | Ý nghĩa |
|---|---|
| `tiktok_source_apify` | Apify OK, đếm `items_count` |
| `tiktok_source_fallback` | **Apify fail**, đang rơi vào TikWM |
| `apify_tiktok_source` | Detail từ `tiktok_apify_source.py` |

### Metric (nếu có Prometheus)

| Metric | Ý nghĩa | Alert khi |
|---|---|---|
| `tiktok_source_total{source="apify"}` | Số lần Apify OK | < 80% tổng / 1h |
| `tiktok_source_total{source="tiktokwm"}` | Số lần rơi vào fallback | > 5 / 1h |
| `tiktok_fallback_total{reason="apify_error:ApifyError"}` | Lý do rơi fallback | > 5 / 1h |
| `tiktok_fallback_total{reason="apify_error:quota"}` | Hết quota | ≥ 1 / 24h |

### Apify Console

- Quota: https://console.apify.com/billing
- Usage log: https://console.apify.com/actors/runs

## Sự cố thường gặp

### 🔴 Log: `ApifyError: APIFY_TOKEN chưa cấu hình`

**Nguyên nhân:** Token rỗng / chưa set trong `.env`

**Cách xử lý:**
1. Mở `apps/api/.env`
2. Kiểm tra `APIFY_TOKEN=apify_api_...` không rỗng
3. Restart API: `systemctl restart ca-api`
4. Chạy lại `scripts/smoke_tiktok_apify.py`

### 🔴 Log: `ApifyError: status=FAILED` liên tục

**Nguyên nhân:** Actor bị lỗi hoặc TikTok chặn proxy Apify

**Cách xử lý:**
1. Vào https://console.apify.com/actors/runs xem chi tiết run fail
2. Nếu là do TikTok chặn → chờ 1-2h rồi retry
3. Nếu là bug actor → check actor repo: https://github.com/clockworks/tiktok-scraper
4. Fallback TikWM đang chạy tạm → user vẫn có data (dù chất lượng thấp hơn)

### 🟡 Log: `ApifyError: timeout sau 90s`

**Nguyên nhân:** Apify chậm (bình thường 10-30s, có khi tới 90s)

**Cách xử lý:**
1. Tăng `TIKTOK_APIFY_TIMEOUT_S=180` trong `.env`
2. Restart API
3. Nếu vẫn timeout → check Apify status: https://status.apify.com/

### 🔴 Metric `tiktok_fallback_total` > 5 lần / phút

**Nguyên nhân:** Hết quota $5/tháng hoặc token bị revoke

**Cách xử lý:**
1. Check quota: https://console.apify.com/billing
2. Nếu hết quota → đợi reset tháng sau hoặc nạp thêm
3. Nếu token bị revoke → tạo token mới, update `.env`

### 🟡 Log: `unexpected:KeyError`

**Nguyên nhân:** Apify actor đổi schema output

**Cách xử lý:**
1. Vào Apify Console → xem JSON mẫu mới nhất
2. Báo dev update `packages/agents/src/ca_agents/sources/tiktok_apify_source.py`
3. Pin version actor trong `.env` nếu cần (vd `clockworks/tiktok-scraper~1.2.0`)

### 🔴 Cả Apify lẫn TikWM đều fail → UI mất data

**Nguyên nhân:** Cả 2 nguồn đều chết

**Cách xử lý:**
1. Verify Apify: `python scripts/smoke_tiktok_apify.py`
2. Check internet connection từ server
3. Nếu cần kíp: bật mock data dự phòng (giữ behavior cũ)
4. Liên hệ dev để tìm nguồn thay thế

## Khi nào cần dev can thiệt

| Tình huống | Action của dev |
|---|---|
| Schema break (KeyError, missing field) | Update mapping trong `tiktok_apify_source.py` |
| Actor deprecated | Đổi `APIFY_TIKTOK_ACTOR_ID`, có thể viết adapter mới |
| TikWM chết hẳn | Tìm fallback mới (RapidAPI TikTok scraper, scraperapi.com,...) |
| Cần thêm use case (hashtag, profile, music) | Extend `scrape_tiktok_apify()` với `mode` param mới |

## Cost reference

| Hoạt động | Compute Units (CU) ước tính |
|---|---|
| Search 12 videos | ~0.5 CU |
| Search 50 videos | ~2 CU |
| Lấy full comment 1 video | ~0.3 CU |
| Quét 1 profile (50 video) | ~3 CU |

**Free tier:** $5 = ~1000 CU / tháng (tùy actor pricing).

**Estimate với traffic hiện tại:**
- ~200 requests/ngày × 0.5 CU = 100 CU/ngày
- ~3000 CU/tháng → vượt free tier → cần plan $29 hoặc giảm traffic

Nếu vượt → check log `tiktok_source_apify` để tối ưu (cache, batch).

## Reference

- Plan: `plans/260830-0930-tiktok-apify-primary-tiktokwm-fallback/plan.md`
- Code: `packages/agents/src/ca_agents/clients/apify_client.py`
- Code: `packages/agents/src/ca_agents/sources/tiktok_apify_source.py`
- Code: `packages/agents/src/ca_agents/ag_trend.py::_scrape_tiktok_smart`
- Smoke test: `scripts/smoke_tiktok_apify.py`
- Apify Console: https://console.apify.com/
- Apify docs: https://docs.apify.com/

## Lịch sử thay đổi

| Ngày | Tác giả | Thay đổi |
|---|---|---|
| 2026-08-30 | AI assistant | Tạo runbook ban đầu (kèm plan refactor Apify primary) |