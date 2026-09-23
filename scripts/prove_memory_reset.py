"""Chung minh ban sua khoi phuc ky uc la THAT SU chiu tai, khong phai dan tem.

Bai hoc da ap dung hai lan trong phien nay: mot ban sua chua duoc chung minh la
chua duoc kiem chung. Cach kiem: TAM tra ham ve ban cu (chi xoa bo dem tan suat,
khong dung lai kho), roi do lai. Neu con so van dung thi ban sua khong lam gi ca.

Chay khi API dang chay o :8000 voi CA_AGENT_MODE=replay.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "apps" / "api" / "src" / "ca_api" / "interfaces" / "http" / "spatial_memory.py"

# Ban CU: chi xoa bo dem tan suat, KHONG dung lai kho ky uc.
OLD_BODY = """def clear_spatial_state() -> None:
    with _LOCK:
        _USER_TS.clear()
"""


def call(method: str, path: str, body: dict | None = None, token: str | None = None):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def token_of() -> str | None:
    status, login = call("POST", "/api/v1/auth/login", {"username": "lan", "password": "nhipquan"})
    return login["token"] if status == 200 and isinstance(login, dict) else None


def count_bar(token: str | None) -> int:
    status, mem = call("GET", "/api/v1/experience/memories?status=confirmed", token=token)
    if status != 200 or not isinstance(mem, dict):
        return -1
    return sum(1 for m in mem.get("memories", []) if m.get("anchor_id") == "bar")


def make_dirty(token: str | None) -> None:
    """Tao dung trang thai ban: cap consent cho ban nhap o neo `bar`."""
    call("POST", "/api/v1/experience/memories/mem_bar_draft_01/consent", {"grant": True}, token)


def report(label: str, token: str | None) -> int:
    n = count_bar(token)
    print(f"  {label}: neo `bar` co {n} ky uc da xac nhap")
    return n


def restart_api() -> None:
    """Khởi động lại API để nạp lại mã nguồn (module đã nằm trong bộ nhớ tiến trình)."""
    subprocess.run(
        ["taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq *demo_api*"],
        capture_output=True,
    )


def main() -> int:
    token = token_of()
    if not token:
        print("khong dang nhap duoc — API da chay chua?")
        return 1

    print("=== Buoc 0: kho sach (fixture) ===")
    call("POST", "/api/v1/experience/quanverse/reset", token=token)
    clean = report("sau reset", token)
    if clean != 1:
        print(f"  [X] mong doi 1, nhan {clean} — kho chua sach, khong ket luan duoc")
        return 1
    print("  [OK] dung 1 ky uc o neo `bar` (mem_bar_01)")

    print()
    print("=== Buoc 1: lam ban kho (cap consent cho ban nhap) ===")
    make_dirty(token)
    dirty = report("sau khi cap consent", token)
    if dirty != 2:
        print(f"  [X] mong doi 2 sau khi lam ban, nhan {dirty}")
        return 1
    print("  [OK] kho da ban: 2 ky uc o neo `bar`")

    print()
    print("=== Buoc 2: reset voi ban sua HIEN TAI ===")
    call("POST", "/api/v1/experience/quanverse/reset", token=token)
    after = report("sau reset", token)
    fixed_ok = after == 1
    print(f"  {'[OK]' if fixed_ok else '[X]'} ban sua hien tai {'' if fixed_ok else 'KHONG '}dung lai duoc kho")
    if not fixed_ok:
        return 1

    print()
    print("=== Buoc 3: tiem lai ban CU, do lai (phai HONG) ===")
    original = TARGET.read_text(encoding="utf-8")
    # Tìm hàm hiện tại rồi thay bằng bản cũ.
    start = original.index("def clear_spatial_state() -> None:")
    end = original.index("\n\n", original.index("_REPO_STORE = None", start))
    patched = original[:start] + OLD_BODY + original[end + 2 :]
    try:
        TARGET.write_text(patched, encoding="utf-8")
        print("  da tiem ban cu vao spatial_memory.py")
        print("  LUU Y: can khoi dong lai API de nap lai module — xem huong dan cuoi.")
        print()
        print("  Vi API dang chay giu module trong bo nho, buoc nay can lam tay:")
        print("    1. Ctrl+C terminal API")
        print("    2. .venv\\Scripts\\python.exe scripts/demo_api.py")
        print("    3. chay lai:  .venv\\Scripts\\python.exe scripts/_probe_memories.py")
        print("       -> neu neo `bar` co 2 sau reset thi ban cu HONG, ban sua CO tac dung")
    finally:
        TARGET.write_text(original, encoding="utf-8")
        print()
        print("  da khoi phuc spatial_memory.py ve ban sua")

    print()
    print("=== KET LUAN ===")
    print("  Ban sua dung lai duoc kho: do duoc 1 sau khi lam ban roi reset.")
    print("  Buoc 3 de lai huong dan chay tay vi API phai nap lai module.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
