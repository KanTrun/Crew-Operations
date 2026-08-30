"""Load the professional synthetic fixture into the local SQLite runtime store."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "fixtures" / "professional"
SEED = ROOT / "data" / "seed" / "sample.json"
SOURCE = "mo_phong_fixture"

for path in (
    ROOT / "apps" / "api" / "src",
    ROOT / "packages" / "playbook" / "src",
    ROOT / "packages" / "gates" / "src",
    ROOT / "packages" / "opsengine" / "src",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ca_api.persist import _conn, hash_password, init_db, kv_get, kv_set  # noqa: E402
from ca_ops import dump_run, start_phieu  # noqa: E402

STAFF_TO_DB = {"fx_nv_lan": "nv_01", "fx_nv_hung": "nv_02", "fx_nv_minh": "nv_03"}
NEW_USERS = {
    "fx_nv_an": ("an", "An Le"),
    "fx_nv_bao": ("bao", "Bao Hoang"),
    "fx_nv_chi": ("chi", "Chi Vu"),
    "fx_nv_dung": ("dung", "Dung Dang"),
    "fx_nv_thao": ("thao", "Thao Duong"),
    "fx_nv_quan": ("quan", "Quan Luong"),
    "fx_nv_yen": ("yen", "Yen Kieu"),
}


def read(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def db_staff_id(fixture_id: str) -> str:
    return STAFF_TO_DB.get(fixture_id, fixture_id)


def mark(row: dict[str, Any]) -> dict[str, Any]:
    return {**row, "synthetic": True, "nguon": SOURCE}


def add_users(base: dict[str, Any]) -> int:
    init_db()
    inserted = 0
    with _conn() as cx:
        for fixture_id, (username, display_name) in NEW_USERS.items():
            before = cx.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
            cx.execute(
                """
                INSERT INTO users(username, password_sha, role, nv_id, display_name)
                VALUES (?, ?, 'nhan_vien', ?, ?)
                ON CONFLICT(username) DO UPDATE SET nv_id=excluded.nv_id,
                    display_name=excluded.display_name
                """,
                (username, hash_password("nhipquan"), fixture_id, display_name),
            )
            inserted += int(before is None)
    return inserted


def upsert_pos(pos: dict[str, Any]) -> tuple[int, int]:
    from ca_api.persist import don_insert, menu_upsert

    menu_count = 0
    order_count = 0
    init_db()
    with _conn() as cx:
        existing_orders = {row[0] for row in cx.execute("SELECT id FROM don_quay").fetchall()}
    for raw in pos["menu_items"]:
        menu_upsert(mark(raw))
        menu_count += 1
    for raw in pos["orders"]:
        if raw["id"] in existing_orders:
            continue
        order = mark(raw)
        order["nv_id"] = db_staff_id(order["staff_id"])
        order.pop("staff_id", None)
        don_insert(order)
        order_count += 1
    return menu_count, order_count


def runtime_operations(
    base: dict[str, Any], pos: dict[str, Any], operations: dict[str, Any], channels: dict[str, Any]
) -> None:
    assignments = {row["shift_id"]: [db_staff_id(row["staff_id"])] for row in base["assignments"]}
    kv_set("phan_cong", assignments)
    current_attendance = list(kv_get("diem_danh", []))
    for staff_id in ("nv_01", "nv_02", "nv_03", *NEW_USERS):
        resolved = db_staff_id(staff_id)
        if resolved not in current_attendance:
            current_attendance.append(resolved)
    kv_set("diem_danh", current_attendance)
    kv_set(
        "treo",
        [
            mark({**row, "nguoi_nhan": db_staff_id(row["nguoi_nhan"])})
            for row in operations["pending_work"]
        ],
    )
    inbox = []
    for row in operations["inbox_constraints"]:
        item = mark(row)
        item["staff_id"] = db_staff_id(row["staff_id"])
        item["nv_id"] = item["staff_id"]
        inbox.append(item)
    kv_set("inbox_rang_buoc", inbox)
    kv_set(
        "inbox_msg",
        [
            {key: row[key] for key in ("id", "tom_tat", "agent", "trang_thai", "do_tin_cay")}
            for row in inbox
        ],
    )
    sample = json.loads(SEED.read_text(encoding="utf-8")) if SEED.exists() else {}
    kv_set("waste_notes", [mark(row) for row in sample.get("hao_phi", [])])
    kv_set("kiem_ke", [mark(row) for row in pos["inventory_snapshots"]])
    kv_set("tieu_thu", [mark(row) for row in pos["consumption_links"]])
    kv_set(
        "page_quan",
        {
            "mode": "fixture",
            "threads": [mark(row) for row in channels["page_threads"]],
            "drafts": [
                mark({**row, "created_by": db_staff_id(row["created_by"])})
                for row in channels["page_drafts"]
            ],
        },
    )
    run = start_phieu(
        run_id="fx_run_open_001",
        mau="mo_quan",
        nv_id="nv_01",
        ca_id="fx_ca_01",
        now_ms=1_756_456_100_000,
        diem_danh=True,
    )
    run.treo = ["Bo sung sua tuoi truoc ca chieu"]
    bag = kv_get("phieu", {})
    bag[run.id] = dump_run(run)
    kv_set("phieu", bag)
    kv_set(
        "professional_fixture",
        {
            "source": SOURCE,
            "manifest": read("manifest.json"),
            "base": base,
            "pos": pos,
            "operations": operations,
            "channels": channels,
            "staff_to_db": STAFF_TO_DB,
        },
    )

    from ca_api.persist import kenh_bind_set

    for row in channels["channel_bindings"]:
        kenh_bind_set(row["channel"], row["channel_user_id"], db_staff_id(row["staff_id"]))


def wipe_db() -> None:
    from ca_api.persist import db_path, reset_init_flag

    p = db_path()
    if p.exists():
        p.unlink()
    for extra in (p.with_name(p.name + "-wal"), p.with_name(p.name + "-shm")):
        if extra.exists():
            extra.unlink()
    reset_init_flag()


def main() -> int:
    if "--reset" in sys.argv:
        wipe_db()
        print("database wiped cleanly.")
    base = read("base.json")
    pos = read("pos.json")
    operations = read("operations.json")
    channels = read("channels.json")
    inserted_users = add_users(base)
    menus, orders = upsert_pos(pos)
    runtime_operations(base, pos, operations, channels)
    print(f"professional fixture loaded: source={SOURCE}")
    print(f"users_added={inserted_users} menu_upserted={menus} orders_added={orders}")
    print("runtime keys: phan_cong, diem_danh, treo, inbox, waste, kiem_ke, tieu_thu, page_quan")
    print("idempotent: rerun keeps fixture IDs stable and does not duplicate orders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
