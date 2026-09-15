"""Debug tool_solve_weekly_schedule với nguồn NV thật (giống API)."""
import sys
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, "/app/apps/api/src")

try:
    from ca_api.nhan_vien import list_nhan_vien_ops
    from ca_solver import build_lich_input, solve_cpsat

    nvs = list_nhan_vien_ops()
    print(f"list_nhan_vien_ops: {len(nvs)} NV")
    for n in nvs:
        print(f"  {n.get('id')} vai={n.get('vai')} ky_nang={n.get('ky_nang')}")

    inp = build_lich_input(nhan_vien_ngoai=nvs)
    print(f"\nnhan_vien_ids: {inp.nhan_vien_ids}")
    print(f"ca_ids count: {len(inp.ca_ids)}")
    print(f"tran_gio_tuan={inp.tran_gio_tuan} khoang_nghi_gio={inp.khoang_nghi_gio}")

    res = solve_cpsat(inp)
    print(f"\nsolve_cpsat: ok={res.ok} status={res.status} violations={res.violations}")
except Exception:
    traceback.print_exc()
