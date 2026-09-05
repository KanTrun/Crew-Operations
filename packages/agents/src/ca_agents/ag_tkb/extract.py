"""AG-TKB extraction — replay reads golden JSON; live calls LLM and fail-closes."""

from __future__ import annotations

import json
import mimetypes
import pathlib
import re
from typing import Any

from ca_agents.llm import LlmResult, agent_mode, complete, parse_json_object

_GOLDEN_DIR = pathlib.Path(__file__).resolve().parents[5] / "data" / "golden" / "tkb"
_PROMPT = pathlib.Path(__file__).resolve().parents[1] / "prompts" / "ag_tkb" / "0.1.0.md"
_INDEX: dict[str, Any] | None = None
_THU = {"T2", "T3", "T4", "T5", "T6", "T7", "CN"}
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


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
    return [{"day": k["thu"], "start": k["start"], "end": k["end"]} for k in khoang]


def _clean_khoang(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        thu = str(item.get("thu") or "").strip().upper()
        if thu in {"CN", "T8", "CHỦ NHẬT", "CHU NHAT"}:
            thu = "CN"
        start = str(item.get("start") or "").strip()
        end = str(item.get("end") or "").strip()
        if thu not in _THU or not _HHMM.match(start) or not _HHMM.match(end):
            continue
        out.append({"thu": thu, "start": start, "end": end})
    return out


def _resolve_source(image_path_or_id: str) -> pathlib.Path | None:
    p = pathlib.Path(image_path_or_id)
    if p.is_file():
        return p
    name = p.stem
    for ext in (".svg", ".png", ".jpg", ".jpeg", ".webp", ".txt"):
        cand = _GOLDEN_DIR / f"{name}{ext}"
        if cand.exists():
            return cand
    return None


def _empty(
    *,
    name: str,
    blur: bool,
    confidence: float,
    reason: str,
    provider: str,
) -> dict[str, Any]:
    return {
        "rows": [],
        "confidence": confidence,
        "spans": [],
        "blur": blur,
        "source_id": name,
        "nhan_vien_id": None,
        "mode": "live",
        "provider": provider,
        "escalate": True,
        "reason": reason,
    }


def extract_tkb(
    image_path_or_id: str,
    mode: str | None = None,
) -> dict[str, Any]:
    """Return structured TKB extraction result.

    Parameters
    ----------
    image_path_or_id:
        Filesystem path to image OR a golden fixture ID (e.g. ``tkb_01``).
    mode:
        ``replay`` reads ``data/golden/tkb/``. ``live`` calls the free-tier LLM
        router and fail-closes (empty rows, escalate) when the model cannot
        return valid JSON. Defaults to ``CA_AGENT_MODE``.
    """
    resolved = (mode or agent_mode() or "replay").strip().lower()
    if resolved != "live":
        return _extract_replay(image_path_or_id)
    return _extract_live(image_path_or_id)


def _extract_replay(image_path_or_id: str) -> dict[str, Any]:
    name = pathlib.Path(image_path_or_id).stem
    index = _load_index()

    meta: dict[str, Any] = index.get(name, {})
    if not meta:
        for key in index:
            if name.startswith(key):
                meta = index[key]
                break

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
        "mode": "replay",
        "provider": "replay",
        "escalate": blur or not spans,
        "reason": "golden",
    }


def _extract_live(image_path_or_id: str) -> dict[str, Any]:
    name = pathlib.Path(image_path_or_id).stem
    blur = _is_blur(name, {})
    source = _resolve_source(image_path_or_id)
    if source is None:
        return _empty(
            name=name,
            blur=blur,
            confidence=0.2,
            reason="missing_source",
            provider="tu_choi",
        )

    image_bytes: bytes | None = None
    image_mime: str | None = None
    try:
        payload = source.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        payload = "Trích lịch làm việc từ ảnh đính kèm."
        image_bytes = source.read_bytes()
        image_mime = mimetypes.guess_type(source.name)[0] or "application/octet-stream"

    system = (
        _PROMPT.read_text(encoding="utf-8")
        if _PROMPT.exists()
        else ("Trả JSON {khoang_ban:[{thu,start,end}], doc_duoc:bool}. Không bịa giờ.")
    )
    result: LlmResult = complete(
        system=system,
        user=payload,
        task="text:ag_tkb",
        json_mode=True,
        image_bytes=image_bytes,
        image_mime=image_mime,
    )
    if not result.ok:
        return _empty(
            name=name,
            blur=blur,
            confidence=0.2,
            reason=result.reason,
            provider=result.provider,
        )

    parsed = parse_json_object(result.text)
    if parsed is None:
        return _empty(
            name=name,
            blur=blur,
            confidence=0.2,
            reason="parse_error",
            provider=result.provider,
        )

    khoang = _clean_khoang(parsed.get("khoang_ban"))
    doc_duoc = bool(parsed.get("doc_duoc", bool(khoang)))
    if not doc_duoc:
        khoang = []
    spans = _spans_from_khoang(khoang)
    confidence = 0.45 if blur or not khoang else 0.82
    return {
        "rows": khoang,
        "confidence": confidence,
        "spans": spans,
        "blur": blur or not doc_duoc,
        "source_id": name,
        "nhan_vien_id": None,
        "mode": "live",
        "provider": result.provider,
        "escalate": not khoang,
        "reason": result.reason,
    }
