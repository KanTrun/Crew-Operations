# Kiểm thử với Dữ Liệu Giả Lập từ Dịch Vụ Ngoài

> ⚠️ **QUAN TRỌNG**: Toàn bộ dữ liệu trong `data/mock_external/` là **DỮ LIỆU GIẢ LẬP (simulated/mock data)** được tạo thủ công để mô phỏng cấu trúc dữ liệu mà hệ thống nhận được từ các dịch vụ bên ngoài. **KHÔNG phải dữ liệu thật.** Mục đích là kiểm thử parser đảm bảo hệ thống hoạt động đúng với cấu trúc dữ liệu thực tế. Sau khi test xong phải **XÓA** thư mục `data/mock_external/`.

## Mục đích

Nghiên cứu cấu trúc dữ liệu (fields) mà hệ thống nhận được từ các dịch vụ ngoài, tạo dữ liệu giả lập khớp đúng cấu trúc đó, kiểm thử parser để đảm bảo hệ thống hoạt động, sau đó xóa dữ liệu giả lập.

## Các dịch vụ ngoài & cấu trúc dữ liệu

| # | Dịch vụ ngoài | File giả lập | Parser được test | Cấu trúc dữ liệu chính |
|---|--------------|--------------|------------------|------------------------|
| 1 | SerpApi Google Maps | `serpapi_gmaps_local_results.json` | `gmaps_serpapi_source`, `shopeefood_serpapi_source` | `local_results[]`: `place_id`, `title`, `rating`, `reviews`, `address`, `gps_coordinates{latitude,longitude}`, `thumbnail`, `place_id_search`, `description`, `type`, `extensions[]` |
| 2 | SerpApi Google Trends | `serpapi_gtrends.json` | `gtrends_serpapi_source` | `interest_over_time.timeline_data[]`, `related_queries.rising[]` (`query`, `value`, `extracted_value`), `related_queries.top[]` |
| 3 | ShopeeFood Delivery API | `shopeefood_delivery_api.json` | `delivery_camoufox_source`, `shopeefood_v2_parser` | `reply.restaurants[]`: `id`, `name`, `address`, `rating`, `review_count`, `distance_km`, `sold_count_text`, `dishes[]` |
| 4 | TikTok Apify actor | `tiktok_apify_items.json` | `tiktok_apify_source` | `id`, `text`, `createTimeISO`, `authorMeta{name,nickName}`, `webVideoUrl`, `stats{playCount,diggCount,...}`, `hashtags[]`, `comments[]` |
| 5 | Threads Apify actor | `threads_apify_items.json` | `threads_apify_source` | `id`, `text`, `publishedOn`, `user{username}`, `url`, `likeCount`, `replyCount`, `repostCount`, `replies[]` |
| 6 | Threads Official API | `threads_official_api.json` | `threads_official_api_source` | `data[]`: `id`, `text`, `media_type`, `permalink`, `timestamp`, `username`, `has_replies`, `is_quote_post`, `is_reply` |
| 7 | Threads Google Bridge (RSS) | `threads_google_rss.xml` | `threads_google_bridge_source` | RSS `<item>`: `<title>`, `<link>`, `<pubDate>`, `<description>` |
| 8 | Threads Trending (HTML) | `threads_trending_html.html` | `threads_trending_source` | HTML DOM: tiêu đề + `· [X] posts` + thumbnail |
| 9 | TikTok Camoufox (HTML) | `tiktok_camoufox_html.html` | `tiktok_camoufox_source` | HTML DOM: `data-e2e="search_top-item"`, `search-card-video-caption`, `video-views`, `search-card-user-unique-id` |
| 10 | Facebook Graph API | `facebook_webhook.json`, `facebook_page_posts.json` | `facebook_page` | Webhook: `entry[].messaging[].message.text`; Posts: `data[].message`, `created_time`, `permalink_url` |
| 11 | Gmail/SMTP | `gmail_smtp_result.json` | `ag_mail` | `MailResult`: `ok`, `sent[]`, `failed[]`, `mode`, `reason` |
| 12 | Google Maps Place | `gmaps_places.json` | `gmaps_menu_source` | `places[]`: `id`, `name`, `address`, `rating`, `review_count`, `distance_km`, `menu_photos[]` |

## Cách chạy test

```bash
python scripts/test_mock_external_data.py
```

Kết quả mong đợi: **Tất cả PASS** (các parser hoạt động đúng với cấu trúc dữ liệu giả lập).

## Quy trình

1. **Nghiên cứu** cấu trúc dữ liệu từ các source file trong `packages/agents/src/ca_agents/sources/` và `clients/`.
2. **Tạo dữ liệu giả lập** khớp đúng cấu trúc trong `data/mock_external/`.
3. **Test** parser với dữ liệu giả lập qua `scripts/test_mock_external_data.py`.
4. **Xác nhận** hệ thống hoạt động (tất cả PASS).
5. **Xóa** dữ liệu giả lập (`data/mock_external/`) sau khi test xong.

## Ghi chú an toàn

- Dữ liệu giả lập dùng tên quán/người dùng có tiền tố `Mock`/`mock_` để tránh nhầm lẫn với dữ liệu thật.
- Không có thông tin cá nhân thật, không có token/secret thật.
- Sau khi test xong, xóa toàn bộ thư mục `data/mock_external/` để không làm ô nhiễm dữ liệu hệ thống.