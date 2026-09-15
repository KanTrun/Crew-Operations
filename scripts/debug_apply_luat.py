"""Debug apply_luat — nguồn nghi vấn gây exception trong tool_solve_weekly_schedule."""
import sys
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, "/app/apps/api/src")

try:
    from ca_api.nhan_vien import list_nhan_vien_ops
    from ca_playbook.vong_doi import list_luat
    from ca_solver import apply_luat, build_lich_input, solve_cpsat

    nvs = list_nhan_vien_ops()
    inp = build_lich_input(nhan_vien_ngoai=nvs)

    luat = list_luat()
    print(f"list_luat: {len(luat)} luật")
    for luat_item in luat[:10]:
        print(f"  {luat_item}")

    print("\n--- apply_luat ---")
    try:
        inp2, applied = apply_luat(inp, luat)
        print(f"apply_luat OK, applied={applied}")
    except Exception:
        print("apply_luat EXCEPTION:")
        traceback.print_exc()

    print("\n--- solve_cpsat sau apply_luat ---")
    res = solve_cpsat(inp)
    print(f"ok={res.ok} status={res.status} violations={res.violations}")
except Exception:
    traceback.print_exc()
