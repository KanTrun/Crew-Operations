from __future__ import annotations

from pathlib import Path

import pytest
from ca_api.persist import reset_init_flag


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NHIPQUAN_DB", str(tmp_path / "quan.db"))
    monkeypatch.setenv("NHIPQUAN_SUA", str(tmp_path / "sua.jsonl"))
    monkeypatch.setenv("NHIPQUAN_CAMNANG", str(tmp_path / "cam_nang.json"))
    monkeypatch.setenv("NHIPQUAN_PBKDF2_VONG", "1000")
    reset_init_flag()
