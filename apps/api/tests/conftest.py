from __future__ import annotations

import os
from pathlib import Path

import pytest
from ca_api.persist import reset_init_flag


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_database_url = os.environ.get("NHIPQUAN_TEST_DATABASE_URL")
    if test_database_url:
        monkeypatch.setenv("DATABASE_URL", test_database_url)
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("NHIPQUAN_DB", str(tmp_path / "quan.db"))
    monkeypatch.setenv("NHIPQUAN_SUA", str(tmp_path / "sua.jsonl"))
    monkeypatch.setenv("NHIPQUAN_CAMNANG", str(tmp_path / "cam_nang.json"))
    monkeypatch.setenv("NHIPQUAN_PBKDF2_VONG", "1000")
    reset_init_flag()


@pytest.fixture
def _du_nhan_vien_xep_lich() -> None:
    """Tạo đủ 12 NV cho solver có nghiệm (pool users thay seed).

    Sau khi build_lich_input lấy pool ngoài làm TOÀN BỘ (2026-09-07), DB test
    chỉ có 3-4 user mặc định → 21 ca cần tới 49 lượt là INFEASIBLE. Mọi test
    đụng solver (copilot SCHEDULE_SOLVE, inbox wiring, worker đề xuất) dùng
    fixture này để được nghiệm OPTIMAL như production có đủ người.
    """
    from ca_api.persist import init_db, register

    init_db()
    for i in range(9):
        register(f"nv_xep{i}", f"matkhautot{i}9x", f"NV Xếp {i}")
