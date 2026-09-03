"""Kiểm tra cấu hình gửi Gmail / SMTP trực tiếp từ dòng lệnh.

Cách dùng:
  python scripts/test_send_mail.py --to nguoinhan@gmail.com
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "agents" / "src"))

# Đọc .env nếu có
_ENV_FILE = ROOT / ".env"
if _ENV_FILE.exists():
    with open(_ENV_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("\"'")
            if k and k not in os.environ:
                os.environ[k] = v


def main() -> int:
    parser = argparse.ArgumentParser(description="Test gửi email SMTP/Gmail của Nhịp Quán")
    parser.add_argument("--to", required=True, help="Email người nhận test")
    parser.add_argument("--subject", default="", help="Tiêu đề email (tùy chọn)")
    parser.add_argument("--body", default="", help="Nội dung email (tùy chọn)")
    args = parser.parse_args()

    host = os.environ.get("NHIPQUAN_SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("NHIPQUAN_SMTP_PORT", "587"))
    user = os.environ.get("NHIPQUAN_SMTP_USER", "").strip()
    password = os.environ.get("NHIPQUAN_SMTP_PASSWORD", "").strip()
    sender = os.environ.get("NHIPQUAN_SMTP_FROM", user or "").strip()

    print("=" * 60)
    print("KIỂM TRA GỬI EMAIL SMTP / GMAIL — NHỊP QUÁN")
    print("=" * 60)
    print(f"Host:     {host}")
    print(f"Port:     {port}")
    print(f"User:     {user or '[CHƯA CẤU HÌNH]'}")
    print(f"Password: {'*' * len(password) if password else '[CHƯA CẤU HÌNH]'}")
    print(f"Sender:   {sender or '[CHƯA CẤU HÌNH]'}")
    print(f"To:       {args.to}")
    print("-" * 60)

    if not user or not password:
        print("[LỖI] Thiếu thông tin đăng nhập SMTP!")
        print("Vui lòng thêm vào file .env:")
        print("  NHIPQUAN_SMTP_HOST=smtp.gmail.com")
        print("  NHIPQUAN_SMTP_PORT=587")
        print("  NHIPQUAN_SMTP_USER=ten_email_cua_ban@gmail.com")
        print("  NHIPQUAN_SMTP_PASSWORD=xxxx xxxx xxxx xxxx  (Mật khẩu ứng dụng 16 chữ cái)")
        return 1

    from ca_agents.ag_mail import send_mail

    subject = args.subject or f"[Nhịp Quán] Kiểm tra gửi email ({datetime.now().strftime('%H:%M:%S %d/%m/%Y')})"
    body = args.body or (
        "Xin chào,\n\n"
        "Đây là email kiểm tra tính năng gửi mail tự động từ hệ thống NHỊP QUÁN (Crew Operations).\n"
        f"Thời gian gửi: {datetime.now().isoformat()}\n"
        f"Gửi qua SMTP Host: {host}:{port}\n\n"
        "Nếu bạn nhận được email này, tính năng gửi Gmail đã hoạt động chính xác!\n"
    )

    print("Đang kết nối SMTP và gửi email...")
    res = send_mail(
        to_emails=[args.to],
        subject=subject,
        body=body,
        mode="smtp",  # buộc gửi thật qua SMTP
    )

    if res.ok and res.sent:
        print(f"[THÀNH CÔNG] Đã gửi email tới: {args.to}")
        print(f"Chi tiết: {res.sent}")
        return 0
    else:
        print("[THẤT BẠI] Không thể gửi email.")
        print(f"Nguyên nhân: {res.reason}")
        if res.failed:
            for f in res.failed:
                print(f"  - {f.get('email')}: {f.get('reason')}")
        print("\nGợi ý khắc phục:")
        print("1. Nếu gặp lỗi 'Username and Password not accepted' hoặc '535':")
        print("   - Bạn phải dùng 'Mật khẩu ứng dụng' (App Password) 16 ký tự, KHÔNG dùng mật khẩu Gmail chính.")
        print("   - Tạo tại: https://myaccount.google.com/apppasswords")
        print("2. Đảm bảo tài khoản Google đã bật 'Xác minh 2 bước' (2-Step Verification).")
        print("3. Kiểm tra cổng mạng: port 587 (TLS) hoặc 465 (SSL).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
