"""Background worker stub — jobs will land in Sprint 3+."""

from __future__ import annotations

import logging
import time

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ca_api.worker")


def main() -> None:
    log.info("worker stub started (CA_AGENT_MODE replay)")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
