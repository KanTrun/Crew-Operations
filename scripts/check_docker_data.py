r"""Kiểm tra dữ liệu nhân viên trong stack Docker qua HTTP."""
from __future__ import annotations

import json
import os
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:8000"
tok = json.load(open(os.path.join(os.environ["TEMP"], "nq_tok.json")))["token"]


def get(path: str):
    r = urllib.request.Request(BASE + path)
    r.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


staff = get("/api/v1/nguoi")
print("nguoi:", json.dumps(staff, ensure_ascii=False)[:600])
menu = get("/api/v1/menu")
print("menu:", json.dumps(menu, ensure_ascii=False)[:300])
