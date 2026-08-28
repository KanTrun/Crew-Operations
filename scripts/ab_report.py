#!/usr/bin/env python3
"""In bảng A/B sơ bộ (API /api/v1/ab)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))

from ca_api.interfaces.http.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def main() -> int:
    data = TestClient(app).get("/api/v1/ab").json()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
