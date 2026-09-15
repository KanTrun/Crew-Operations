# Runbook Vận hành: Tích hợp SerpApi Toàn diện v2.0 (F&B NHỊP QUÁN)

> **Mã kế hoạch:** `260913-2045-serpapi-integration`  
> **Phiên bản:** **v2.0** — Production-Grade Architecture  
> **Áp dụng cho:** Phân hệ `ag_pricing` (Catchment Radar), `ag_trend` (Trend Radar), `ag_voc` (Customer Voice).

---

## 1. Tổng quan & Kiến trúc Phòng thủ Hạn ngạch

Hệ thống sử dụng gói tài khoản **SerpApi Free Tier** với hạn mức cứng **250 lượt tìm kiếm/tháng** (~8 lượt/ngày). Để đảm bảo không bao giờ gián đoạn dịch vụ của Chủ quán/Quản lý và không phát sinh chi phí bất ngờ, mọi lệnh gọi mạng phải đi qua chuỗi phòng thủ 5 lớp:

```
[User on-demand / Weekly Batch]
               │
               ▼
   [1. Idempotency Key] ── (SHA256 engine + params)
               │
               ▼
   [2. L1 Cache (5 phút) & L2 Cache (File/TTL)] ──(HIT)──▶ Trả dữ liệu ngay (0 quota, 0 latency)
               │ (MISS)
               ▼
   [3. Circuit Breaker] ──(OPEN: >=3 lỗi liên tiếp)──▶ Chuyển Fallback ngay (Camoufox / Stale Cache)
               │ (CLOSED / HALF_OPEN)
               ▼
   [4. Quota Guard (3 mức)] ──(CRITICAL: đã dùng >=240)──▶ Fail-Closed, Chuyển Fallback ngay
               │ (Còn quota an toàn)
               ▼
   [5. HTTP Call + Retry Jitter] ──▶ SerpApi REST API
```

---

## 2. Các Mốc Cảnh báo & Hành động Tự động (Quota Thresholds)

| Mức độ | Số lượt đã dùng | Số lượt còn khả dụng | Trạng thái & Hành động tự động |
|---|---|---|---|
| **NORMAL** | 0 – 149 (< 60%) | > 90 | Hệ thống vận hành bình thường. |
| **INFO** | 150 – 199 (60% – 79%) | 41 – 90 | Ghi log INFO `quota_threshold_info`. |
| **WARN** | 200 – 239 (80% – 95%) | 1 – 40 | Ghi log WARN `quota_threshold_warn`. Tự động giảm tần suất batch Google Trends xuống 1 lần/tuần. |
| **CRITICAL** | 240 / 250 (>= 96%) | 0 | **Fail-Closed**: Khóa toàn bộ request gọi ra ngoài, 100% chuyển sang Fallback (Camoufox scraper hoặc Stale Cache). |

---

## 3. Quy trình Kiểm tra Định kỳ Hàng tuần

Vận hành viên (Ops) kiểm tra mỗi sáng thứ Hai:

1. **Gọi API kiểm tra sức khỏe tích hợp:**
   ```bash
   curl -s -H "Authorization: Bearer <TOKEN_QUAN_LY>" https://api.nhipquan.vn/api/system/integrations/serpapi | jq .
   ```
2. **Kiểm tra response mẫu:**
   ```json
   {
     "ok": true,
     "data": {
       "enabled": true,
       "status": "ok",
       "quota": {
         "year_month": "2026-09",
         "total_limit": 250,
         "safety_margin": 10,
         "usable_limit": 240,
         "used_requests": 68,
         "remaining_usable": 172,
         "warning_level": "NORMAL"
       },
       "circuit_breaker": {
         "state": "CLOSED",
         "consecutive_failures": 0
       },
       "cache_hit_rate_pct": 64.2
     }
   }
   ```
3. **Tiêu chí đánh giá nhanh:**
   - `status == "ok"`: Hoàn hảo.
   - `remaining_usable >= 50`: Hạn ngạch an toàn cho tuần tiếp theo.
   - `cache_hit_rate_pct >= 60%`: Bộ đệm hoạt động hiệu quả.

---

## 4. Xử lý Sự cố Thường gặp (Incident Response)

### Sự cố 1: Hạn ngạch chạm mức CẢNH BÁO (WARN: còn < 50 lượt)
- **Triệu chứng:** `warning_level == "WARN"`, log xuất hiện `quota_threshold_warn`.
- **Hành động khắc phục:**
  1. Kiểm tra xem có người dùng spam click khảo sát on-demand hay không.
  2. Tạm hoãn các tác vụ batch tìm kiếm Google Trends không thiết yếu cho đến đầu tháng sau.
  3. Nếu nhu cầu khảo sát thực tế cao liên tục trong 2 tháng, báo cáo PM để đánh giá nâng cấp gói trả phí.

### Sự cố 2: Hạn ngạch chạm mức NGUY CẤP (CRITICAL: còn <= 10 lượt)
- **Triệu chứng:** `warning_level == "CRITICAL"`, ngoại lệ `SerpApiQuotaExceededError`.
- **Hành động khắc phục:**
  1. Hệ thống đã **tự động Fail-Closed** và chuyển sang Camoufox / Cache cũ (không làm trắng UI).
  2. Bật cờ thông báo bảo trì tạm thời cho tính năng khảo sát trực tiếp nếu Camoufox cũng quá tải.
  3. Không cố gắng reset file quota thủ công khi tài khoản SerpApi upstream đã cạn lượt.

### Sự cố 3: Circuit Breaker ngắt mạch (`status == "circuit_open"`)
- **Triệu chứng:** `circuit_breaker.state == "OPEN"`, log xuất hiện `serpapi_circuit_breaker_tripped`.
- **Nguyên nhân:** Có >= 3 lỗi kết nối hoặc HTTP 5xx liên tiếp từ phía SerpApi upstream trong 60 giây.
- **Hành động khắc phục:**
  1. Kiểm tra trạng thái máy chủ SerpApi tại https://serpapi.com/status.
  2. Mạch sẽ tự động chuyển sang `HALF_OPEN` sau 300 giây (5 phút) để thử nghiệm 1 request thăm dò.
  3. Nếu cần reset mạch cưỡng bức khi máy chủ SerpApi đã phục hồi: restart worker backend `ca_api`.

### Sự cố 4: Lỗi xác thực API Key (`SerpApiAuthError`)
- **Triệu chứng:** HTTP 401 hoặc 403 từ SerpApi.
- **Hành động khắc phục:**
  1. Đăng nhập https://serpapi.com để xác nhận API Key còn hoạt động.
  2. Cập nhật biến `SERPAPI_API_KEY` trong file `.env` trên server production.
  3. Khởi động lại service `ca_api`: `docker compose restart api`.

---

## 5. Bảo mật & Tuân thủ Quyền Riêng tư (Nghị định 13/2023/NĐ-CP)

1. **Không bao giờ in raw API Key ra Log:** Mọi dòng log hệ thống đều được tự động che giấu dưới dạng `ak_***masked***`.
2. **Ẩn danh hóa dữ liệu đánh giá khách hàng (VOC / Reviews):**
   - Khi bóc tách đánh giá qua `google_maps_reviews`, toàn bộ thông tin định danh cá nhân (`user.name`, `user.thumbnail`, `user.link`) bị loại bỏ ngay tại tầng adapter `gmaps_serpapi_source.py`.
   - Cơ sở dữ liệu và cache chỉ lưu trữ: nội dung nhận xét (`snippet`), số sao (`rating`), và thời điểm tương đối (`date`) phục vụ cải tiến vận hành.

---

## 6. Kiểm tra & Chu kỳ Hàng tháng

- Bộ đếm quota `data/cache/serpapi_quota.json` tự động ghi nhận theo khóa `year_month` (ví dụ `2026-09`).
- Vào ngày đầu tiên của tháng mới (00:00 UTC), bộ đếm sẽ tự động chuyển sang chu kỳ mới và bắt đầu lại từ 0 lượt dùng, hoàn toàn không cần can thiệp thủ công bằng tay.
