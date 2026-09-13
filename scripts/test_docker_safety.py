from __future__ import annotations

import os
import socket

from smoke_docker import call


def main() -> None:
    assert os.environ.get("CA_AGENT_MODE") == "replay"
    assert os.environ.get("NHIPQUAN_PAGE_MODE") == "disconnected"
    assert os.environ.get("NHIPQUAN_FB_AUTO_SEND") == "0"
    try:
        connection = socket.create_connection(("1.1.1.1", 443), timeout=3)
    except OSError:
        print("Outbound probe blocked")
    else:
        connection.close()
        raise RuntimeError("Outbound isolation failed")
    base = "http://localhost:8000"
    login = call(base, "/api/v1/auth/login", body={"username": "lan", "password": "nhipquan"})
    status = call(base, "/api/v1/channels/status", token=login["token"])
    print(status)
    assert status["agent_mode"] == "replay"
    assert all(not status[channel]["connected"] for channel in ("facebook", "telegram", "zalo"))
    print("Safety gate PASS")


if __name__ == "__main__":
    main()