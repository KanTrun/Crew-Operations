# Nối Zalo Official Account (kênh ưu tiên khi đủ điều kiện)

Bạn phải tự tạo OA trên tài khoản Zalo của quán — hệ thống không tạo hộ được.

## Chưa có giấy tờ / chưa xác thực OA?

**Bỏ qua Zalo tạm thời.** Dùng **Telegram bot** (không cần GPKD / xác thực doanh nghiệp) theo `docs/runbooks/telegram-bot-connect.md`. Cùng luồng: bind trên `/toi` → inbox → duyệt. Khi sau này có OA (cá nhân hoặc doanh nghiệp) + token, bật Zalo trong `.env` — code đã sẵn, không phải làm lại sản phẩm.

Thử OA cá nhân trên [oa.zalo.me](https://oa.zalo.me) nếu Zalo cho phép với SĐT; nhiều gói chat API vẫn đòi xác thực / phí — đừng kỳ vọng “OA miễn phí = đủ gửi tin”.

## 1. Tạo OA (khi đã sẵn sàng)

1. Vào [https://oa.zalo.me](https://oa.zalo.me) → đăng nhập Zalo quán.
2. Tạo Official Account (cá nhân hoặc doanh nghiệp theo gói Zalo).
3. **Đọc bảng giá** trước khi bật chat API — rủi ro R8: gói miễn phí có thể không đủ gửi tin.

## 2. App + token

1. Vào [https://developers.zalo.me](https://developers.zalo.me) → tạo ứng dụng gắn OA.
2. Bật quyền gửi/nhận tin nhắn phù hợp (CS / OA message).
3. Lấy **OA Access Token** (và làm mới theo chu kỳ Zalo yêu cầu).

## 3. Gắn vào NHỊP QUÁN

Trong `.env` (không commit):

```env
CA_AGENT_MODE=live
NHIPQUAN_ZALO_ENABLED=1
NHIPQUAN_ZALO_OA_ACCESS_TOKEN=...token...
NHIPQUAN_MSG_BACKEND=zalo
```

Cộng thêm một trong các key LLM (`GROQ_API_KEY` / `GEMINI_API_KEY` / …) để AG-MSG hiểu câu tiếng Việt thật.

## 4. Webhook

1. API công khai HTTPS trỏ tới: `POST https://<domain>/api/v1/channels/zalo/webhook`
2. Local/dev: dùng tunnel (cloudflared / ngrok) trỏ về `localhost:8000`.
3. Điền URL webhook trên Zalo Developers theo hướng dẫn app của bạn.

## 5. Bind nhân viên

1. Nhân viên đăng nhập web → **Ca của tôi** → **Lấy mã bind**.
2. Nhắn OA đúng một dòng: `/bind <mã>`.
3. Sau đó hỏi `xem lịch của tôi` hoặc gửi ý định đổi ca / xin nghỉ → vào **Hộp thư ràng buộc** để quản lý duyệt.

## 6. Kiểm

- `GET /api/v1/channels/status` (có Bearer) → `zalo.connected: true`
- Tin thật từ Zalo xuất hiện trong `/inbox` với chip `zalo`
- Không dùng endpoint replay cho vận hành quán
