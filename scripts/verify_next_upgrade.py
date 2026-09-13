"""Xác minh chính xác phiên bản `next` trước/sau thay đổi, từ git object thật.

Báo cáo đang ghi "15.5.23 -> 15.5.24" — cần kiểm chứng cả phạm vi khai báo
(package.json) lẫn bản phân giải thực tế (package-lock.json).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout


def pham_vi(pkg_json: str) -> str:
    d = json.loads(pkg_json)
    for nhom in ("dependencies", "devDependencies"):
        if "next" in d.get(nhom, {}):
            return f"{nhom}: {d[nhom]['next']}"
    return "khong thay"


def ban_phan_giai(lock: str) -> str:
    d = json.loads(lock)
    pkgs = d.get("packages", {})
    out = []
    for k, v in pkgs.items():
        if k.endswith("node_modules/next"):
            out.append(f"{k or '(root)'} -> {v.get('version')}")
    return " | ".join(out) or "khong thay"


def main() -> int:
    print("=== TRUOC (HEAD~2) ===")
    truoc_pkg = git("show", "HEAD~2:apps/web/package.json")
    truoc_lock = git("show", "HEAD~2:apps/web/package-lock.json")
    print(f"  package.json  {pham_vi(truoc_pkg)}")
    print(f"  lock phan giai: {ban_phan_giai(truoc_lock)}")

    print("=== SAU (working tree) ===")
    sau_pkg = (ROOT / "apps/web/package.json").read_text(encoding="utf-8")
    sau_lock = (ROOT / "apps/web/package-lock.json").read_text(encoding="utf-8")
    print(f"  package.json  {pham_vi(sau_pkg)}")
    print(f"  lock phan giai: {ban_phan_giai(sau_lock)}")

    print("=== node_modules thuc te (neu da cai) ===")
    nm = ROOT / "apps/web/node_modules/next/package.json"
    if nm.is_file():
        print(f"  next = {json.loads(nm.read_text(encoding='utf-8')).get('version')}")
    else:
        print("  (chua cai node_modules)")

    print("=== bao-cao.md noi gi ve ban nang cap ===")
    bc = (ROOT / "plans/260913-1151-kiem-thu-toan-dien-v3/bao-cao.md").read_text(encoding="utf-8")
    for i, line in enumerate(bc.splitlines(), 1):
        if re.search(r"15\.5\.2\d|CVE-2026-75604|GHSA-p293", line):
            print(f"  {i}: {line.strip()[:170]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
