#!/usr/bin/env python3
"""Script định dạng email điều hành gửi nhà cung cấp hoặc toàn thể nhân viên quán.

Dùng cho AG-MAILWRITER và AG-COPILOT.
"""

from __future__ import annotations

import json
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def format_email(
    email_type: str,
    recipient_name: str,
    items_or_points: list[str],
    sender_name: str = "Ban Quản Lý Nhịp Quán",
) -> dict[str, Any]:
    """Soạn email chuẩn mực."""
    bullet_points = "\n".join(f"- {pt}" for pt in items_or_points)

    if email_type == "vendor_order":
        subject = f"[ĐẶT HÀNG] Nhịp Quán Coffee — Đơn hàng gửi {recipient_name}"
        body = f"""Kính gửi quý đối tác {recipient_name},

Nhịp Quán Coffee xin gửi danh mục nguyên vật liệu cần nhập cho đợt tiếp theo:
{bullet_points}

Địa điểm nhận hàng: Quầy Bar Nhịp Quán Coffee.
Kính nhờ quý đối tác xác nhận thời gian giao hàng và xuất hóa đơn VAT giúp quán.

Trân trọng,
{sender_name}"""

    else:
        subject = f"[THÔNG BÁO NỘI BỘ] Gửi toàn thể nhân sự — {recipient_name}"
        body = f"""Thân gửi các bạn nhân viên {recipient_name},

Ban quản lý xin gửi thông báo quan trọng trong tuần này:
{bullet_points}

Các bạn vui lòng kiểm tra lịch làm việc trên ứng dụng PWA và phản hồi nếu có vướng mắc.

Thân ái,
{sender_name}"""

    return {
        "success": True,
        "subject": subject,
        "body": body,
        "recipient": recipient_name,
    }


def main() -> int:
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        t = data.get("email_type", "vendor_order")
        r = data.get("recipient", "Nhà Cung Cấp")
        pts = data.get("items", [])
        res = format_email(t, r, pts)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    # Dữ liệu self-test
    res = format_email("vendor_order", "Công ty Sữa DalatMilk", ["12 hộp sữa tươi thanh trùng", "5 lon sữa đặc"])
    if res["success"] is True and "DalatMilk" in res["subject"]:
        print(json.dumps({"smoke_test": "PASSED", "preview": res["subject"]}, ensure_ascii=False, indent=2))
        return 0
    else:
        print(json.dumps({"smoke_test": "FAILED"}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
