"""Check data in container."""
import json
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:8000"

# Login
r = urllib.request.Request(
    BASE + "/api/v1/auth/login",
    data=json.dumps({"username": "lan", "password": "nhipquan"}).encode(),
    method="POST",
)
r.add_header("Content-Type", "application/json")
with urllib.request.urlopen(r, timeout=30) as resp:
    tok = json.loads(resp.read().decode("utf-8", "replace"))["token"]

# Login chu_quan để xem danh sách user
r = urllib.request.Request(
    BASE + "/api/v1/auth/login",
    data=json.dumps({"username": "hung", "password": "nhipquan"}).encode(),
    method="POST",
)
r.add_header("Content-Type", "application/json")
with urllib.request.urlopen(r, timeout=30) as resp:
    tok_owner = json.loads(resp.read().decode("utf-8", "replace"))["token"]

# Get user list (chu_quan only)
r = urllib.request.Request(BASE + "/api/v1/nguoi", method="GET")
r.add_header("Authorization", f"Bearer {tok_owner}")
try:
    with urllib.request.urlopen(r, timeout=30) as resp:
        users = json.loads(resp.read().decode("utf-8", "replace"))
    items = users.get("items", [])
    print(f"User count: {len(items)}")
    for u in items[:10]:
        print(f"  - {u.get('username')} role={u.get('role')} nv_id={u.get('nv_id')}")
except Exception as e:
    print(f"Error getting users: {e}")

# Get TKB
r = urllib.request.Request(BASE + "/api/v1/tkb/tuan", method="GET")
r.add_header("Authorization", f"Bearer {tok}")
try:
    with urllib.request.urlopen(r, timeout=30) as resp:
        tkb = json.loads(resp.read().decode("utf-8", "replace"))
    print(f"\nTKB: {json.dumps(tkb, ensure_ascii=False, indent=2)[:500]}")
except Exception as e:
    print(f"Error getting TKB: {e}")
