# Hướng dẫn cấu hình gửi Gmail qua SMTP

Tính năng gửi email trong **NHỊP QUÁN** phục vụ thông báo phân ca, đổi ca, bù ca khẩn và gửi tin nhắn từ Copilot hoặc trang quản trị tới nhân viên.

---

## 1. Chuẩn bị tài khoản Gmail (Tạo Google App Password)

> [!IMPORTANT]
> Google đã ngừng hỗ trợ đăng nhập trực tiếp bằng mật khẩu tài khoản (Less Secure Apps). Bạn **bắt buộc** phải sử dụng **Mật khẩu ứng dụng (App Password)** 16 ký tự.

1. Đăng nhập vào tài khoản Google bạn muốn dùng để gửi mail (ví dụ email của quán hoặc của quản lý).
2. Bật **Xác minh 2 bước (2-Step Verification)** nếu chưa bật:
   - Truy cập: [Google Account Security](https://myaccount.google.com/security)
   - Chọn **Xác minh 2 bước** và làm theo hướng dẫn.
3. Tạo **Mật khẩu ứng dụng (App Password)**:
   - Truy cập trực tiếp: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   - Nhập tên ứng dụng (ví dụ: `Nhip Quan` hoặc `Crew Operations`).
   - Nhấn **Tạo (Create)**.
   - Google sẽ hiển thị một mật khẩu 16 chữ cái (ví dụ: `abcd efgh ijkl mnop`). Hãy sao chép chuỗi này.

---

## 2. Cấu hình file `.env`

Mở file `.env` ở thư mục gốc dự án và thêm/cập nhật các biến sau:

```env
# 1. Chế độ live (bắt buộc để gửi email thật qua SMTP)
CA_AGENT_MODE=live

# 2. Cấu hình SMTP Gmail
NHIPQUAN_SMTP_HOST=smtp.gmail.com
NHIPQUAN_SMTP_PORT=587
NHIPQUAN_SMTP_USER=email_cua_ban@gmail.com
NHIPQUAN_SMTP_PASSWORD=abcd efgh ijkl mnop
NHIPQUAN_SMTP_FROM="Nhịp Quán <email_cua_ban@gmail.com>"
```

*Ghi chú:*
- Cổng `587` sử dụng mã hóa TLS (STARTTLS). Hệ thống cũng hỗ trợ cổng `465` (SSL).
- Mật khẩu ứng dụng có thể giữ nguyên khoảng trắng hoặc viết liền, hệ thống đều tự động xử lý.

---

## 3. Kiểm tra kết nối từ dòng lệnh (CLI Test)

Dự án đã tích hợp sẵn script kiểm tra nhanh mà không cần khởi động toàn bộ ứng dụng:

```powershell
python scripts/test_send_mail.py --to nguoinhan@gmail.com
```

Nếu thành công, bạn sẽ nhận được thông báo:
```text
============================================================
KIỂM TRA GỬI EMAIL SMTP / GMAIL — NHỊP QUÁN
============================================================
Host:     smtp.gmail.com
Port:     587
User:     email_cua_ban@gmail.com
Password: ****************
Sender:   "Nhịp Quán <email_cua_ban@gmail.com>"
To:       nguoinhan@gmail.com
------------------------------------------------------------
Đang kết nối SMTP và gửi email...
[THÀNH CÔNG] Đã gửi email tới: nguoinhan@gmail.com
```

---

## 4. Cách thức hoạt động trong hệ thống

### A. Nhân viên cập nhật email cá nhân
1. Nhân viên đăng nhập vào web app (`http://localhost:3000`).
2. Vào trang **Ca của tôi** (`/toi`).
3. Tại thẻ **Hồ sơ cá nhân & Email nhận thông báo ca**, nhập địa chỉ Gmail và bấm **Lưu Gmail**.
4. Địa chỉ này được lưu vào bảng `users` trong cơ sở dữ liệu (`PATCH /api/v1/me/profile/email`).

### B. Ra lệnh gửi qua AG-COPILOT
Chủ quán hoặc Quản lý có thể chat tự nhiên với Copilot:
> *"Gửi email cho Minh thông báo tuần sau đổi ca sáng sang ca chiều"*

Copilot sẽ nhận diện ý định `SEND_MAIL`, tự động tra cứu email của nhân viên `Minh` trong DB và thực hiện gửi qua `ag_mail`.

### C. Gửi qua API trực tiếp
Endpoint: `POST /api/v1/mail/send` (yêu cầu quyền quản lý/chủ quán):
```json
{
  "to_nv_ids": ["nv_03"],
  "subject": "Thông báo họp ca sáng",
  "body": "Ngày mai họp quán lúc 7h30 nhé cả đội."
}
```

---

## 5. Xử lý lỗi thường gặp

| Hiện tượng | Nguyên nhân | Cách khắc phục |
|---|---|---|
| `535 5.7.8 Username and Password not accepted` | Dùng mật khẩu Gmail thông thường thay vì App Password, hoặc gõ sai email | Tạo lại App Password tại `https://myaccount.google.com/apppasswords` và cập nhật vào `NHIPQUAN_SMTP_PASSWORD`. |
| Mail báo trạng thái `queued_replay` | `CA_AGENT_MODE` đang để `replay` | Chuyển `CA_AGENT_MODE=live` trong file `.env`. |
| `no_emails_found` | Nhân viên chưa cập nhật email | Yêu cầu nhân viên vào `/toi` để lưu Gmail. |
| Connection Timeout / Network unreachable | Tường lửa hoặc mạng chặn cổng 587 | Đổi `NHIPQUAN_SMTP_PORT=465` hoặc kiểm tra mạng internet. |
