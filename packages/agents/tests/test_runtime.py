from __future__ import annotations

from pathlib import Path

from ca_agents.runtime import AgentRuntime


def test_runtime_caches_by_identity() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "ca_agents" / "prompts"
    rt = AgentRuntime(prompts_root=root)
    a = rt.run_replay("ag_tkb", "0.1.0", {"image": "x"})
    b = rt.run_replay("ag_tkb", "0.1.0", {"image": "x"})
    assert a is b
    assert a["mode"] == "replay"
