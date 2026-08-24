from __future__ import annotations

import os

# CI and local pytest must not pick CA_AGENT_MODE=live from a developer .env.
os.environ["CA_AGENT_MODE"] = "replay"
