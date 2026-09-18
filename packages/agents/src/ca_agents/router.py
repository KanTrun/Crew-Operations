"""Free-tier provider router — groq → gemini → openrouter → ollama, replay-first."""

from __future__ import annotations

from dataclasses import dataclass

# Nguyên tắc (260918): API Gemini CHỈ dùng cho model Live (Voice Copilot + STT Live).
# Các tác vụ AI agent text (extract biên bản, chat, ...) dùng model bên khác:
# groq → openrouter → bai → ollama. Bỏ gemini khỏi live text order.
_LIVE_ORDER = ("groq", "openrouter", "bai", "ollama")
# Ảnh TKB: ưu tiên Gemini (vision ổn định trên free tier); bỏ ollama (không gửi ảnh).
_VISION_ORDER = ("gemini", "openrouter", "groq", "bai")


@dataclass(frozen=True)
class RouteDecision:
    provider: str
    reason: str


class FreeTierRouter:
    """Route a task to the cheapest available provider.

    In replay mode always returns ``provider="replay"``.
    In live mode iterates groq → openrouter → bai → ollama (Gemini REST bị loại —
    Gemini chỉ dùng cho model Live: Voice Copilot + STT Live).
    Vision tasks use gemini → openrouter → groq.
    Pass ``exhausted`` as a set of providers already tried to skip them.
    If all are exhausted, returns ``provider="tu_choi"`` (escalate).
    """

    def __init__(self, mode: str = "replay") -> None:
        self.mode = mode

    def choose(
        self,
        task: str,
        exhausted: frozenset[str] | set[str] | None = None,
    ) -> RouteDecision:
        if self.mode == "replay":
            return RouteDecision(provider="replay", reason="CA_AGENT_MODE=replay")

        skip = set(exhausted or ())
        order = _VISION_ORDER if task.startswith("vision") else _LIVE_ORDER
        for provider in order:
            if provider not in skip:
                return RouteDecision(provider=provider, reason=f"live_order:{provider}")

        return RouteDecision(provider="tu_choi", reason="all_providers_exhausted_escalate")
