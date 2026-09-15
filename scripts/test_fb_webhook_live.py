"""Test webhook Facebook trong container — mô phỏng tin nhắn Messenger thật.

Gửi POST /api/v1/channels/facebook/webhook với payload chuẩn Meta,
x-signature-256 hợp lệ, rồi đọc kết quả + inbox để xem bot trả lời gì.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8000"
APP_SECRET = None  # sẽ đọc từ .env


def read_env(key: str) -> str:
    with open(".env", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
    return ""


APP_SECRET = read_env("NHIPQUAN_FB_APP_SECRET")
VERIFY = read_env("NHIPQUAN_FB_WEBHOOK_VERIFY")
PAGE_ID = read_env("NHIPQUAN_FB_PAGE_ID")
print(f"APP_SECRET={'có' if APP_SECRET else 'KHÔNG CÓ'} PAGE_ID={PAGE_ID}")

PSID = "123456789_testcase"
MID = f"mid.{hash('test_fb_ai_260915') % 10**12}"


def send_webhook(payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    sig = "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        BASE + "/api/v1/channels/facebook/webhook",
        data=body,
        headers={"Content-Type": "application/json", "x-hub-signature-256": sig},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"http_error": exc.code, "body": exc.read().decode("utf-8", "replace")[:300]}


def login() -> str:
    body = json.dumps({"username": "lan", "password": "nhipquan"}).encode()
    req = urllib.request.Request(
        BASE + "/api/v1/auth/login", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())["access_token"]


def get_threads(token: str) -> dict:
    req = urllib.request.Request(
        BASE + "/api/v1/page/threads",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


# ── Case 1: hỏi menu (whitelist auto) ──
payload = {
    "object": "page",
    "entry": [{
        "id": PAGE_ID,
        "time": 1757890000000,
        "messaging": [{
            "sender": {"id": PSID},
            "recipient": {"id": PAGE_ID},
            "timestamp": 1757890000000,
            "message": {"mid": MID, "text": "Cho em xin menu với ạ"},
        }],
    }],
}
print("\nGỬI: 'Cho em xin menu với ạ'")
print("Webhook response:", send_webhook(payload))

# ── Case 2: hỏi tự do (không keyword) ──
MID2 = f"mid.{hash('test_fb_ai_260915_b') % 10**12}"
payload2 = {
    "object": "page",
    "entry": [{
        "id": PAGE_ID,
        "time": 1757890001000,
        "messaging": [{
            "sender": {"id": PSID},
            "recipient": {"id": PAGE_ID},
            "timestamp": 1757890001000,
            "message": {"mid": MID2, "text": "Quán hôm nay có gì vui không ạ"},
        }],
    }],
}
print("\nGỬI: 'Quán hôm nay có gì vui không ạ'")
print("Webhook response:", send_webhook(payload2))

# ── Đọc inbox xem bot đã trả lời gì ──
print("\n=== THREADS SAU XỬ LÝ ===")
try:
    token = login()
    data = get_threads(token)
    threads = data.get("threads") or data.get("items") or []
    for t in threads[:3]:
        if t.get("psid") == PSID or t.get("id", "").endswith(PSID[-8:]):
            print(json.dumps(t, ensure_ascii=False, indent=2)[:2000])
except Exception as exc:  # noqa: BLE001
    print(f"Lỗi đọc threads: {exc!r}")
