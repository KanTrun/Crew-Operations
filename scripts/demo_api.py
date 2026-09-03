#!/usr/bin/env python3
"""Start API. Other terminal: cd apps/web && npm run dev"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

os.environ.setdefault("NHIPQUAN_PBKDF2_VONG", "1000")

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
    print("API http://localhost:8000/health")
    print("Login lan / nhipquan — open http://localhost:3000/login")
    print("Web: cd apps/web && npm run dev")
    uvicorn.run("ca_api.interfaces.http.main:app", host="0.0.0.0", port=8000)
