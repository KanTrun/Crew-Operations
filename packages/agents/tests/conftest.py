"""Shared deterministic defaults for the agents test suite."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _default_to_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent a developer's live .env from changing test behavior."""
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    monkeypatch.setenv("NHIPQUAN_AUTO_RESERVATION", "1")
    monkeypatch.setenv("CA_SOLVER_TIME_LIMIT_S", "4.0")

    import ca_agents.ag_concierge as concierge_mod

    monkeypatch.setattr(
        concierge_mod,
        "_RESERVATION_BACKEND",
        {
            "book": lambda **kwargs: {
                "id": "res_test_mock",
                "table_ids": ["B105"],
                "status": "confirmed",
                "booking_time": kwargs.get("booking_time"),
                "party_size": kwargs.get("party_size"),
                "dialog_step": "CONFIRMED",
            },
            "anti_abuse": lambda **kwargs: (True, None),
            "cancel": lambda *args: True,
            "notify": lambda *args: None,
            "is_enabled": lambda: True,
        },
    )