---
title: "Phase 05 — Runbook + rollout"
description: "Viết runbook tiktok-scraping.md, cập nhật .env.example, thêm CI guard, rollout từng bước."
status: planned
priority: P2
effort: "20min"
tags: [runbook, rollout, ci, phase-05]
created: 2026-08-30
blockedBy: [phase-04]
blocks: []
---

# Phase 05 — Runbook + rollout

## Mục tiêu

Sau Phase 5, người vận hành có đủ:
- Tài liệu xử lý sự cố (runbook)
- Config mẫu để copy (`.env.example`)
- CI tự động verify
- Quy trình rollout từng bước

## Task 1: Runbook `docs/runbooks/tiktok-scraping.md`

### Sections yêu cầu

1. **Tổng quan**
   - Apify là primary (~$X/tháng, X tính từ Phase 1)
   - TikWM là fallback duy nhất
   - Sơ đồ flow Apify → TikWM

2. **Setup ban đầu**
   - Đăng ký Apify: link trực tiếp
   - Lấy token từ Settings → Integrations
   - Thêm vào `.env`: 3 dòng

3. **Theo dõi hàng ngày**
   - Log cần quan sát: `tiktok_source_apify`, `tiktok_source_fallback`
   - Metric: `tiktok_fallback_total{reason}` tăng = dấu hiệu Apify có vấn đề
   - Apify Console: https://console.apify.com/billing để check quota

4. **Sự cố thường gặp & cách xử lý**

   | Triệu chứng | Nguyên nhân có thể | Cách xử lý |
   |---|---|---|
   | Log: `ApifyError: APIFY_TOKEN chưa cấu hình` | Token rỗng trong env | Set lại token trong `.env` |
   | Log: `ApifyError: status=FAILED` liên tục | Actor bị lỗi / TikTok chặn | Check Apify status page; đổi actor nếu cần |
   | Log: `ApifyError: timeout sau 90s` | Apify chậm | Tăng `TIKTOK_APIFY_TIMEOUT_S` lên 180 |
   | Metric `tiktok_fallback_total` > 5/phút | Hết quota $5/tháng | Nạp thêm hoặc chờ reset tháng sau |
   | Log: `unexpected:KeyError` | Apify actor đổi schema | Pin version actor trong `.env`; báo dev update mapping |
   | TikWM fallback cũng fail → list rỗng | Cả 2 nguồn đều chết | Cân nhắc bật mock data dự phòng (giữ behavior cũ) |

5. **Khi nào cần dev can thiệt**
   - Schema break: cần update `tiktok_apify_source.py`
   - Actor deprecated: cần đổi sang actor khác + update `APIFY_TIKTOK_ACTOR_ID`
   - TikWM chết hẳn: cần tìm fallback khác hoặc accept mất data

6. **Cost reference**
   - Bảng CU / lần scrape
   - Estimate quota dùng hàng tháng dựa trên traffic thực
   - Link Apify pricing

## Task 2: Cập nhật `.env.example`

```bash
# Thêm vào apps/api/.env.example (KHÔNG commit giá trị thật)

# ─── TikTok scraping (optional, fallback tự động nếu không có) ───
# Đăng ký miễn phí $5/tháng tại https://console.apify.com/
APIFY_TOKEN=your_apify_token_here
APIFY_TIKTOK_ACTOR_ID=clockworks/tiktok-scraper
TIKTOK_APIFY_TIMEOUT_S=90
```

## Task 3: CI guard

### File: `.github/workflows/tiktok-apify-guard.yml` (hoặc thêm vào workflow có sẵn)

```yaml
name: tiktok-apify-guard

on: [pull_request]

jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e apps/api -e packages/agents
      - run: |
          pytest apps/api/tests/unit/test_apify_client.py \
                 apps/api/tests/unit/test_tiktok_apify_source.py \
                 apps/api/tests/unit/test_tiktok_smart_fallback.py \
                 --cov=ca_agents.clients.apify_client \
                 --cov=ca_agents.sources.tiktok_apify_source \
                 --cov-fail-under=85 \
                 -v
      - run: |
          # Integration test sẽ skip vì không có APIFY_TOKEN — verify chỉ skip
          pytest apps/api/tests/integration/test_tiktok_live.py -v
```

### Đảm bảo

- Unit test **luôn pass** trong CI (mock toàn bộ)
- Integration test **luôn skip** trong CI (không có token) — không được fail
- Coverage ≥ 85% gate fail PR nếu dưới ngưỡng

## Task 4: Rollout

### Bước 1 — Dev (đã xong ở Phase 1-4)
- Code merged vào branch chính
- Test local xanh

### Bước 2 — Staging
1. Pull code mới về staging
2. Set `APIFY_TOKEN` trong `.env` của staging
3. Restart API service
4. Chạy `python scripts/smoke_tiktok_apify.py` → verify có items
5. Mở UI `/page-quan` → verify TikTok items hiển thị
6. Kiểm tra log 15 phút: không có `tiktok_source_fallback` quá 1 lần

### Bước 3 — Production (canary)
1. Deploy cho 1 tenant / 1 region trước (nếu có multi-tenant)
2. Monitor metric `tiktok_fallback_total` trong 24h
3. Nếu fallback ≤ 1 lần/giờ → rollout toàn bộ
4. Nếu fallback > 5 lần/giờ → rollback (xem bước 4)

### Bước 4 — Rollback procedure
```bash
# 1. Tắt Apify bằng cách xóa token (giữ code, tắt config)
unset APIFY_TOKEN
# hoặc trong .env: APIFY_TOKEN=

# 2. Restart service
systemctl restart ca-api

# 3. Verify: TikWM fallback đang chạy
python scripts/smoke_tiktok_apify.py
# → in "⚠️ Apify fail, đang dùng fallback"
```

Rollback an toàn vì code có try/except: xóa token → Apify raise `ApifyError("chưa cấu hình")` → fallback TikWM chạy ngay.

## Task 5: Update docs liên quan

| File | Sửa gì |
|---|---|
| `docs/team.md` | Không cần (trừ khi có team TikTok) |
| `README.md` | Nếu có section "Data sources" → thêm Apify |
| `docs/runbooks/index.md` (nếu có) | Thêm link `tiktok-scraping.md` |
| `docs/THIRD_PARTY.md` | Thêm Apify vào bảng vendor |

## Kiểm tra "Phase done"

- [ ] `docs/runbooks/tiktok-scraping.md` đã tạo, có 6 sections
- [ ] `apps/api/.env.example` đã có 3 dòng mới
- [ ] CI workflow tiktok-apify-guard chạy xanh trên PR
- [ ] Staging đã deploy, smoke pass
- [ ] Rollback procedure đã test 1 lần (verify TikWM fallback hoạt động khi xóa token)
- [ ] Metric dashboard link đã share cho team

## Definition of Done (toàn bộ plan)

- [x] Plan có 5 phases, mỗi phase có file riêng
- [ ] Apify là primary path cho mọi call site TikTok
- [ ] TikWM chỉ chạy khi Apify raise error / trả rỗng
- [ ] Có log JSON phân biệt rõ `source=apify` vs `source=tiktokwm`
- [ ] Có metric (nếu infra cho phép)
- [ ] Test: unit mock + integration live + fallback path + smoke e2e
- [ ] Runbook đầy đủ 6 sections
- [ ] `.env.example` đồng bộ
- [ ] CI guard pass
- [ ] Staging verified, production rollout có rollback plan

## Reference

- Phase 1-4 outputs (đã xong)
- Existing runbook pattern: `docs/runbooks/facebook-page-connect.md`
- Existing CI: `.github/workflows/`