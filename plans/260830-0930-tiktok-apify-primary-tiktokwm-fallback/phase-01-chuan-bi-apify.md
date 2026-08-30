---
title: "Phase 01 — Chuẩn bị Apify & schema mapping"
description: "Đăng ký Apify, lấy token, test actor thật trên Console, đo CU/12 video, chốt schema mapping."
status: planned
priority: P2
effort: "15min"
tags: [apify, setup, schema, phase-01]
created: 2026-08-30
blockedBy: []
blocks: [phase-02]
---

# Phase 01 — Chuẩn bị Apify & schema mapping

## Mục tiêu

Có trong tay: Apify token, schema output thật của `clockworks/tiktok-scraper`, con số compute unit cho 12 video, file `.env` cập nhật.

## Task list

| # | Task | Acceptance | Time |
|---|------|------------|------|
| 1.1 | Đăng ký Apify account | Có email xác nhận | 5 min |
| 1.2 | Lấy `APIFY_TOKEN` từ Settings → Integrations → Token | Token 32+ ký tự bắt đầu `apify_api_` | 2 min |
| 1.3 | Mở Apify Console → Store → search `clockworks/tiktok-scraper` | Thấy actor có rating ≥ 4★ | 2 min |
| 1.4 | Test input: `{"searchQueries": ["xuhuong"], "maxItems": 12, "proxyCountryCode": "VN"}` | Run SUCCEEDED, có ≥ 10 items | 3 min |
| 1.5 | Đo `computeUnits` từ log của run ở bước 1.4 | Ghi nhận con số vào file này | 1 min |
| 1.6 | Copy 1 item JSON mẫu từ dataset output | Dán vào `phase-01-schema-sample.json` cùng folder | 1 min |
| 1.7 | Thêm config vào `.env.example` (KHÔNG commit `.env` thật) | 3 dòng: `APIFY_TOKEN`, `APIFY_TIKTOK_ACTOR_ID`, `TIKTOK_APIFY_TIMEOUT_S` | 1 min |

## Output mong đợi

- `APIFY_TOKEN` đã có trong `.env` local (không push Git)
- File `phase-01-schema-sample.json` chứa 1 item mẫu
- Số CU/12 video đã biết → estimate được quota dùng hàng tháng
- `.env.example` đã có 3 biến mới

## Schema mapping (dự kiến, sẽ xác nhận lại ở bước 1.6)

| TrendItem field | Apify field (clockworks) | Ghi chú |
|---|---|---|
| `id` | `id` (video id) + prefix `apify_tiktok_` | Đảm bảo unique |
| `tieu_de` | `text` | Cắt 65 ký tự + prefix emoji |
| `tiktok_url` | `webVideoUrl` | Fallback build từ author+id |
| `cum_tu_khoa_viral` | extract từ `text` | Dùng `extract_core_tiktok_keyword` |
| `play_count` | `videoMeta.playCount` | int → format `f"{n:,}"` |
| `digg_count` | `videoMeta.diggCount` | int → format |
| `comment_count` | `videoMeta.commentCount` | int → format |
| `author.username` | `authorMeta.name` | |
| `author.nickname` | `authorMeta.nickName` | |
| `binh_luan_that_tiktok` | `comments[]` (nếu input yêu cầu) | Top 5, format `@user: "text" (❤️ N tim)` |
| `tu_khoa_hashtag` | extract từ `text` | Regex `#\w+` |
| `thoi_gian_cao` | `videoMeta.createTimeISO` | Format `%H:%M:%S %d/%m/%Y` |

## Kiểm tra "Phase done" trước khi qua Phase 2

- [ ] `APIFY_TOKEN` có trong `.env` local
- [ ] File `phase-01-schema-sample.json` đã tạo
- [ ] Số CU đã ghi vào file này
- [ ] `.env.example` đã có 3 biến mới
- [ ] User review & duyệt schema mapping ở bảng trên

## Ghi chú quan trọng

- **KHÔNG commit `.env`** — chỉ commit `.env.example` với placeholder `your_apify_token_here`
- Apify token có quyền scope full account, lộ là mất luôn account → add vào `.gitignore` nếu chưa có
- Pin actor version: `clockworks/tiktok-scraper` (latest) là đủ, không cần pin version strict ở phase này

## Reference

- Apify Console: https://console.apify.com/
- Actor docs: https://apify.com/clockworks/tiktok-scraper
- Auth docs: https://docs.apify.com/api/v2#/reference/authentication