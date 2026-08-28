"""Compliance policies — deterministic, injectable parameters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_tham_so(path: Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[6]
    cfg = path or (root / "config" / "tham-so-lao-dong.yaml")
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("tham-so-lao-dong.yaml must be a mapping")
    return data


def tran_gio_tuan(tham_so: dict[str, Any]) -> int:
    return int(tham_so["tran_gio_tuan"])


def khoang_nghi_toi_thieu_gio(tham_so: dict[str, Any]) -> int:
    return int(tham_so["khoang_nghi_toi_thieu_gio"])
