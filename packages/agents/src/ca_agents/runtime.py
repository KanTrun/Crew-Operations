"""Agent runtime — versioned prompts + content-hash cache. No DB writes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True)
class PromptRef:
    agent: str
    version: str
    path: Path


class ContentCache:
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    @staticmethod
    def key(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()

    def get(self, digest: str) -> Any | None:
        return self._store.get(digest)

    def put(self, digest: str, value: Any) -> None:
        self._store[digest] = value


class AgentRuntime:
    """Sprint 1 frame: load prompt file, cache by content, replay-safe."""

    def __init__(self, prompts_root: Path | None = None) -> None:
        root = prompts_root or Path(__file__).resolve().parent / "prompts"
        self.prompts_root = root
        self.cache = ContentCache()

    def load_prompt(self, agent: str, version: str) -> PromptRef:
        path = self.prompts_root / agent / f"{version}.md"
        if not path.exists():
            raise FileNotFoundError(path)
        return PromptRef(agent=agent, version=version, path=path)

    def run_replay(self, agent: str, version: str, inp: dict[str, Any]) -> dict[str, Any]:
        ref = self.load_prompt(agent, version)
        blob = json.dumps({"agent": agent, "v": version, "in": inp}, sort_keys=True).encode()
        digest = self.cache.key(blob)
        hit = self.cache.get(digest)
        if hit is not None:
            return cast(dict[str, Any], hit)
        text = ref.path.read_text(encoding="utf-8")
        out = {
            "agent": agent,
            "prompt_version": version,
            "mode": "replay",
            "prompt_chars": len(text),
            "result": None,
            "note": "Sprint 1 runtime frame — no live LLM",
        }
        self.cache.put(digest, out)
        return out
