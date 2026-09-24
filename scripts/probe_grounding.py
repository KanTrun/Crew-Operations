"""Kiem tra tinh "khong bia" cua Spatial Memory — bang ham that, khong qua HTTP.

MUC DICH: spec `grand-experience-replay.spec.ts` "failure path: no live LLM, replay
still complete" khang dinh: hoi ve anchor `stockroom` (KHONG co memory confirmed
trong fixture) thi cau tra loi phai co **0 citation**.

Script nay goi thang `build_grounded_answer` voi anchor do de biet citation sinh ra
tu dau — loi o tang agent hay o tang API/UI.

Chay: .venv\\Scripts\\python.exe scripts/probe_grounding.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for rel in ("apps/api/src", "packages/agents/src", "packages/contracts/src"):
    sys.path.insert(0, str(ROOT / rel))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from ca_agents.ag_spatial_memory import (  # noqa: E402
    build_grounded_answer,
    retrieve_filtered,
)

FIX = ROOT / "data" / "fixtures" / "grand_experience" / "spatial-memory.json"
MAP = ROOT / "data" / "fixtures" / "grand_experience" / "spatial-map.json"


def main() -> int:
    raw = json.loads(FIX.read_text(encoding="utf-8"))
    memories = raw.get("memories", [])
    print(f"== Fixture: {FIX.name} ==")
    print(f"   {len(memories)} memory, theo anchor:")
    by_anchor: dict[str, list[tuple[str, str]]] = {}
    for m in memories:
        by_anchor.setdefault(m.get("anchor_id") or "(khong)", []).append(
            (m.get("memory_id"), m.get("status"))
        )
    for a, lst in sorted(by_anchor.items()):
        print(f"     {a:16} {lst}")

    for anchor in ("stockroom", "bar"):
        print(f"\n== Hoi ve anchor '{anchor}' ==")
        q = {"store_id": "quan_01", "anchor_id": anchor, "role": "quan_ly", "requester_id": "quan_ly"}
        try:
            retrieve_filtered(q) if not isinstance(q, dict) else None
        except Exception as e:  # pragma: no cover
            print(f"   retrieve_filtered(dict) loi: {type(e).__name__}: {e}")

        try:
            ans = build_grounded_answer(
                question="chuyện gì đã xảy ra ở đây?",
                anchor_id=anchor,
                store_id="quan_01",
                role="quan_ly",
                requester_id="quan_ly",
            )
            cites = getattr(ans, "citations", None)
            print(f"   citations = {cites!r}  (so luong = {len(cites) if cites else 0})")
            txt = getattr(ans, "response", None) or getattr(ans, "text", None)
            print(f"   response  = {str(txt)[:130]!r}")
            if anchor == "stockroom" and cites:
                print("   => LOI: anchor khong co memory confirmed nhung VAN co citation.")
        except TypeError as e:
            print(f"   goi bang keyword khong dung chu ky: {e}")
        except Exception as e:
            print(f"   loi: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
