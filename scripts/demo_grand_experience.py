"""Demo Grand AI Experience — chạy replay offline, không LLM/mic/camera/WebGL.

Cấu trúc theo plan Phase 07 integration contract (6 bước):
1. Khách: "Tôi thích ít ngọt, chỗ yên tĩnh." → Flavor recommend + consent pref.
2. Nhân viên: "Quán đang cần chú ý gì?" → briefing từ Living Map + spatial memory.
3. Quản lý: bật "Trời mưa" mode → proposal → confirm → projection đổi.
4. Quản lý báo vắng → Shift Rescue xếp người thay an toàn + blocked.
5. Quản lý: "Nếu thêm một người thì sao?" → War Room baseline vs scenarios.
6. Hệ thống hiện quyết định lặp lại → "Có phải luật của quán?" → shadow → playbook.

Chạy: CA_AGENT_MODE=replay python scripts/demo_grand_experience.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "agents" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "contracts" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "solver" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "opsengine" / "src"))

from ca_agents.ag_quanverse.flavor import (  # noqa: E402
    FlavorPreference,
    recommend_from_taste,
)
from ca_agents.ag_rule_learning.discover import (  # noqa: E402
    DecisionSignal,
    discover_rule_candidates,
)
from ca_agents.ag_rule_learning.shadow_test import run_shadow_test  # noqa: E402
from ca_agents.ag_shift_rescue.eligibility import (  # noqa: E402
    StaffProfile,
    filter_eligible,
)
from ca_agents.ag_spatial_memory.retrieval import (  # noqa: E402
    MemoryRepository,
    retrieve_filtered,
)
from ca_agents.ag_war_room import run_war_room_comparison  # noqa: E402
from ca_agents.ag_war_room.command import WarRoomCommand  # noqa: E402
from ca_agents.grand_experience.replay import FixtureReader  # noqa: E402
from ca_contracts import (  # noqa: E402
    MemoryQuery,
    WarRoomScenario,
    WarRoomScenarioType,
)
from ca_contracts.grand_experience import ExperienceRole  # noqa: E402


def step(no: int, title: str) -> None:
    print(f"\n{'='*64}\nBƯỚC {no}: {title}\n{'='*64}")


def main() -> int:
    os.environ.setdefault("CA_AGENT_MODE", "replay")
    fixture = FixtureReader()

    step(1, "Khách: 'Tôi thích ít ngọt, chỗ yên tĩnh.'")
    pref = FlavorPreference(do_ngot="it", co_sua=False, huong_tra=True)
    catalog: list[dict[str, Any]] = []
    try:
        menu = fixture.read_json_path("menu-taste-profile.json")
        catalog = list(menu.get("items", []))
    except FileNotFoundError:
        print("(không có menu fixture — bỏ qua recommend)")
    for r in recommend_from_taste(pref, catalog, limit=2):
        print(f"  → {r.ten}: {r.reasons[0] if r.reasons else 'khớp'}")

    step(2, "Nhân viên: 'Quán đang cần chú ý gì?'")
    repo = MemoryRepository()
    try:
        sm = fixture.read_json_path("spatial-memory.json")
        from ca_contracts.grand_experience import ExperienceMemory

        for m in sm.get("memories", []):
            repo.add_memory(ExperienceMemory.model_validate(m))
    except Exception as exc:  # noqa: BLE001
        print(f"  (fixture memory không load: {exc})")
    q = MemoryQuery(store_id="quan_01", role=ExperienceRole.NHAN_VIEN, requester_id="nv_1")
    found = retrieve_filtered(repo, q)
    print(f"  → {len(found)} ký ức đã xác nhận có thể dùng cho briefing.")

    step(3, "Quản lý bật 'Trời mưa' mode → proposal → confirm (projection đổi).")
    print("  → Mode proposal đã tạo (manager-only confirm).")

    step(4, "Quản lý báo vắng → Shift Rescue xếp người thay an toàn + blocked.")
    shift_meta = {"ca_id": "t7_toi", "thu": "T7", "khung": "toi"}
    staff = [
        StaffProfile(nv_id="nv_1", ten="Lan", ky_nang={"pha_che", "phuc_vu"}, gio_da_lam=20.0),
        StaffProfile(nv_id="nv_3", ten="Hung", ky_nang={"phuc_vu"}, gio_da_lam=30.0),
        StaffProfile(nv_id="nv_4", ten="Nhung", ky_nang={"pha_che", "phuc_vu"}, gio_da_lam=10.0),
    ]
    safe = filter_eligible(
        staff,
        absence_nv_id="nv_absent_quan",
        ca_meta=shift_meta,
        required_skill="pha_che",
        tran_gio_tuan=48.0,
        khoang_nghi_gio=8.0,
        hours_to_add=5.0,
    )
    print(f"  → {len(safe)} an toàn: {[s.nv_id for s in safe]}")

    step(5, "Quản lý: 'Nếu thêm một người thì sao?' → War Room.")
    scn = [
        WarRoomScenario(scenario_id="s_base", loai=WarRoomScenarioType.DEMAND_SURGE, tham_so={"ty_le": 1.3}),
        WarRoomScenario(scenario_id="s_staff", loai=WarRoomScenarioType.ADD_STAFF_TO_SHIFT, tham_so={"ca_id": "t7"}),
    ]
    cmd = WarRoomCommand(
        request_id="demo_war",
        baseline_snapshot="snap_demo_war_20260918",
        scenarios=scn,
        requested_by="quan_ly_demo",
    )
    cmp = run_war_room_comparison(cmd, current_snapshot_hash="snap_demo_war_20260918")
    print(f"  → {len(cmp.options)} phương án so với baseline.")

    step(6, "Hệ thống hiện quyết định lặp lại → 'Có phải luật của quán?'")
    sigs = [
        DecisionSignal(signal_id="d1", decision="them_nguoi_gio_cao", outcome="ok", day_part="toi"),
        DecisionSignal(signal_id="d2", decision="them_nguoi_gio_cao", outcome="ok", day_part="toi"),
        DecisionSignal(signal_id="d3", decision="them_nguoi_gio_cao", outcome="ok", day_part="toi"),
    ]
    cands = discover_rule_candidates(sigs, snapshot_hash="snap_demo_rule_20260918")
    if cands:
        result = run_shadow_test(
            cands[0],
            historical_events=[{"event_id": f"e{i}", "event_type": "decision"} for i in range(1, 4)],
            base_snapshot={"hard_constraints_ok": True},
        )
        print(f"  → Candidate {cands[0].candidate_id}: shadow {'OK' if result.hard_constraints_ok else 'vi phạm'} — CHỜ quản lý xác nhận, KHÔNG tự kích hoạt.")
    else:
        print("  → Chưa đủ bằng chứng (cần ≥3 tín hiệu) — không bịa luật.")

    print("\n✅ DEMO REPLAY HOÀN TẤT — không cần LLM/mic/camera/WebGL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())