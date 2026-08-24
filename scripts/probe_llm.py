"""Probe live LLM keys from `.env`. Does not print secrets.

  python scripts/probe_llm.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "agents" / "src"))
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from ca_agents.ag_msg.extract import classify  # noqa: E402
from ca_agents.ag_tkb.extract import extract_tkb  # noqa: E402
from ca_agents.llm import (  # noqa: E402
    _call_provider,
    _ProviderError,
    agent_mode,
    load_dotenv,
    provider_status,
)


def _ping(name: str) -> str:
    try:
        text = _call_provider(
            name,
            system='Trả JSON {"pong":true}. Không thêm chữ.',
            user="ping",
            timeout_s=40.0,
            json_mode=True,
        )
    except _ProviderError as exc:
        return f"LỖI {exc}"
    snippet = text.replace("\n", " ")[:120]
    return f"OK {snippet}"


def main() -> int:
    loaded = load_dotenv(ROOT / ".env")
    print("dotenv:", "loaded" if loaded else "missing")
    os.environ["CA_AGENT_MODE"] = "live"
    print("CA_AGENT_MODE:", agent_mode())
    status = provider_status()
    print("providers:", json.dumps(status))

    failures = 0
    for name in ("groq", "gemini", "openrouter"):
        if not status[name]:
            print(f"  {name}: bỏ qua (không có key)")
            continue
        line = _ping(name)
        print(f"  {name}: {line}")
        if line.startswith("LỖI"):
            failures += 1

    print("\n== AG-TKB live tkb_01.svg ==")
    tkb = extract_tkb("tkb_01", mode="live")
    print(
        json.dumps(
            {
                "provider": tkb.get("provider"),
                "escalate": tkb.get("escalate"),
                "spans": tkb.get("spans"),
                "reason": tkb.get("reason"),
            },
            ensure_ascii=False,
        )
    )
    if tkb.get("escalate"):
        failures += 1

    print("\n== AG-MSG live (không khớp từ khoá) ==")
    msg = classify("em tới sau một lúc nhé", mode="live")
    print(json.dumps(msg.__dict__, ensure_ascii=False))
    if msg.rang_buoc.get("nguon", "").startswith("llm_fail"):
        failures += 1

    print("\nKẾT QUẢ:", "ĐỎ" if failures else "XANH")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
