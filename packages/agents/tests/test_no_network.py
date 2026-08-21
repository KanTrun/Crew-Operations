"""Gate 10: tests must not open live network when CA_AGENT_MODE=replay."""

from __future__ import annotations

import os
import socket

import pytest


@pytest.fixture(autouse=True)
def _block_network_in_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.environ.get("CA_AGENT_MODE", "replay") != "replay":
        return

    def _blocked(*_a: object, **_k: object) -> None:
        raise RuntimeError("live network blocked in CA_AGENT_MODE=replay")

    monkeypatch.setattr(socket.socket, "connect", _blocked)


def test_replay_mode_default() -> None:
    assert os.environ.get("CA_AGENT_MODE", "replay") == "replay"
