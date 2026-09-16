"""Gọi thẳng tool_solve_weekly_schedule với sources giống API để bắt exception thật."""
import sys
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, "/app/apps/api/src")

try:
    from ca_agents.ag_copilot import tool_registry as tr
    from ca_api.nhan_vien import list_nhan_vien_ops
    from ca_api.persist import kv_get, list_users
    from ca_playbook.sua import list_sua
    from ca_playbook.vong_doi import list_luat

    # Cấu hình sources tối thiểu giống API
    tr.configure_data_sources(
        kv_get=kv_get,
        list_luat=list_luat,
        list_sua=list_sua,
        list_nhan_vien_ops=list_nhan_vien_ops,
        list_users=lambda: [
            {"nv_id": u["nv_id"], "ten": u["display_name"], "role": u["role"]}
            for u in list_users()
        ],
    )

    print("--- gọi tool_solve_weekly_schedule trực tiếp ---")
    try:
        result = tr.tool_solve_weekly_schedule(store_id="quan_01", tuan="2026-W39")
        print(f"success={result.success}")
        print(f"summary={result.summary}")
        print(f"error={result.error}")
        print(f"explanation={result.explanation}")
    except Exception:
        print("TOOL EXCEPTION (không bị bắt):")
        traceback.print_exc()
except Exception:
    traceback.print_exc()
