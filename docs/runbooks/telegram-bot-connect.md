# Nối Telegram Bot (kênh phụ)

Telegram miễn phí và ổn cho kỹ thuật; quán VN thường ưu tiên Zalo — vẫn nên có bot dự phòng.

## 1. Tạo bot

1. Mở Telegram → chat [@BotFather](https://t.me/BotFather)
2. `/newbot` → đặt tên → nhận **HTTP API token**

## 2. `.env`

```env
CA_AGENT_MODE=live
NHIPQUAN_TELEGRAM_BOT_TOKEN=123456:ABC...
NHIPQUAN_TELEGRAM_WEBHOOK_SECRET=chuoi_bi_mat_tu_chon
# optional nếu không dùng Zalo làm mặc định:
# NHIPQUAN_MSG_BACKEND=telegram
```

## 3. Webhook (bắt buộc để nhận tin)

Telegram không đẩy tin vào `localhost`. Cần HTTPS công khai trỏ về API (`:8000`).

**Dev với ngrok** (ví dụ):

```powershell
ngrok http 8000
```

Copy URL `https://….ngrok-free.dev`, rồi gắn webhook (PowerShell):

```powershell
# Thay TOKEN, SECRET, NGROK_URL
curl "https://api.telegram.org/bot$TOKEN/setWebhook?url=$NGROK_URL/api/v1/channels/telegram/webhook&secret_token=$SECRET&drop_pending_updates=true"
```

Mỗi lần **đổi URL ngrok** phải `setWebhook` lại. Cửa sổ ngrok chỉ hiện dòng `POST /api/v1/channels/telegram/webhook` — đó là tín hiệu đã tới API; trả lời bot xem trong **Telegram chat**, tin vào inbox xem trên web `http://localhost:3000/inbox`.

Production:

```text
https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<domain>/api/v1/channels/telegram/webhook&secret_token=<NHIPQUAN_TELEGRAM_WEBHOOK_SECRET>
```

## 4. Bind

Giống Zalo: mã trên `/toi` → nhắn bot `/bind <mã>`.

## 5. Kiểm

`GET /api/v1/channels/status` → `telegram.connected: true`
