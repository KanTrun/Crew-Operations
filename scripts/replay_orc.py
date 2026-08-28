#!/usr/bin/env python3
"""Replay một phiên orc theo khóa idempotency (make replay PHIEN=...)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))

from ca_api.interfaces.http.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def main() -> int:
    key = (sys.argv[1] if len(sys.argv) > 1 else None) or os.environ.get("PHIEN")
    if not key:
        print("usage: make replay PHIEN=<idempotency-key>", file=sys.stderr)
        return 2
    c = TestClient(app)
    login = c.post(
        "/api/v1/auth/login",
        json={"username": "lan", "password": "nhipquan"},
    )
    assert login.status_code == 200, login.text
    h = {"Authorization": f"Bearer {login.json()['token']}"}
    body = {"key": key}
    first = c.post("/api/v1/orc/dispatch", json=body, headers=h).json()
    second = c.post("/api/v1/orc/dispatch", json=body, headers=h).json()
    out = {
        "phien": key,
        "lan_1": {"replayed": first.get("replayed"), "n": first.get("n")},
        "lan_2": {"replayed": second.get("replayed"), "n": second.get("n")},
        "ok": second.get("replayed") is True,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
