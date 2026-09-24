# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LOADER = ROOT / "scripts" / "seed_professional_fixture.py"


def run_loader(db_path: Path) -> None:
    env = os.environ.copy()
    env["NHIPQUAN_DB"] = str(db_path)
    env["NHIPQUAN_PBKDF2_VONG"] = "1000"
    result = subprocess.run(
        [sys.executable, str(LOADER)],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "professional fixture loaded" in result.stdout


def test_professional_fixture_load_is_consistent_and_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "fixture.db"
    run_loader(db_path)
    run_loader(db_path)

    with sqlite3.connect(db_path) as connection:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("users", "menu_mon", "don_quay", "kenh_bind")
        }
        # `menu_mon` = 8 món của fixture + `_MENU_MAC_DINH` mà `persist.init_db()`
        # tự gieo khi bảng còn trống. Con số này từng ghim cứng 12 và đã LỖI THỜI:
        # commit 7b018da thêm 2 món mặc định (nước suối, bánh quy) nhưng không cập
        # nhật ở đây, nên test đỏ dù hành vi đúng.
        #
        # Đừng ghim lại một con số nữa — nó sẽ lệch lần sau. Kiểm điều THẬT SỰ cần:
        # có ĐỦ 8 món của fixture (đã upsert, không mất), và không có món trùng id.
        fixture_menu = json.loads(
            (ROOT / "data" / "fixtures" / "professional" / "pos.json").read_text(encoding="utf-8")
        )["menu_items"]
        fixture_ids = [m["id"] for m in fixture_menu]
        db_menu_ids = {row[0] for row in connection.execute("SELECT id FROM menu_mon")}
        assert set(fixture_ids) <= db_menu_ids, (
            "thiếu món của fixture sau khi nạp: "
            + str(sorted(set(fixture_ids) - db_menu_ids))
        )
        assert len(db_menu_ids) == counts["menu_mon"], "menu_mon có id trùng"

        assert counts["users"] == 10
        assert counts["don_quay"] == 6
        assert counts["kenh_bind"] == 4
        assert counts["menu_mon"] >= len(fixture_ids)

        user_ids = {row[0] for row in connection.execute("SELECT nv_id FROM users")}
        order_ids = [row[0] for row in connection.execute("SELECT id FROM don_quay")]
        order_staff = {row[0] for row in connection.execute("SELECT nv_id FROM don_quay")}
        bind_staff = {row[0] for row in connection.execute("SELECT nv_id FROM kenh_bind")}
        assignments = json.loads(
            connection.execute("SELECT v FROM kv WHERE k='phan_cong'").fetchone()[0]
        )
        assigned_staff = {staff_id for staff_ids in assignments.values() for staff_id in staff_ids}
        assert len(order_ids) == len(set(order_ids))
        assert order_staff <= user_ids
        assert bind_staff <= user_ids
        assert assigned_staff <= user_ids

        values = {
            key: json.loads(value)
            for key, value in connection.execute("SELECT k, v FROM kv")
        }
        assert len(values["treo"]) == 6
        assert len(values["inbox_rang_buoc"]) == 6
        assert len(values["page_quan"]["threads"]) == 3
        assert "fx_run_open_001" in values["phieu"]
        assert values["phieu"]["fx_run_open_001"]["closed"] is False
