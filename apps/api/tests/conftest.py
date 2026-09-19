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
    # Test unit chủ động dùng bộ demo/fixture; runtime thật mặc định không seed.
    monkeypatch.setenv("NHIPQUAN_SEED_DEMO", "1")
    monkeypatch.setenv("NHIPQUAN_INBOX_SEED_FIXTURE", "1")
    # `ag_mail._log_mail_replay` mặc định ghi vào ĐƯỜNG DẪN TƯƠNG ĐỐI
    # `data/out/mail_log.jsonl` khi biến này chưa được đặt. File đó ĐÃ ĐƯỢC
    # TRACK trong git, nên mỗi lần chạy suite sẽ nối thêm bản ghi replay và làm
    # bẩn working tree (test_copilot_send_mail_proposal_and_execute gọi mail
    # adapter thật, không patch). Không test nào trong apps/api đọc file này.
    monkeypatch.setenv("NHIPQUAN_MAIL_LOG", str(tmp_path / "mail_log.jsonl"))
    monkeypatch.setenv("NHIPQUAN_PBKDF2_VONG", "1000")
    monkeypatch.setenv("CA_SOLVER_TIME_LIMIT_S", "4.0")
    monkeypatch.delenv("NHIPQUAN_LOI_GIAI_SEED", raising=False)
    # _run_solver ghi output ra data/out/lich_tuan.json — file lịch THẬT của
    # quán. Test INFEASIBLE (vd test_infeasible_solver_returns_specific_conflicts)
    # ghi đè phan_cong rỗng + status INFEASIBLE vào file này, làm UI mất lịch.
    monkeypatch.setenv("NHIPQUAN_LICH_TUAN_OUT", str(tmp_path / "lich_tuan.json"))
    reset_init_flag()


@pytest.fixture
def _du_nhan_vien_xep_lich() -> None:
    """Tạo đủ 12 NV cho solver có nghiệm (pool users thay seed).

    Sau khi build_lich_input lấy pool ngoài làm TOÀN BỘ (2026-09-07), DB test
    chỉ có 3-4 user mặc định → 70 role-slot cần tới 91 lượt là INFEASIBLE. Mỗi
    ngày có 10 role-slot (3 sáng + 3 chiều + 4 tối) và C03/C04 chặn 1 người
    2 khung trùng → cần ≥ 10 người/ngày, thêm biên độ cho TKB/nghỉ phép.
    Mọi test đụng solver (copilot SCHEDULE_SOLVE, inbox wiring, worker đề
    xuất) dùng fixture này để được nghiệm OPTIMAL như production có đủ người.
    """
    from ca_api.persist import init_db, register

    init_db()
    for i in range(13):
        register(f"nv_xep{i}", f"matkhautot{i}9x", f"NV Xếp {i}")


@pytest.fixture
def _xac_nhan_kha_dung_tuan() -> None:
    """Seed explicit confirmed availability for tests of authoritative scheduling."""
    from ca_api.persist import availability_confirmation_upsert, list_users

    availability = {day: ["Sáng", "Chiều", "Tối"] for day in ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]}
    for user in list_users():
        if user.get("role") != "nhan_vien":
            continue
        for week in ("2026-W01", "2026-W36", "2026-W44"):
            availability_confirmation_upsert(
                item_id=f"test-av-{user['nv_id']}-{week}", store_id="quan_01", nv_id=str(user["nv_id"]),
                tuan_iso=week, availability=availability, status="da_xac_nhan", source="test",
            )
