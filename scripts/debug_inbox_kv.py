"""Dump KV inbox_rang_buoc để xem shape thật của dữ liệu."""
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, "/app/apps/api/src")

from ca_api.persist import kv_get

items = kv_get("inbox_rang_buoc", [])
print(f"type={type(items).__name__} len={len(items) if isinstance(items, list) else 'n/a'}")
print(json.dumps(items, ensure_ascii=False, indent=2)[:6000])
