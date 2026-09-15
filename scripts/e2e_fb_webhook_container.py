"""E2E test webhook Facebook trong container: message + comment, đủ chữ ký HMAC.

Chạy: docker exec nhipquan-api-1 python /tmp/e2e_fb.py
Set APP_SECRET test trong process này (không đụng .env thật).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
os.environ["NHIPQUAN_FB_APP_SECRET"] = "test_secret_260915"

from ca_api.interfaces.http.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

SECRET = b"test_secret_260915"
PAGE_ID = os.environ.get("NHIPQUAN_FB_PAGE_ID", "").strip() or "1367177249801969"
PSID = "999888777_testcase"
client = TestClient(app)


def post_webhook(payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    sig = "sha256=" + hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    resp = client.post(
        "/api/v1/channels/facebook/webhook",
        content=body,
        headers={"Content-Type": "application/json", "x-hub-signature-256": sig},
    )
    try:
        return resp.status_code, resp.json()
    except Exception:  # noqa: BLE001
        return resp.status_code, {"raw": resp.text[:200]}


def msg_event(mid: str, text: str) -> dict:
    return {
        "object": "page",
        "entry": [{
            "id": PAGE_ID,
            "time": 1757890000000,
            "messaging": [{
                "sender": {"id": PSID},
                "recipient": {"id": PAGE_ID},
                "timestamp": 1757890000000,
                "message": {"mid": mid, "text": text},
            }],
        }],
    }


def comment_event(comment_id: str, text: str) -> dict:
    return {
        "object": "page",
        "entry": [{
            "id": PAGE_ID,
            "time": 1757890000000,
            "changes": [{
                "field": "feed",
                "value": {
                    "item": "comment",
                    "verb": "add",
                    "comment_id": comment_id,
                    "post_id": f"{PAGE_ID}_123456",
                    "created_time": 1757890000,
                    "message": text,
                    "from": {"id": "888777666_commenter", "name": "Khách Test"},
                },
            }],
        }],
    }


print("=== CASE 1: Messenger — hỏi menu (intent whitelist, kỳ vọng LLM) ===")
code, out = post_webhook(msg_event("mid.260915.case1.menu", "Cho em xin menu với ạ"))
print(f"HTTP {code} → {out}")

print()
print("=== CASE 2: Messenger — hỏi tự do (intent 'khac', kỳ vọng queue + template) ===")
code, out = post_webhook(msg_event("mid.260915.case2.vui", "Quán hôm nay có gì vui không ạ"))
print(f"HTTP {code} → {out}")

print()
print("=== CASE 3: COMMENT trên bài viết (kỳ vọng queue duyệt + template) ===")
code, out = post_webhook(comment_event("cmt_260915_case3", "Quán còn bàn trống không ạ?"))
print(f"HTTP {code} → {out}")

print()
print("=== KIỂM TRA KẾT QUẢ LƯU ===")
from ca_api.persist import kv_get  # noqa: E402

page = kv_get("page_quan", {}) or {}
for t in (page.get("threads") or []):
    if t.get("psid") == PSID:
        print(f"THREAD psid={PSID}")
        print(f"  intent={t.get('intent')} conf={t.get('confidence')} pending={t.get('pending_approval')}")
        print(f"  suggested_reply={str(t.get('suggested_reply'))[:200]!r}")
        for r in (t.get("replies") or []):
            print(f"  REPLY by={r.get('by')}: {str(r.get('text'))[:200]!r}")

print()
print("=== FB REVIEW QUEUE (inbox duyệt) ===")
try:
    from ca_api.persist import fb_review_list  # type: ignore[attr-defined]
    items = fb_review_list(status=None, limit=10)
    for it in items:
        print(f"  #{it.get('id')} src={it.get('source')} intent={it.get('detected_intent')} "
              f"policy={it.get('policy_action')} status={it.get('status')}")
        print(f"    text={str(it.get('message_text'))[:60]!r}")
        print(f"    proposed={str(it.get('proposed_response'))[:200]!r}")
except Exception as exc:  # noqa: BLE001
    print(f"  (fb_review_list lỗi: {exc})")
    # Thử qua API
    login = client.post("/api/v1/auth/login", json={"username": "lan", "password": "nhipquan"})
    token = login.json().get("access_token", "")
    if token:
        resp = client.get("/api/v1/page/fb-inbox?limit=10", headers={"Authorization": f"Bearer {token}"})
        for it in (resp.json().get("items") or [])[:10]:
            print(f"  #{it.get('id')} src={it.get('source')} intent={it.get('detected_intent')} "
                  f"policy={it.get('policy_action')} status={it.get('status')}")
            print(f"    text={str(it.get('message_text'))[:60]!r}")
            print(f"    proposed={str(it.get('proposed_response'))[:200]!r}")
