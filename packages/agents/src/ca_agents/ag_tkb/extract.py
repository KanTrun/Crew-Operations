<<<<<<< Updated upstream
"""AG-TKB extraction logic — replay-first, no live LLM."""
=======
"""AG-TKB extraction — replay reads golden JSON; live calls LLM (text SVG or vision image)."""
>>>>>>> Stashed changes

from __future__ import annotations

import json
import pathlib
from typing import Any

_GOLDEN_DIR = pathlib.Path(__file__).resolve().parents[5] / "data" / "golden" / "tkb"
_INDEX: dict[str, Any] | None = None
<<<<<<< Updated upstream
=======
_THU = {"T2", "T3", "T4", "T5", "T6", "T7", "CN"}
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
>>>>>>> Stashed changes


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
<<<<<<< Updated upstream
        ``"replay"`` reads from ``data/golden/tkb/``; other values reserved
        for live LLM (not implemented).

    Returns
    -------
    dict with keys: rows, confidence, spans, blur
=======
        ``replay`` reads ``data/golden/tkb/``. ``live`` calls the free-tier LLM
        (text for SVG, vision for PNG/JPEG/WebP) and fail-closes when invalid.
        Defaults to ``CA_AGENT_MODE``.
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
    }
=======
        "mode": "replay",
        "provider": "replay",
        "escalate": False,
        "reason": "golden",
    }


def _system_prompt() -> str:
    if _PROMPT.exists():
        return _PROMPT.read_text(encoding="utf-8")
    return "Trả JSON {khoang_ban:[{thu,start,end}], doc_duoc:bool}. Không bịa giờ."


def _pack_result(
    *,
    name: str,
    blur: bool,
    result: LlmResult,
    parsed: dict[str, Any],
) -> dict[str, Any]:
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

    system = _system_prompt()
    suffix = source.suffix.lower()

    if suffix in _IMAGE_EXT:
        raw = source.read_bytes()
        if len(raw) > 8_000_000:
            return _empty(
                name=name,
                blur=True,
                confidence=0.2,
                reason="file_too_large",
                provider="tu_choi",
            )
        result = complete(
            system=system,
            user=(
                "Đây là ảnh thời khoá biểu. Đọc các khung giờ học / bận trong tuần. "
                "Trả đúng JSON khoang_ban + doc_duoc. Không bịa."
            ),
            task="vision:ag_tkb",
            json_mode=True,
            image_bytes=raw,
            image_mime=_MIME.get(suffix, "image/jpeg"),
            timeout_s=90.0,
        )
    else:
        try:
            payload = source.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return _empty(
                name=name,
                blur=blur,
                confidence=0.2,
                reason="binary_unsupported",
                provider="tu_choi",
            )
        result = complete(
            system=system,
            user=payload,
            task="text:ag_tkb",
            json_mode=True,
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

    return _pack_result(name=name, blur=blur, result=result, parsed=parsed)
>>>>>>> Stashed changes
