#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seed_staff_complete.py
-----------------------
Seed script cho database nhan vien + lich xep ca quan ca phe (quan_01).

- Doc du lieu tu staff_database_complete.json (cung thu muc, hoac truyen
  duong dan bang --json).
- Tao SQLite:
    * bang `users`            (tai khoan dang nhap, mat khau mac dinh)
    * KV store `kv_store`     (key/value JSON, dung cho:
          lich_tuan, phan_cong, ngan_sach_cong_bang,
          de_xuat_doi_ca, viec_treo, kenh_bind)
- Idempotent: chay lai nhieu lan KHONG tao du lieu trung; cac namespace
    dang danh sach cung duoc dong bo de xoa key khong con trong dataset moi.
- Mat khau mac dinh cho moi tai khoan: "nhipquan" (duoc hash bang sha256 +
  salt co dinh moi user = username, chi mang tinh demo - KHONG dung cho
  production thuc te).
- Ho tro --reset de xoa sach du lieu cu truoc khi seed lai.

Cach dung:
    python3 seed_staff_complete.py
    python3 seed_staff_complete.py --json duong/dan/khac.json --db khac.sqlite3
    python3 seed_staff_complete.py --reset
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

DEFAULT_PASSWORD = "nhipquan"


def hash_password(username: str, password: str) -> str:
    """Hash demo (KHONG dung cho production): sha256(username + ':' + password)."""
    return hashlib.sha256(f"{username}:{password}".encode("utf-8")).hexdigest()


def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id                  TEXT PRIMARY KEY,
            ten                 TEXT NOT NULL,
            username            TEXT NOT NULL UNIQUE,
            display_name        TEXT,
            role                TEXT NOT NULL,
            ky_nang             TEXT NOT NULL,      -- JSON array
            la_sinh_vien        INTEGER NOT NULL DEFAULT 0,
            so_dien_thoai_hash  TEXT,
            store_id            TEXT NOT NULL,
            active              INTEGER NOT NULL DEFAULT 1,
            contract_type       TEXT NOT NULL,
            max_hours_tuan      REAL NOT NULL,
            password_hash       TEXT NOT NULL,
            created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at          TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS kv_store (
            namespace   TEXT NOT NULL,
            key         TEXT NOT NULL,
            value_json  TEXT NOT NULL,
            updated_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (namespace, key)
        );
        """
    )
    conn.commit()


def reset_data(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DELETE FROM users;
        DELETE FROM kv_store;
        """
    )
    conn.commit()
    print("[reset] Da xoa sach du lieu users + kv_store.")


def validate_data(data: dict) -> None:
    """Reject malformed or internally inconsistent replacement datasets."""
    required = {
        "staff", "shifts", "assignments", "availability", "leave_requests",
        "swap_requests", "fairness_ledger", "handover_tasks", "channel_bindings",
        "weekly_schedule",
    }
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Thieu section: {', '.join(sorted(missing))}")

    staff = {person["id"]: person for person in data["staff"]}
    shifts = {shift["id"]: shift for shift in data["shifts"]}
    if len(staff) != len(data["staff"]):
        raise ValueError("Trung staff id")
    if len(shifts) != len(data["shifts"]):
        raise ValueError("Trung shift id")

    week = data["weekly_schedule"]["tuan_iso"]
    year, week_number = (int(part) for part in week.split("-W"))
    monday = date.fromisocalendar(year, week_number, 1)
    for shift in shifts.values():
        expected_date = monday + timedelta(days=shift["thu"] - 1)
        if shift["ngay"] != expected_date.isoformat():
            raise ValueError(
                f"{shift['id']} co ngay {shift['ngay']}, expected {expected_date.isoformat()}"
            )
        assigned = data["assignments"].get(shift["id"], [])
        if len(assigned) < shift["so_nguoi_toi_thieu"]:
            raise ValueError(f"{shift['id']} thieu nguoi")
        for staff_id in assigned:
            person = staff.get(staff_id)
            if person is None:
                raise ValueError(f"{shift['id']} tham chieu staff khong ton tai: {staff_id}")
            if shift["vi_tri"] not in person["ky_nang"]:
                raise ValueError(f"{staff_id} thieu ky nang {shift['vi_tri']} tai {shift['id']}")

    approved_leave = {
        (leave["staff_id"], leave["date"])
        for leave in data["leave_requests"]
        if leave["status"] == "approved"
    }
    for shift_id, assigned in data["assignments"].items():
        if shift_id not in shifts:
            raise ValueError(f"Assignment tham chieu shift khong ton tai: {shift_id}")
        for staff_id in assigned:
            if (staff_id, shifts[shift_id]["ngay"]) in approved_leave:
                raise ValueError(f"{staff_id} bi trung nghi phep tai {shift_id}")


def sync_namespace(conn: sqlite3.Connection, namespace: str, records: dict[str, object]) -> None:
    """Upsert current records and remove keys absent from the replacement dataset."""
    if records:
        placeholders = ",".join("?" for _ in records)
        conn.execute(
            f"DELETE FROM kv_store WHERE namespace = ? AND key NOT IN ({placeholders})",
            (namespace, *records),
        )
    else:
        conn.execute("DELETE FROM kv_store WHERE namespace = ?", (namespace,))
    for key, value in records.items():
        seed_kv(conn, namespace, key, value)


def seed_runtime(data: dict, db_path: str) -> None:
    """Replace the cafe staff/schedule slice in the application's runtime DB."""
    repo_root = Path(__file__).resolve().parents[1]
    api_src = repo_root / "apps" / "api" / "src"
    sys.path.insert(0, str(api_src))
    from ca_api.persist import hash_password
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    staff_ids = {person["id"] for person in data["staff"]}
    old_staff_ids = {
        row[0]
        for row in conn.execute(
            "SELECT nv_id FROM users WHERE store_id = ? AND role != 'ai_assistant'",
            (data["metadata"]["store_id"],),
        )
    }
    conn.execute(
        "DELETE FROM sessions WHERE nv_id IN ({})".format(",".join("?" for _ in old_staff_ids)),
        tuple(old_staff_ids),
    ) if old_staff_ids else None
    conn.execute(
        "DELETE FROM users WHERE store_id = ? AND role != 'ai_assistant'",
        (data["metadata"]["store_id"],),
    )
    for person in data["staff"]:
        conn.execute(
            """
            INSERT INTO users
                (username, password_sha, role, nv_id, display_name, email, store_id, status)
            VALUES (?, ?, ?, ?, ?, '', ?, 'active')
            """,
            (
                person["username"],
                hash_password(DEFAULT_PASSWORD),
                person["role"],
                person["id"],
                person.get("display_name") or person["ten"],
                person["store_id"],
            ),
        )

    store_id = data["metadata"]["store_id"]
    seed_kv_runtime(conn, "staff_database_complete", data)
    seed_kv_runtime(conn, "nhan_vien", data["staff"])
    seed_kv_runtime(conn, "ca_mau_21", data["shifts"])
    seed_kv_runtime(conn, "phan_cong", data["assignments"])
    seed_kv_runtime(conn, "lich_tuan", data["weekly_schedule"])
    seed_kv_runtime(conn, "availability", data["availability"])
    seed_kv_runtime(conn, "xin_nghi", data["leave_requests"])
    seed_kv_runtime(conn, "de_xuat_doi_ca", data["swap_requests"])
    seed_kv_runtime(conn, "ngan_sach_cong_bang", data["fairness_ledger"])
    seed_kv_runtime(conn, "viec_treo", data["handover_tasks"])
    seed_kv_runtime(conn, "kenh_bind", data["channel_bindings"])
    conn.commit()
    conn.close()
    print(f"[runtime] Da thay staff cu bang {len(staff_ids)} staff moi trong {db_path}.")


def seed_kv_runtime(conn: sqlite3.Connection, key: str, value: object) -> None:
    conn.execute(
        "INSERT INTO kv(k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (key, json.dumps(value, ensure_ascii=False)),
    )


def seed_users(conn: sqlite3.Connection, staff: list) -> int:
    cur = conn.cursor()
    n = 0
    for s in staff:
        cur.execute(
            """
            INSERT INTO users (id, ten, username, display_name, role, ky_nang,
                                la_sinh_vien, so_dien_thoai_hash, store_id,
                                active, contract_type, max_hours_tuan,
                                password_hash, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                ten=excluded.ten,
                username=excluded.username,
                display_name=excluded.display_name,
                role=excluded.role,
                ky_nang=excluded.ky_nang,
                la_sinh_vien=excluded.la_sinh_vien,
                so_dien_thoai_hash=excluded.so_dien_thoai_hash,
                store_id=excluded.store_id,
                active=excluded.active,
                contract_type=excluded.contract_type,
                max_hours_tuan=excluded.max_hours_tuan,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                s["id"], s["ten"], s["username"], s.get("display_name"),
                s["role"], json.dumps(s["ky_nang"], ensure_ascii=False),
                1 if s["la_sinh_vien"] else 0, s.get("so_dien_thoai_hash"),
                s["store_id"], 1 if s["active"] else 0, s["contract_type"],
                s["max_hours_tuan"], hash_password(s["username"], DEFAULT_PASSWORD),
            ),
        )
        n += 1
    conn.commit()
    return n


def seed_kv(conn: sqlite3.Connection, namespace: str, key: str, value) -> None:
    conn.execute(
        """
        INSERT INTO kv_store (namespace, key, value_json, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(namespace, key) DO UPDATE SET
            value_json=excluded.value_json,
            updated_at=CURRENT_TIMESTAMP
        """,
        (namespace, key, json.dumps(value, ensure_ascii=False)),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed staff + schedule DB cho quan_01")
    default_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "staff_database_complete.json")
    parser.add_argument("--json", default=default_json, help="Duong dan staff_database_complete.json")
    parser.add_argument("--db", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "quan_01.sqlite3"),
                         help="Duong dan file SQLite dich")
    parser.add_argument("--reset", action="store_true", help="Xoa sach du lieu cu truoc khi seed")
    parser.add_argument("--runtime", action="store_true", help="Nap vao DB runtime cua ung dung")
    args = parser.parse_args()

    if not os.path.exists(args.json):
        print(f"LOI: khong tim thay {args.json}", file=sys.stderr)
        return 1

    with open(args.json, "r", encoding="utf-8") as f:
        data = json.load(f)
    try:
        validate_data(data)
    except (KeyError, TypeError, ValueError) as exc:
        print(f"LOI: du lieu khong hop le: {exc}", file=sys.stderr)
        return 1

    if args.runtime:
        seed_runtime(data, args.db)
        return 0

    conn = get_conn(args.db)
    create_schema(conn)
    if args.reset:
        reset_data(conn)

    n_users = seed_users(conn, data["staff"])
    print(f"[users] Da seed {n_users} tai khoan (mat khau mac dinh: '{DEFAULT_PASSWORD}').")

    tuan_iso = data["weekly_schedule"]["tuan_iso"]

    seed_kv(conn, "lich_tuan", tuan_iso, {
        "shifts": data["shifts"],
        "weekly_schedule": data["weekly_schedule"],
        "availability": data["availability"],
    })
    seed_kv(conn, "phan_cong", tuan_iso, data["assignments"])
    seed_kv(conn, "ngan_sach_cong_bang", "global", data["fairness_ledger"])
    sync_namespace(conn, "de_xuat_doi_ca", {sw["id"]: sw for sw in data["swap_requests"]})
    sync_namespace(conn, "viec_treo", {h["id"]: h for h in data["handover_tasks"]})
    sync_namespace(conn, "kenh_bind", {c["id"]: c for c in data["channel_bindings"]})
    sync_namespace(conn, "xin_nghi", {lv["id"]: lv for lv in data["leave_requests"]})
    conn.commit()

    print("[kv_store] Da seed: lich_tuan, phan_cong, ngan_sach_cong_bang, "
          f"de_xuat_doi_ca ({len(data['swap_requests'])}), "
          f"viec_treo ({len(data['handover_tasks'])}), "
          f"kenh_bind ({len(data['channel_bindings'])}), "
          f"xin_nghi ({len(data['leave_requests'])}).")

    cur = conn.execute("SELECT COUNT(*) FROM users")
    print(f"[verify] Tong so users trong DB: {cur.fetchone()[0]}")
    cur = conn.execute("SELECT COUNT(*) FROM kv_store")
    print(f"[verify] Tong so ban ghi kv_store: {cur.fetchone()[0]}")

    conn.close()
    print(f"\nHoan tat. DB: {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
