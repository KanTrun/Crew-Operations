"""Validate the professional synthetic fixture without touching the application store."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "professional"


def load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main() -> int:
    manifest = load("manifest.json")
    base = load("base.json")
    pos = load("pos.json")
    operations = load("operations.json")
    channels = load("channels.json")

    assert manifest["synthetic"] is True
    assert manifest["nguon"] == "mo_phong_fixture"
    staff_ids = {row["id"] for row in base["staff"]}
    shift_ids = {row["id"] for row in base["shifts"]}
    menu_ids = {row["id"] for row in pos["menu_items"]}
    item_ids = {row["id"] for row in pos["inventory_items"]}
    thread_ids = {row["id"] for row in channels["page_threads"]}

    assert len(staff_ids) == 10
    assert len(shift_ids) == 21
    assert {row["thu"] for row in base["shifts"]} == set(range(1, 8))
    assert all(row["staff_id"] in staff_ids for row in base["assignments"])
    assert all(row["shift_id"] in shift_ids for row in base["assignments"])
    assert all(row["staff_id"] in staff_ids for row in pos["orders"])
    assert all(line["mon_id"] in menu_ids for order in pos["orders"] for line in order["dong"])
    assert all(row["item_id"] in item_ids for row in pos["inventory_snapshots"])
    assert all(row["shift_id"] in shift_ids for row in operations["checklist_runs"])
    assert all(row["shift_id"] in shift_ids for row in operations["pending_work"])
    assert all(row["staff_id"] in staff_ids for row in operations["inbox_constraints"])
    assert all(row["thread_id"] in thread_ids for row in channels["page_drafts"])
    assert {row["trang_thai"] for row in pos["orders"]} >= {"cho_pha", "dang_pha", "xong", "huy"}
    assert {row["status"] for row in operations["checklist_runs"]} == {"in_progress", "completed", "blocked"}
    assert {row["status"] for row in channels["page_drafts"]} == {"nhap", "cho_duyet", "da_dang_mock"}
    assert all(
        section["metadata"] == {"synthetic": True, "nguon": "mo_phong_fixture"}
        for section in (base, pos, operations, channels)
    )

    print("professional fixture: OK")
    print(f"staff={len(base['staff'])} shifts={len(base['shifts'])} orders={len(pos['orders'])} runs={len(operations['checklist_runs'])}")
    print(f"bindings={len(channels['channel_bindings'])} threads={len(channels['page_threads'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
