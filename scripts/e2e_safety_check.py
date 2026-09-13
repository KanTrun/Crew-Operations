"""Safety gate cho e2e host: xác nhận API chạy ở chế độ replay/disconnected
và mọi kênh thật (zalo/telegram/facebook) đều KHÔNG kết nối.

Chạy độc lập với pytest; dùng httpx (đã có sẵn trong Python 3.12 host).
In ra SAFETY_GATE=PASS/FAIL và exit code tương ứng.
"""

from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"


def _get(path: str, token: str | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # noqa: PERF203
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"raw": body}


def _login(username: str, password: str) -> str | None:
    payload = json.dumps({"username": username, "password": password}).encode()
    req = urllib.request.Request(
        BASE + "/api/v1/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())["token"]
    except Exception as exc:  # noqa: BLE001
        print(f"login_err={exc}")
        return None


def main() -> int:
    token = _login("lan", "nhipquan")
    if not token:
        print("SAFETY_GATE=FAIL (không login được để kiểm tra channels)")
        return 1

    status, data = _get("/api/v1/channels/status", token)
    if status != 200:
        print(f"SAFETY_GATE=FAIL (channels/status={status})")
        return 1

    agent_mode = data.get("agent_mode")
    channels = data.get("channels", data)

    def _connected(name: str) -> bool:
        node = channels.get(name) if isinstance(channels, dict) else None
        if isinstance(node, dict):
            return bool(node.get("connected"))
        return bool(node)

    problems: list[str] = []
    if agent_mode != "replay":
        problems.append(f"agent_mode={agent_mode} (mong đợi 'replay')")
    for name in ("zalo", "telegram", "facebook"):
        if _connected(name):
            problems.append(f"kênh {name} đang CONNECTED")

    print(json.dumps(data, ensure_ascii=False))
    if problems:
        print("SAFETY_GATE=FAIL — " + "; ".join(problems))
        return 1
    print("SAFETY_GATE=PASS (agent_mode=replay, zalo/telegram/facebook disconnected)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
