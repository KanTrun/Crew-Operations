from __future__ import annotations

from pathlib import Path

from ca_agents.llm import LlmResult
from ca_agents.runtime import AgentRuntime


def test_runtime_caches_by_identity() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "ca_agents" / "prompts"
    rt = AgentRuntime(prompts_root=root)
    a = rt.run_replay("ag_tkb", "0.1.0", {"image": "x"})
    b = rt.run_replay("ag_tkb", "0.1.0", {"image": "x"})
    assert a is b
    assert a["mode"] == "replay"


def test_runtime_live_parses_json(monkeypatch: object) -> None:
    def fake_complete(**_k: object) -> LlmResult:
        return LlmResult(ok=True, text='{"ok":true}', provider="gemini", reason="ok")

    monkeypatch.setattr("ca_agents.runtime.complete", fake_complete)  # type: ignore[attr-defined]
    root = Path(__file__).resolve().parents[1] / "src" / "ca_agents" / "prompts"
    rt = AgentRuntime(prompts_root=root)
    out = rt.run("ag_tkb", "0.1.0", {"id": "tkb_01"}, mode="live")
    assert out["mode"] == "live"
    assert out["ok"] is True
    assert out["result"] == {"ok": True}
    assert out["provider"] == "gemini"
