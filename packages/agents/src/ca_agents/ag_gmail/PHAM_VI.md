# Phạm vi AG-GMAIL

## Nhiệm vụ

Quản lý tài khoản Gmail của quán: OAuth 2.0, đọc/gửi email, nhãn, bộ lọc.

## Đầu vào

- OAuth tokens (access token, refresh token) do tầng API cấp.
- Tham số truy vấn: `label_ids`, `query`, `max_results`, `page_token`.

## Đầu ra

- `GmailMessage`, `GmailLabel`, `GmailFilter`, `GmailAccount` (dataclass thuần).
- URL uỷ quyền OAuth, tokens sau khi đổi mã.

## Ràng buộc

- **KHÔNG** truy cập DB — việc lưu trữ do `ca_api.persist` đảm nhiệm.
- **KHÔNG** import `ca_api`, `sqlalchemy`, `psycopg` (gate `test_architecture`).
- Chỉ gọi Google API qua `googleapiclient` / `google-auth`.
- Mọi hàm nhận token qua tham số, không đọc biến môi trường bí mật.

## Vị trí trong hệ sinh thái

- `ag_gmail.oauth` — luồng OAuth 2.0 (uỷ quyền, đổi mã, làm mới, thu hồi).
- `ag_gmail.service` — gọi Gmail API (messages, labels, filters, threads).
- `ag_gmail.models` — dataclass kết quả.
- `ag_gmail.sync` — **đã chuyển sang `ca_api.services.gmail_sync`** vì cần ghi DB.

## Không thuộc phạm vi

- Lưu token vào DB (ở `ca_api.persist`).
- Lịch chạy đồng bộ định kỳ (ở worker/tầng API).
- Chất lượng nội dung mail (ở `ag_mailwriter`).
