"""Background worker stub — jobs will land in Sprint 3+."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from ca_agents.llm import agent_mode, load_dotenv

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ca_api.worker")


def main() -> None:
    root = Path(__file__).resolve().parents[4]
    load_dotenv(root / ".env")
    log.info("worker started (CA_AGENT_MODE=%s)", agent_mode())
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
