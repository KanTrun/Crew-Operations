r"""Chạy Docker Compose toàn tuyến, chịu được đường dẫn có dấu tiếng Việt.

## Vì sao cần script này thay vì gọi `docker compose` trực tiếp

Repo có thể được clone vào thư mục có dấu, ví dụ `D:\CA-CÔNG-BẰNG`. Khi đó
BuildKit của Docker Desktop trên Windows nhét đường dẫn vào HTTP/2 header
`x-docker-expose-session-sharedkey`, và header HTTP chỉ nhận ASCII in được nên
build vỡ ngay từ đầu:

    failed to dial gRPC: ... header key "x-docker-expose-session-sharedkey"
    contains value with non-printable ASCII characters

Script tắt BuildKit (dùng builder classic) và ghim tên project về ASCII, nên
`make docker-up` chạy được bất kể thư mục tên gì. Đây là điều kiện để cổng ra
Sprint 8 (§14.9) — *"make demo trên 3 máy, một máy chưa từng cài dự án"* —
không phụ thuộc vào việc người chạy đặt tên thư mục thế nào.

## Dùng

    python scripts/docker_stack.py up      # build + khởi động, chờ healthy
    python scripts/docker_stack.py smoke   # chạy smoke trong container api
    python scripts/docker_stack.py ps
    python scripts/docker_stack.py logs
    python scripts/docker_stack.py down
    python scripts/docker_stack.py reset   # down -v rồi up lại từ trắng
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

# Console Windows mặc định cp1252, không in được đường dẫn có dấu (ví dụ 'Ằ').
# Không ép UTF-8 thì script chết ở đúng dòng print, không phải ở Docker.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "infra" / "docker" / "compose.yml"

# Tên project phải là ASCII: Docker dùng nó làm tiền tố container và network.
PROJECT = "nhipquan"

# Cổng chỉ mở ra host cho hai dịch vụ người dùng cần thấy.
HEALTH_URL = "http://localhost:8000/health"
WEB_URL = "http://localhost:3000"


def _env() -> dict[str, str]:
    env = dict(os.environ)
    # Builder classic: không mở gRPC session nên không có header non-ASCII.
    env["DOCKER_BUILDKIT"] = "0"
    env["COMPOSE_DOCKER_CLI_BUILD"] = "0"
    env["COMPOSE_PROJECT_NAME"] = PROJECT
    return env


def _compose(*args: str) -> int:
    cmd = ["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE), *args]
    print("$", " ".join(cmd), flush=True)
    return subprocess.call(cmd, env=_env())


def _cho_healthy(timeout_s: int = 180) -> bool:
    """Chờ api trả /health và web trả 200. Trả False nếu quá hạn."""
    import urllib.error
    import urllib.request

    han = time.time() + timeout_s
    api_ok = web_ok = False
    while time.time() < han:
        for url, ten in ((HEALTH_URL, "api"), (WEB_URL, "web")):
            if (ten == "api" and api_ok) or (ten == "web" and web_ok):
                continue
            try:
                with urllib.request.urlopen(url, timeout=5) as r:  # noqa: S310
                    if r.status == 200:
                        print(f"  {ten}: HTTP 200")
                        if ten == "api":
                            api_ok = True
                        else:
                            web_ok = True
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
        if api_ok and web_ok:
            return True
        time.sleep(3)
    print(f"  quá hạn {timeout_s}s — api_ok={api_ok} web_ok={web_ok}")
    return False


def up() -> int:
    if rc := _compose("up", "-d", "--build"):
        return rc
    print("\n== chờ dịch vụ sẵn sàng ==")
    if not _cho_healthy():
        _compose("ps")
        return 1
    return _compose("ps")


def main() -> int:
    lenh = sys.argv[1] if len(sys.argv) > 1 else "up"
    if lenh == "up":
        return up()
    if lenh == "down":
        return _compose("down")
    if lenh == "ps":
        return _compose("ps")
    if lenh == "logs":
        return _compose("logs", "-f", "--tail=100")
    if lenh == "smoke":
        return _compose("exec", "-T", "api", "python", "/app/scripts/smoke_docker.py")
    if lenh == "reset":
        _compose("down", "-v")
        return up()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
