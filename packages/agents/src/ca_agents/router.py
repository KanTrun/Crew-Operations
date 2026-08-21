"""Free-tier provider router stub."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteDecision:
    provider: str
    reason: str


class FreeTierRouter:
    def __init__(self, mode: str = "replay") -> None:
        self.mode = mode

    def choose(self, task: str) -> RouteDecision:
        if self.mode == "replay":
            return RouteDecision(provider="replay", reason="CA_AGENT_MODE=replay")
        # Prefer local when cloud quotas unknown
        if task.startswith("vision"):
            return RouteDecision(provider="ollama", reason="vision_fallback")
        return RouteDecision(provider="ollama", reason="default_local")
