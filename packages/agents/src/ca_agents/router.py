"""Free-tier provider router — groq → gemini → openrouter → ollama, replay-first."""

from __future__ import annotations

from dataclasses import dataclass

_LIVE_ORDER = ("groq", "gemini", "openrouter", "ollama")


@dataclass(frozen=True)
class RouteDecision:
    provider: str
    reason: str


class FreeTierRouter:
    """Route a task to the cheapest available provider.

    In replay mode always returns ``provider="replay"``.
    In live mode iterates groq → gemini → openrouter → ollama.
    Pass ``exhausted`` as a set of providers already tried to skip them.
    If all four are exhausted, returns ``provider="tu_choi"`` (escalate).
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
        for provider in _LIVE_ORDER:
            if provider not in skip:
                if task.startswith("vision") and provider == "ollama":
                    reason = "vision_fallback"
                else:
                    reason = f"live_order:{provider}"
                return RouteDecision(provider=provider, reason=reason)

        return RouteDecision(provider="tu_choi", reason="all_providers_exhausted_escalate")
