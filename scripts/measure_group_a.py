#!/usr/bin/env python3
"""Chạy toàn bộ số đo nhóm A (fixture / replay / script)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    run([PY, "scripts/solve_tuan.py"])
    run([PY, "scripts/verify_hard.py"])
    run([PY, "scripts/rebuild_golden_messages.py"])
    run([PY, "scripts/eval_ag_tkb.py"])
    run([PY, "scripts/eval_ag_msg.py"])
    run([PY, "scripts/eval_override_demo_week.py"])
    run([PY, "scripts/eval_vf_escalations.py"])
    # #10 playbook counts via API
    sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))
    from ca_api.interfaces.http.main import app  # noqa: E402
    from fastapi.testclient import TestClient  # noqa: E402

    c = TestClient(app)
    tok = c.post(
        "/api/v1/auth/login", json={"username": "lan", "password": "nhipquan"}
    ).json()["token"]
    r = c.post(
        "/api/v1/cam-nang/chay-8-buoc",
        headers={"Authorization": f"Bearer {tok}"},
        json={"noi_dung": "Không ai làm ca tối thứ 7", "nguon": "fixture"},
    ).json()
    print("#10 playbook:", json.dumps(r.get("thong_ke", r), ensure_ascii=False))
    print("Done measure_group_a")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
