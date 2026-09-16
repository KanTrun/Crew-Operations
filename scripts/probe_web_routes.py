"""Probe các route web chính trên stack Docker."""
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = [
    "/",
    "/dang-nhap",
    "/copilot",
    "/roster",
    "/thong-ke",
    "/ban-hang",
    "/menu",
    "/inbox",
    "/hop",
    "/khao-sat-gia",
    "/phieu",
    "/cai-dat",
]

ok = 0
for u in ROUTES:
    try:
        r = urllib.request.urlopen(urllib.request.Request("http://localhost:3000" + u), timeout=15)
        print(f"  {u} -> {r.status}")
        ok += 1
    except urllib.error.HTTPError as e:
        print(f"  {u} -> {e.code}")
    except Exception as e:
        print(f"  {u} -> ERR {str(e)[:60]}")

print(f"== {ok}/{len(ROUTES)} route trả 200 ==")
