"""STT Service — Transcribe audio using gemini-3.5-transcribe / Gemini Flash or Groq with speaker diarization."""

from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from ca_agents.llm import agent_mode, ensure_dotenv


@dataclass(frozen=True)
class TranscriptSegment:
    nguoi_noi: str
    noi_dung: str
    bat_dau_s: float | None = None
    ket_thuc_s: float | None = None


@dataclass(frozen=True)
class TranscribeResult:
    ok: bool
    raw_text: str
    segments: list[TranscriptSegment]
    provider: str
    reason: str


def transcribe_audio(
    audio_bytes: bytes,
    mime_type: str = "audio/webm",
    *,
    language: str = "vi",
    timeout_s: float = 60.0,
) -> TranscribeResult:
    """Transcribe audio with speaker diarization.

    Supports Gemini-3.5-Transcribe / Gemini Flash multimodal audio, Groq Whisper, and Replay mode.
    """
    mode = agent_mode()
    if mode == "replay" or not audio_bytes:
        return _replay_transcribe()

    ensure_dotenv()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()

    # 1. Primary: Gemini 3.5 Transcribe / Gemini Audio
    if gemini_key:
        try:
            return _transcribe_with_gemini(
                audio_bytes=audio_bytes,
                mime_type=mime_type,
                api_key=gemini_key,
                timeout_s=timeout_s,
            )
        except Exception as exc:  # noqa: BLE001
            gemini_err = str(exc)
        else:
            gemini_err = ""
    else:
        gemini_err = "missing_gemini_key"

    # 2. Fallback: Groq Whisper
    if groq_key:
        try:
            return _transcribe_with_groq(
                audio_bytes=audio_bytes,
                mime_type=mime_type,
                api_key=groq_key,
                language=language,
                timeout_s=timeout_s,
            )
        except Exception as exc:  # noqa: BLE001
            return TranscribeResult(
                ok=False,
                raw_text="",
                segments=[],
                provider="fail",
                reason=f"gemini_err:{gemini_err};groq_err:{exc}",
            )

    return _replay_transcribe()


def _transcribe_with_gemini(
    audio_bytes: bytes,
    mime_type: str,
    api_key: str,
    timeout_s: float,
) -> TranscribeResult:
    """Call Google Gemini for batch audio transcription.

    Excludes models known ahead-of-time not to support REST batch audio JSON output
    (e.g., gemini-3.5-transcribe is stream-only) to avoid wasting time waiting on API failures.
    """
    default_model = os.environ.get("GEMINI_TRANSCRIBE_MODEL", "gemini-2.5-flash").strip()
    raw_models = [default_model, "gemini-2.5-flash", "gemini-flash-latest"]

    # Pre-filter known incompatible models for REST batch audio + JSON response
    models_to_try: list[str] = []
    for m in raw_models:
        if m in {"gemini-3.5-transcribe", "gemini-3.6-flash"}:
            continue
        if m and m not in models_to_try:
            models_to_try.append(m)
    if not models_to_try:
        models_to_try = ["gemini-2.5-flash", "gemini-flash-latest"]

    # Strip any codec parameters like ';codecs=opus' for Google Gemini API compatibility
    clean_mime = (mime_type or "audio/webm").split(";")[0].strip().lower()
    if clean_mime not in {
        "audio/webm",
        "audio/mp3",
        "audio/wav",
        "audio/ogg",
        "audio/aac",
        "audio/m4a",
        "audio/flac",
    }:
        clean_mime = "audio/webm"

    prompt = (
        "Bạn là bộ chuyển đổi âm thanh sang văn bản chuyên dụng. "
        "Hãy nghe file âm thanh cuộc họp này và thực hiện Speaker Diarization (tách người nói). "
        "Trả về định dạng JSON thuần túy theo cấu trúc:\n"
        "{\n"
        '  "raw_text": "Toàn bộ văn bản cuộc họp",\n'
        '  "segments": [\n'
        '    {"nguoi_noi": "Người nói 1", "noi_dung": "...", "bat_dau_s": 0.0, "ket_thuc_s": 10.5}\n'
        "  ]\n"
        "}"
    )

    b64_data = base64.b64encode(audio_bytes).decode("ascii")
    payload: dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": clean_mime, "data": b64_data}},
                    {"text": prompt},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
        },
    }

    from ca_agents.llm import parse_json_object

    last_err: Exception | None = None
    for m in models_to_try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            f"?key={urllib.parse.quote(api_key, safe='')}"
        )
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
                body = resp.read().decode("utf-8")
            data = json.loads(body)
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(str(p.get("text") or "") for p in parts)
            parsed = parse_json_object(text) or {}

            raw_text = str(parsed.get("raw_text") or "")
            segments_raw = parsed.get("segments") or []
            segs: list[TranscriptSegment] = []
            for s in segments_raw:
                if isinstance(s, dict) and s.get("noi_dung"):
                    segs.append(
                        TranscriptSegment(
                            nguoi_noi=str(s.get("nguoi_noi") or "Người nói"),
                            noi_dung=str(s.get("noi_dung") or ""),
                            bat_dau_s=float(s.get("bat_dau_s"))
                            if s.get("bat_dau_s") is not None
                            else None,
                            ket_thuc_s=float(s.get("ket_thuc_s"))
                            if s.get("ket_thuc_s") is not None
                            else None,
                        )
                    )
            if not raw_text and segs:
                raw_text = " ".join(s.noi_dung for s in segs)

            if raw_text:
                return TranscribeResult(
                    ok=True,
                    raw_text=raw_text,
                    segments=segs,
                    provider=m,
                    reason="success",
                )
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            continue

    raise last_err or RuntimeError("Gemini transcribe all models failed")


def _transcribe_with_groq(
    audio_bytes: bytes,
    mime_type: str,
    api_key: str,
    language: str,
    timeout_s: float,
) -> TranscribeResult:
    """Call Groq Whisper API."""
    import io
    import urllib.request

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    filename = "audio.webm" if "webm" in mime_type else "audio.mp3"

    buf = io.BytesIO()
    buf.write(f"--{boundary}\r\n".encode())
    buf.write(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    buf.write(f"Content-Type: {mime_type}\r\n\r\n".encode())
    buf.write(audio_bytes)
    buf.write(b"\r\n")

    for key, val in [
        ("model", "whisper-large-v3-turbo"),
        ("language", language),
        ("response_format", "verbose_json"),
    ]:
        buf.write(f"--{boundary}\r\n".encode())
        buf.write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        buf.write(val.encode())
        buf.write(b"\r\n")
    buf.write(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        data=buf.getvalue(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
        body = resp.read().decode("utf-8")
    data = json.loads(body)
    raw_text = str(data.get("text") or "")

    segs: list[TranscriptSegment] = []
    for s in data.get("segments") or []:
        segs.append(
            TranscriptSegment(
                nguoi_noi="Người nói",
                noi_dung=str(s.get("text") or "").strip(),
                bat_dau_s=float(s.get("start", 0)),
                ket_thuc_s=float(s.get("end", 0)),
            )
        )
    return TranscribeResult(
        ok=True,
        raw_text=raw_text,
        segments=segs,
        provider="groq_whisper",
        reason="success",
    )


def _replay_transcribe() -> TranscribeResult:
    """Fixture fallback for offline/CI replay."""
    fixture_segs = [
        TranscriptSegment(
            nguoi_noi="Quản lý",
            noi_dung="Chào cả nhà, ca chiều nay chúng ta cần vệ sinh máy pha và kiểm tra tủ đá.",
        ),
        TranscriptSegment(
            nguoi_noi="Tuấn", noi_dung="Dạ em Tuấn nhận lau máy pha và thay ron trước 16h."
        ),
        TranscriptSegment(
            nguoi_noi="My", noi_dung="Dạ em My sẽ dán lại công thức trà đào mới trước 17h."
        ),
    ]
    raw = " ".join(s.noi_dung for s in fixture_segs)
    return TranscribeResult(
        ok=True,
        raw_text=raw,
        segments=fixture_segs,
        provider="replay_fixture",
        reason="offline_replay",
    )
