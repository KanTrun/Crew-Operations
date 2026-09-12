"""Live LLM client — groq → gemini → openrouter → ollama. Fail closed.

Never invents a payload when the provider errors or returns non-JSON.
Does not override process env (CI `CA_AGENT_MODE=replay` wins over `.env`).
"""

from __future__ import annotations

import json
import os
import urllib.error
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
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "groq/compound",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
)
_GEMINI_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
)


_OPENROUTER_MODELS = (
    "minimax/minimax-m3:free",
    "minimax/minimax-m2.7:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
    "cohere/north-mini-code:free",
    "dots-studio/dots-3-note-preview:free",
    "openai/gpt-oss-20b:free",
    "deepseek/deepseek-chat:free",
    "meta-llama/llama-3.3-70b-instruct:free",
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


_MODEL_ALIASES: dict[str, str] = {
    "minimax-m3": "minimax/minimax-m3:free",
    "minimax/minimax-m3": "minimax/minimax-m3:free",
    "minimax-m2.7": "minimax/minimax-m2.7:free",
    "minimax/minimax-m2.7": "minimax/minimax-m2.7:free",
    "qwen-3.8-27b": "qwen/qwen3.8-27b",
    "qwen-3.6-27b": "qwen/qwen3.6-27b",
    "gpt-oss-120b": "openai/gpt-oss-120b",
    "gpt-oss-20b": "openai/gpt-oss-20b",
    "nemotron-3.5-lightning": "nvidia/nemotron-3.5-lightning:free",
    "gemma-4-31b": "google/gemma-4-31b-it:free",
    "gemma-4-26b": "google/gemma-4-26b-a4b-it:free",
}


def _env_model(name: str, default: str) -> str:
    return os.environ.get(name, default).strip() or default


def _model_list(env_name: str, defaults: tuple[str, ...]) -> list[str]:
    raw_preferred = _env_model(env_name, defaults[0])
    preferred = _MODEL_ALIASES.get(raw_preferred, raw_preferred)
    out: list[str] = []
    for name in (preferred, raw_preferred, *defaults):
        canonical = _MODEL_ALIASES.get(name, name)
        if canonical not in out:
            out.append(canonical)
        if name not in out:
            out.append(name)
    return out


def _is_model_missing(exc: _ProviderError) -> bool:
    """True nếu model thiếu (404), không hợp lệ (400 not a valid model), bị quá tải (429/503), timeout hoặc bị lỗi/treo."""
    msg = str(exc).lower()
    return (
        msg.startswith("http_404")
        or (msg.startswith("http_400") and ("not a valid model" in msg or "invalid model" in msg))
        or msg.startswith("http_429")
        or msg.startswith("http_500")
        or msg.startswith("http_502")
        or msg.startswith("http_503")
        or msg.startswith("http_504")
        or "timeout" in msg
        or "rate limit" in msg
        or "overloaded" in msg
        or "capacity" in msg
        or "no longer available" in msg
        or "is unavailable" in msg
        or "missing_choices" in msg
        or "missing_candidates" in msg
        or "empty" in msg
        or "bad_json_response" in msg
    )


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
                    timeout_s=min(timeout_s, 10.0),
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
                    timeout_s=min(timeout_s, 12.0),
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
                    timeout_s=min(timeout_s, 20.0),
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


def _openai_compat_stream(
    *,
    url: str,
    token: str,
    model: str,
    system: str,
    user: str,
    timeout_s: float,
    json_mode: bool,
) -> Any:
    """Return a line-iterator over SSE deltas for an OpenAI-compatible endpoint.

    Không đụng `_openai_compat` (vẫn dùng cho tác vụ JSON tất định). Trả về
    generator các chunk text — chỉ dùng cho copilot streaming.
    """
    payload: dict[str, Any] = {
        "model": model,
        "temperature": 0,
        "stream": True,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", _UA)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout_s)
    except urllib.error.HTTPError as exc:
        raise _ProviderError(f"http_{exc.code}") from exc
    except urllib.error.URLError as exc:
        raise _ProviderError(f"net:{exc.reason}") from exc

    def _iter_lines() -> Any:
        for raw_line in resp:
            line = raw_line.decode("utf-8", "replace").strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:") :].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = obj.get("choices") or []
            if not choices:
                continue
            delta = (choices[0].get("delta") or {}).get("content")
            if delta:
                yield delta
        resp.close()
        return

    return _iter_lines()


def complete_stream(
    *,
    system: str,
    user: str,
    task: str = "text",
    timeout_s: float = 45.0,
) -> tuple[str, Any]:
    """Stream a live LLM response (copilot). Trả về (provider, generator chunk text).

    Dàn xếp: groq → openrouter (những provider OpenAI-compatible có stream).
    Nếu không có credential / replay → trả () rỗng (caller fallback về complete).
    """
    ensure_dotenv()
    router = FreeTierRouter(mode="live")
    for provider in ("groq", "openrouter"):
        decision = router.choose(task, set())
        # Chỉ thử provider OpenAI-compatible đã có key.
        if decision.provider != provider or not provider_status().get(provider, False):
            continue
        try:
            gen = _openai_compat_stream(
                url={"groq": "https://api.groq.com/openai/v1/chat/completions", "openrouter": "https://openrouter.ai/api/v1/chat/completions"}[provider],
                token=os.environ[_KEY_ENV[provider]].strip(),
                model=_env_model(
                    "GROQ_MODEL" if provider == "groq" else "OPENROUTER_MODEL",
                    "llama-3.1-8b-instant" if provider == "groq" else _OPENROUTER_MODELS[0],
                ),
                system=system,
                user=user,
                timeout_s=timeout_s,
                json_mode=False,
            )
            return provider, gen
        except _ProviderError:
            continue
    return "", ()


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

    # API key qua header, không qua URL query — key trong URL bị log ở
    # proxy/access-log và rò ra ngoài. Gemini hỗ trợ x-goog-api-key.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
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
    data = _http_json(url, payload, headers={"x-goog-api-key": token}, timeout_s=timeout_s)
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
