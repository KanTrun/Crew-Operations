"""Kiểm tra trạng thái kết nối Facebook thật: subscribed_apps, page health, DB review queue."""

from __future__ import annotations

import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

TOKEN = os.environ.get("NHIPQUAN_FB_PAGE_TOKEN", "").strip()
PAGE_ID = os.environ.get("NHIPQUAN_FB_PAGE_ID", "").strip()
print(f"PAGE_ID={PAGE_ID} TOKEN={'có (' + TOKEN[:12] + '...)' if TOKEN else 'KHÔNG'}")


def graph(path: str) -> dict:
    url = f"https://graph.facebook.com/v21.0/{path}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return {"http_error": exc.code, "body": exc.read().decode("utf-8", "replace")[:200]}


print("\n=== 1. Page health (/me) ===")
me = graph(f"me?fields=name,id&access_token={TOKEN}")
print(json.dumps(me, ensure_ascii=False)[:300])

print("\n=== 2. App đã subscribe webhook page chưa (subscribed_apps) ===")
sub = graph(f"{PAGE_ID}/subscribed_apps?access_token={TOKEN}")
print(json.dumps(sub, ensure_ascii=False)[:500])
if not sub.get("data"):
    print(">>> RỖNG = Meta KHÔNG GỬI webhook nào cả → bot không bao giờ thấy tin nhắn thật!")

print("\n=== 3. DB: fb_review queue gần đây ===")
try:
    pass  # type: ignore
except Exception:
    pass
try:
    import ca_api.persist as p

    # Thử các hàm có thể có
    names = [n for n in dir(p) if "conn" in n.lower() or "session" in n.lower() or "engine" in n.lower()]
    print("persist helpers:", names)
except Exception as exc:
    print("persist introspect lỗi:", exc)

# Đọc trực tiếp qua SQLAlchemy của app
try:
    from ca_api.persist import _get_engine
except Exception:
    _get_engine = None

if _get_engine:
    with _get_engine().connect() as conn:
        rows = conn.execute(
            "SELECT id, source, detected_intent, policy_action, status, message_text, created_at "
            "FROM fb_review ORDER BY id DESC LIMIT 10"
        ).fetchall()
        print(f"Số review gần đây: {len(rows)}")
        for r in rows:
            print(f"  #{r[0]} src={r[1]} intent={r[2]} policy={r[3]} status={r[4]}")
            print(f"    text={str(r[5])[:80]!r} at={r[6]}")
