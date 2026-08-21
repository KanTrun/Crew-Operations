"""AG-TKB extraction logic — replay-first, no live LLM."""

from __future__ import annotations

import json
import pathlib
from typing import Any

_GOLDEN_DIR = pathlib.Path(__file__).resolve().parents[5] / "data" / "golden" / "tkb"
_INDEX: dict[str, Any] | None = None


def _load_index() -> dict[str, Any]:
    global _INDEX
    if _INDEX is None:
        idx_path = _GOLDEN_DIR / "index.json"
        if idx_path.exists():
            data = json.loads(idx_path.read_text(encoding="utf-8"))
            _INDEX = {item["id"]: item for item in data.get("items", [])}
        else:
            _INDEX = {}
    return _INDEX


def _is_blur(name: str, meta: dict[str, Any]) -> bool:
    return "blur" in name.lower() or bool(meta.get("blur"))


def _spans_from_khoang(khoang: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"day": k["thu"], "start": k["start"], "end": k["end"]}
        for k in khoang
    ]


def extract_tkb(
    image_path_or_id: str,
    mode: str = "replay",
) -> dict[str, Any]:
    """Return structured TKB extraction result.

    Parameters
    ----------
    image_path_or_id:
        Filesystem path to image OR a golden fixture ID (e.g. ``tkb_01``).
    mode:
        ``"replay"`` reads from ``data/golden/tkb/``; other values reserved
        for live LLM (not implemented).

    Returns
    -------
    dict with keys: rows, confidence, spans, blur
    """
    if mode != "replay":
        raise NotImplementedError(f"mode={mode!r} not implemented; use replay")

    name = pathlib.Path(image_path_or_id).stem  # e.g. "tkb_01" or "tkb_01_blur"
    index = _load_index()

    # Try exact ID match first, then stem of path
    meta: dict[str, Any] = index.get(name, {})
    if not meta:
        # Try prefix match (e.g. "tkb_01_blur" -> "tkb_01")
        for key in index:
            if name.startswith(key):
                meta = index[key]
                break

    # Try loading dedicated JSON file alongside images
    json_candidate = _GOLDEN_DIR / f"{name}.json"
    if json_candidate.exists():
        file_meta = json.loads(json_candidate.read_text(encoding="utf-8"))
        meta = {**file_meta, **meta} if meta else file_meta

    blur = _is_blur(name, meta)
    khoang: list[dict[str, Any]] = meta.get("khoang_ban", [])
    spans = _spans_from_khoang(khoang)
    confidence = 0.45 if blur else (0.92 if spans else 0.55)

    return {
        "rows": khoang,
        "confidence": confidence,
        "spans": spans,
        "blur": blur,
        "source_id": meta.get("id", name),
        "nhan_vien_id": meta.get("nhan_vien_id"),
    }
