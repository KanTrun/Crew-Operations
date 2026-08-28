# Nối Facebook Page (Page quán)

Không giả lập bài/comment. Chỉ nối khi đã có Page thật.

## 1. Tạo Page

1. Facebook → tạo **Trang** (Page) cho quán.
2. Bạn phải là admin Page.

## 2. Meta App

1. [https://developers.facebook.com](https://developers.facebook.com) → tạo app loại Business.
2. Thêm sản phẩm Messenger / Webhooks / pages_manage_posts (tùy quyền cần).
3. App Review có thể bắt buộc trước khi public — trước đó chỉ test user/admin.

## 3. Token

1. Graph API Explorer hoặc Business settings → **Page access token** dài hạn.
2. Lưu Page ID.

## 4. `.env`

```env
CA_AGENT_MODE=live
NHIPQUAN_FB_PAGE_TOKEN=...
NHIPQUAN_FB_PAGE_ID=...
NHIPQUAN_PAGE_MODE=live
```

## 5. Trong NHỊP QUÁN

- UI: `/page-quan` — trống cho đến khi webhook/Graph đổ thread thật.
- API status: `GET /api/v1/page/status` → `connected: true`
- Webhook (khi bật): cùng pattern `/api/v1/channels/...` — mở rộng sau khi App Review xong; hiện store nhận reply/draft nội bộ khi đã có token.

## 6. Ranh giới sản phẩm

- Không CRM giữ chân khách cá nhân (ADR-011).
- Thread khó xử → **Tạo việc treo**, không auto-marketing.
