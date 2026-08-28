"""Live LLM client — groq → gemini → openrouter → ollama. Fail closed.

Never invents a payload when the provider errors or returns non-JSON.
Does not override process env (CI `CA_AGENT_MODE=replay` wins over `.env`).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ca_agents.router import FreeTierRouter

_REPO_ROOT = Path(__file__).resolve().parents[4]
_KEY_ENV = {
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
_GROQ_MODELS = (
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
)
_GEMINI_MODELS = (
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash",
)
_OPENROUTER_MODELS = (
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-8b:free",
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct",
)
_UA = "nhip-quan/0.1 (https://github.com/KanTrun/Crew-Operations)"
_DOTENV_LOADED = False


@dataclass(frozen=True)
class LlmResult:
    ok: bool
    text: str
    provider: str
    reason: str
    exhausted: tuple[str, ...] = ()


def agent_mode() -> str:
    raw = os.environ.get("CA_AGENT_MODE", "replay").strip().lower()
    return raw if raw else "replay"


def load_dotenv(path: Path | None = None, *, override: bool = False) -> Path | None:
    """Load KEY=VALUE lines. Existing process env wins unless override=True."""
    global _DOTENV_LOADED
    candidates: list[Path] = []
    if path is not None:
        candidates.append(path)
    candidates.append(_REPO_ROOT / ".env")
    candidates.append(Path.cwd() / ".env")
    chosen: Path | None = None
    for cand in candidates:
        if cand.is_file():
            chosen = cand
            break
    if chosen is None:
        return None
    for line in chosen.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
    _DOTENV_LOADED = True
    return chosen


def ensure_dotenv() -> None:
    if not _DOTENV_LOADED:
        load_dotenv()


def provider_status() -> dict[str, bool]:
    ensure_dotenv()
    return {
        "groq": bool(os.environ.get(_KEY_ENV["groq"], "").strip()),
        "gemini": bool(os.environ.get(_KEY_ENV["gemini"], "").strip()),
        "openrouter": bool(os.environ.get(_KEY_ENV["openrouter"], "").strip()),
        "ollama": bool(os.environ.get("OLLAMA_BASE_URL", "").strip()),
    }


def parse_json_object(text: str) -> dict[str, Any] | None:
    """Extract a JSON object. Returns None instead of guessing."""
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    try:
        val: Any = json.loads(raw)
        return val if isinstance(val, dict) else None
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            val = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
        return val if isinstance(val, dict) else None


def complete(
    *,
    system: str,
    user: str,
    task: str = "text",
    timeout_s: float = 45.0,
    json_mode: bool = True,
    image_bytes: bytes | None = None,
    image_mime: str | None = None,
) -> LlmResult:
    """Call the first live provider that has credentials and answers.

    Pass ``image_bytes`` + ``image_mime`` for vision tasks (TKB photo).
    """
    ensure_dotenv()
    router = FreeTierRouter(mode="live")
    exhausted: set[str] = set()
    last_reason = "no_provider"
    route_task = "vision:ag_tkb" if image_bytes else task

    while True:
        decision = router.choose(route_task, exhausted)
        if decision.provider == "tu_choi":
            return LlmResult(
                ok=False,
                text="",
                provider="tu_choi",
                reason=last_reason,
                exhausted=tuple(sorted(exhausted)),
            )
        if decision.provider == "replay":
            return LlmResult(ok=False, text="", provider="replay", reason=decision.reason)

        if decision.provider != "ollama" and not provider_status().get(decision.provider, False):
            exhausted.add(decision.provider)
            last_reason = f"missing_key:{decision.provider}"
            continue
        if decision.provider == "ollama" and not provider_status()["ollama"]:
            exhausted.add("ollama")
            last_reason = "ollama_disabled"
            continue

        try:
            text = _call_provider(
                decision.provider,
                system=system,
                user=user,
                timeout_s=timeout_s,
                json_mode=json_mode,
                image_bytes=image_bytes,
                image_mime=image_mime,
            )
        except _ProviderError as exc:
            exhausted.add(decision.provider)
            last_reason = str(exc)
            continue

        if not text.strip():
            exhausted.add(decision.provider)
            last_reason = f"empty:{decision.provider}"
            continue

        return LlmResult(
            ok=True,
            text=text,
            provider=decision.provider,
            reason=decision.reason,
            exhausted=tuple(sorted(exhausted)),
        )


class _ProviderError(RuntimeError):
    pass


def _env_model(name: str, default: str) -> str:
    return os.environ.get(name, default).strip() or default


def _model_list(env_name: str, defaults: tuple[str, ...]) -> list[str]:
    preferred = _env_model(env_name, defaults[0])
    out: list[str] = []
    for name in (preferred, *defaults):
        if name not in out:
            out.append(name)
    return out


def _is_model_missing(exc: _ProviderError) -> bool:
    msg = str(exc)
    return msg.startswith("http_404") or "no longer available" in msg or "is unavailable" in msg


def _call_provider(
    provider: str,
    *,
    system: str,
    user: str,
    timeout_s: float,
    json_mode: bool,
    image_bytes: bytes | None = None,
    image_mime: str | None = None,
) -> str:
    last: _ProviderError | None = None
    if provider == "groq":
        if image_bytes:
            raise _ProviderError("vision_unsupported:groq")
        for model in _model_list("GROQ_MODEL", _GROQ_MODELS):
            try:
                return _openai_compat(
                    url="https://api.groq.com/openai/v1/chat/completions",
                    token=os.environ[_KEY_ENV["groq"]].strip(),
                    model=model,
                    system=system,
                    user=user,
                    timeout_s=timeout_s,
                    json_mode=json_mode,
                )
            except _ProviderError as exc:
                last = exc
                if _is_model_missing(exc):
                    continue
                raise
        raise last or _ProviderError("groq_no_model")
    if provider == "openrouter":
        for model in _model_list("OPENROUTER_MODEL", _OPENROUTER_MODELS):
            try:
                return _openai_compat(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    token=os.environ[_KEY_ENV["openrouter"]].strip(),
                    model=model,
                    system=system,
                    user=user,
                    timeout_s=timeout_s,
                    json_mode=json_mode,
                    image_bytes=image_bytes,
                    image_mime=image_mime,
                    extra_headers={
                        "HTTP-Referer": "https://github.com/KanTrun/Crew-Operations",
                        "X-Title": "NHIP QUAN",
                    },
                )
            except _ProviderError as exc:
                last = exc
                if _is_model_missing(exc):
                    continue
                raise
        raise last or _ProviderError("openrouter_no_model")
    if provider == "gemini":
        for model in _model_list("GEMINI_MODEL", _GEMINI_MODELS):
            try:
                return _gemini(
                    token=os.environ[_KEY_ENV["gemini"]].strip(),
                    model=model,
                    system=system,
                    user=user,
                    timeout_s=timeout_s,
                    json_mode=json_mode,
                    image_bytes=image_bytes,
                    image_mime=image_mime,
                )
            except _ProviderError as exc:
                last = exc
                if _is_model_missing(exc):
                    continue
                raise
        raise last or _ProviderError("gemini_no_model")
    if provider == "ollama":
        if image_bytes:
            raise _ProviderError("vision_unsupported:ollama")
        return _ollama(
            base=os.environ["OLLAMA_BASE_URL"].rstrip("/"),
            model=_env_model("OLLAMA_MODEL", "llama3.2"),
            system=system,
            user=user,
            timeout_s=min(timeout_s, 8.0),
        )
    raise _ProviderError(f"unknown_provider:{provider}")


def _http_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str],
    timeout_s: float,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", _UA)
    for key, value in headers.items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:240]
        raise _ProviderError(f"http_{exc.code}:{detail}") from exc
    except urllib.error.URLError as exc:
        raise _ProviderError(f"net:{exc.reason}") from exc
    except TimeoutError as exc:
        raise _ProviderError("timeout") from exc
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _ProviderError("bad_json_response") from exc
    if not isinstance(data, dict):
        raise _ProviderError("non_object_response")
    return data


def _openai_compat(
    *,
    url: str,
    token: str,
    model: str,
    system: str,
    user: str,
    timeout_s: float,
    json_mode: bool,
    extra_headers: dict[str, str] | None = None,
    image_bytes: bytes | None = None,
    image_mime: str | None = None,
) -> str:
    if image_bytes:
        import base64

        mime = image_mime or "image/jpeg"
        b64 = base64.b64encode(image_bytes).decode("ascii")
        user_content: Any = [
            {"type": "text", "text": user},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]
    else:
        user_content = user
    payload: dict[str, Any] = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {token}", **(extra_headers or {})}
    try:
        data = _http_json(url, payload, headers=headers, timeout_s=timeout_s)
    except _ProviderError as exc:
        if not json_mode or not str(exc).startswith("http_400"):
            raise
        payload.pop("response_format", None)
        data = _http_json(url, payload, headers=headers, timeout_s=timeout_s)
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise _ProviderError("missing_choices") from exc
    if not isinstance(content, str):
        raise _ProviderError("non_text_content")
    return content


def _gemini(
    *,
    token: str,
    model: str,
    system: str,
    user: str,
    timeout_s: float,
    json_mode: bool,
    image_bytes: bytes | None = None,
    image_mime: str | None = None,
) -> str:
    import base64

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={urllib.parse.quote(token, safe='')}"
    )
    parts: list[dict[str, Any]] = []
    if image_bytes:
        parts.append(
            {
                "inline_data": {
                    "mime_type": image_mime or "image/jpeg",
                    "data": base64.b64encode(image_bytes).decode("ascii"),
                }
            }
        )
    parts.append({"text": user})
    payload: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": 0},
    }
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"
    data = _http_json(url, payload, headers={}, timeout_s=timeout_s)
    try:
        parts_out = data["candidates"][0]["content"]["parts"]
        text = "".join(str(p.get("text") or "") for p in parts_out)
    except (KeyError, IndexError, TypeError) as exc:
        raise _ProviderError("missing_candidates") from exc
    if not text.strip():
        raise _ProviderError("empty_candidates")
    return text


def _ollama(
    *,
    base: str,
    model: str,
    system: str,
    user: str,
    timeout_s: float,
) -> str:
    data = _http_json(
        f"{base}/api/chat",
        {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        headers={},
        timeout_s=timeout_s,
    )
    msg = data.get("message") or {}
    content = msg.get("content") if isinstance(msg, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise _ProviderError("ollama_empty")
    return content
