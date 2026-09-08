"""Seed the complete NHIP QUAN demo foundation into the active API store.

This composes the existing idempotent loaders without importing the
professional fixture's duplicate fixture-user identities. The canonical
accounts and weekly roster always come from ``seed_19_staff.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "fixtures" / "professional"

for path in (
    ROOT / "apps" / "api" / "src",
    ROOT / "packages" / "playbook" / "src",
    ROOT / "packages" / "gates" / "src",
    ROOT / "packages" / "opsengine" / "src",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def read_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def seed_menu_and_inventory() -> dict[str, int]:
    """Load recipes, menu, inventory snapshots, and consumption links."""
    from ca_api.persist import kv_set, menu_upsert

    pos = read_fixture("pos.json")
    menu_count = 0
    for item in pos["menu_items"]:
        menu_upsert(item)
        menu_count += 1

    kv_set("inventory_items", pos["inventory_items"])
    kv_set("kiem_ke", pos["inventory_snapshots"])
    kv_set("tieu_thu", pos["consumption_links"])
    return {
        "menu": menu_count,
        "inventory_items": len(pos["inventory_items"]),
        "inventory_snapshots": len(pos["inventory_snapshots"]),
        "consumption_links": len(pos["consumption_links"]),
    }


def seed_sample_orders() -> int:
    """Add fixture orders once, translating fixture staff IDs to real IDs."""
    from ca_api.persist import _conn, don_insert

    staff_ids = {
        "fx_nv_lan": "nv_01",
        "fx_nv_hung": "nv_02",
        "fx_nv_minh": "nv_03",
        "fx_nv_an": "nv_04",
        "fx_nv_bao": "nv_05",
        "fx_nv_chi": "nv_06",
        "fx_nv_dung": "nv_07",
        "fx_nv_thao": "nv_08",
        "fx_nv_quan": "nv_09",
        "fx_nv_yen": "nv_10",
    }
    orders = read_fixture("pos.json")["orders"]
    with _conn() as cx:
        existing = {str(row[0]) for row in cx.execute("SELECT id FROM don_quay").fetchall()}
    inserted = 0
    for raw in orders:
        if raw["id"] in existing:
            continue
        order = {**raw, "nv_id": staff_ids[raw["staff_id"]]}
        order.pop("staff_id", None)
        don_insert(order)
        inserted += 1
    return inserted


def main() -> int:
    import seed_19_staff
    import seed_operational

    base = seed_19_staff.read_fixture("base.json")
    seed_19_staff.seed_users()
    schedule = seed_19_staff.seed_schedule(base)
    seed_19_staff.seed_fairness(base)
    seed_19_staff.seed_doi_ca(base)
    seed_19_staff.seed_viec_treo()
    seed_19_staff.seed_attendance()
    seed_19_staff.seed_channel_bindings()
    seed_19_staff.seed_availability(base)

    ops = seed_operational.nap_tat_ca()
    catalog = seed_menu_and_inventory()
    orders = seed_sample_orders()

    print("NHIP QUAN demo foundation loaded (idempotent)")
    print(f"  users=19 shifts={schedule['shifts']} assignments={schedule['assignments']}")
    print(f"  menu={catalog['menu']} inventory_items={catalog['inventory_items']}")
    print(f"  inventory_snapshots={catalog['inventory_snapshots']} orders_added={orders}")
    print(f"  operations={sum(ops.values())} playbook/SOP sources loaded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())