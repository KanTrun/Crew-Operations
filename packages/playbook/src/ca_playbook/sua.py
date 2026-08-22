"""Bảng ghi nhận lần sửa — bước 1 vòng đời luật (Sprint 3)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
STORE = ROOT / "data" / "out" / "so_lan_sua.jsonl"


def _store(path: Path | None = None) -> Path:
    if path is not None:
        return path
    override = os.environ.get("NHIPQUAN_SUA")
    return Path(override) if override else STORE


def record_sua(
    *,
    loai: str,
    truoc: Any,
    sau: Any,
    ai: str,
    now_iso: str,
    path: Path | None = None,
    synthetic: bool = False,
) -> dict[str, Any]:
    row = {
        "loai": loai,
        "truoc": truoc,
        "sau": sau,
        "ai": ai,
        "at": now_iso,
    }
    if synthetic:
        row["synthetic"] = True
    p = _store(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def list_sua(path: Path | None = None, *, include_synthetic: bool = True) -> list[dict[str, Any]]:
    p = _store(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if not include_synthetic and row.get("synthetic"):
                continue
            out.append(row)
    return out
