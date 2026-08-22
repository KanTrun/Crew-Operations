"""Persistent quán store — SQLite file, survives process restart."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]

_INITIALIZED = False

USERS = (
    ("lan", "nhipquan", "quan_ly", "nv_01", "Lan — quản lý"),
    ("minh", "nhipquan", "nhan_vien", "nv_03", "Minh — ca sáng"),
    ("hung", "nhipquan", "chu_quan", "nv_02", "Hùng — chủ quán"),
)


def db_path() -> Path:
    override = os.environ.get("NHIPQUAN_DB")
    return Path(override) if override else ROOT / "data" / "quan.db"


def _conn() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(path, timeout=30)
    cx.execute("PRAGMA journal_mode=WAL")
    return cx


def init_db() -> None:
    global _INITIALIZED
    if _INITIALIZED and db_path().exists():
        return
    with _conn() as cx:
        cx.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_sha TEXT NOT NULL,
                role TEXT NOT NULL,
                nv_id TEXT NOT NULL,
                display_name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                nv_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS kv (
                k TEXT PRIMARY KEY,
                v TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                at TEXT NOT NULL,
                ai TEXT NOT NULL,
                hanh TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            """
        )
        for u, pw, role, nv, name in USERS:
            digest = hashlib.sha256(pw.encode()).hexdigest()
            cx.execute(
                """
                INSERT OR IGNORE INTO users(username, password_sha, role, nv_id, display_name)
                VALUES (?,?,?,?,?)
                """,
                (u, digest, role, nv, name),
            )
    _INITIALIZED = True


def reset_init_flag() -> None:
    """Tests may swap NHIPQUAN_DB between cases."""
    global _INITIALIZED
    _INITIALIZED = False


def login(username: str, password: str) -> dict[str, str] | None:
    init_db()
    digest = hashlib.sha256(password.encode()).hexdigest()
    with _conn() as cx:
        row = cx.execute(
            """
            SELECT username, role, nv_id, display_name
            FROM users WHERE username=? AND password_sha=?
            """,
            (username.strip().lower(), digest),
        ).fetchone()
        if not row:
            return None
        token = uuid.uuid4().hex
        cx.execute(
            "INSERT INTO sessions(token, username, role, nv_id) VALUES (?,?,?,?)",
            (token, row[0], row[1], row[2]),
        )
        return {
            "token": token,
            "role": row[1],
            "nv_id": row[2],
            "display_name": row[3],
        }


def session(authorization: str | None) -> dict[str, str] | None:
    init_db()
    if not authorization:
        return None
    raw = authorization.removeprefix("Bearer ").strip()
    with _conn() as cx:
        row = cx.execute(
            "SELECT username, role, nv_id FROM sessions WHERE token=?", (raw,)
        ).fetchone()
        if not row:
            return None
        return {"username": row[0], "role": row[1], "nv_id": row[2]}


def kv_get(key: str, default: Any) -> Any:
    init_db()
    with _conn() as cx:
        row = cx.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
    if not row:
        return default
    return json.loads(row[0])


def kv_set(key: str, value: Any) -> None:
    init_db()
    with _conn() as cx:
        cx.execute(
            "INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (key, json.dumps(value, ensure_ascii=False)),
        )


def kv_mutate(key: str, fn: Callable[[Any], Any], default: Any) -> Any:
    """Atomic read-modify-write under BEGIN IMMEDIATE."""
    init_db()
    with _conn() as cx:
        cx.isolation_level = None
        cx.execute("BEGIN IMMEDIATE")
        try:
            row = cx.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
            cur = json.loads(row[0]) if row else default
            if isinstance(default, dict) and isinstance(cur, dict):
                cur = dict(cur)
            elif isinstance(default, list) and isinstance(cur, list):
                cur = list(cur)
            new = fn(cur)
            cx.execute(
                "INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (key, json.dumps(new, ensure_ascii=False)),
            )
            cx.execute("COMMIT")
            return new
        except Exception:
            cx.execute("ROLLBACK")
            raise


def audit_add(at: str, ai: str, hanh: str, payload: dict[str, Any]) -> None:
    init_db()
    with _conn() as cx:
        cx.execute(
            "INSERT INTO audit(at, ai, hanh, payload) VALUES (?,?,?,?)",
            (at, ai, hanh, json.dumps(payload, ensure_ascii=False)),
        )


def audit_list() -> list[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        rows = cx.execute(
            "SELECT at, ai, hanh, payload FROM audit ORDER BY id"
        ).fetchall()
    out = []
    for at, ai, hanh, payload in rows:
        item = json.loads(payload)
        item.update({"at": at, "ai": ai, "hanh": hanh})
        out.append(item)
    return out
