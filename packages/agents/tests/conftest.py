"""Shared deterministic defaults for the agents test suite."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _default_to_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent a developer's live .env from changing test behavior."""
    monkeypatch.setenv("CA_AGENT_MODE", "replay")