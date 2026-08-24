from __future__ import annotations

import os
from pathlib import Path

import pytest
from ca_api.persist import reset_init_flag

# Developer `.env` may set CA_AGENT_MODE=live; tests stay replay (Gate 10).
os.environ["CA_AGENT_MODE"] = "replay"


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NHIPQUAN_DB", str(tmp_path / "quan.db"))
    monkeypatch.setenv("NHIPQUAN_SUA", str(tmp_path / "sua.jsonl"))
    monkeypatch.setenv("NHIPQUAN_CAMNANG", str(tmp_path / "cam_nang.json"))
    reset_init_flag()
