#!/usr/bin/env python3
"""Start API. Other terminal: cd apps/web && npm run dev"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

os.environ.setdefault("NHIPQUAN_PBKDF2_VONG", "1000")
os.environ.setdefault("NHIPQUAN_DISABLE_RATE_LIMIT", "true")

ROOT = Path(__file__).resolve().parents[1]
for p in [
    "apps/api",
    "packages/contracts",
    "packages/agents",
    "packages/solver",
    "packages/playbook",
    "packages/gates",
    "packages/opsengine",
]:
    sys.path.insert(0, str(ROOT / p / "src"))

if __name__ == "__main__":
    host = os.environ.get("NHIPQUAN_API_HOST", "0.0.0.0")
    port = int(os.environ.get("NHIPQUAN_API_PORT", "8000"))
    print(f"API http://{host}:{port}/health")
    print("Login lan / nhipquan — open http://localhost:3000/login")
    print("Web: cd apps/web && npm run dev")
    uvicorn.run("ca_api.interfaces.http.main:app", host=host, port=port)
