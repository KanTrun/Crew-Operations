"""Debug SCHEDULE_SOLVE error."""
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

# Chat SCHEDULE_SOLVE
r = urllib.request.Request(
    BASE + "/api/v1/copilot/message",
    data=json.dumps({"message": "Xếp lịch tuần sau giúp chị", "channel": "web"}).encode(),
    method="POST",
)
r.add_header("Content-Type", "application/json")
r.add_header("Authorization", f"Bearer {tok}")
with urllib.request.urlopen(r, timeout=60) as resp:
    body = json.loads(resp.read().decode("utf-8", "replace"))

print("Full response:")
print(json.dumps(body, ensure_ascii=False, indent=2))
