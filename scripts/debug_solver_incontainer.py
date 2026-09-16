"""Debug solver trực tiếp trong container."""
import sys
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from ca_solver import build_lich_input, solve_cpsat
    print("import ca_solver OK")

    inp = build_lich_input()
    print(f"LichInput fields: {[f for f in dir(inp) if not f.startswith('_')]}")
    print(f"nhan_vien_ids: {inp.nhan_vien_ids}")
    print(f"tkb: {inp.tkb}")
    print(f"nghi_phep: {inp.nghi_phep}")

    out = solve_cpsat(inp)
    print(f"solve_cpsat OK: {out}")
except Exception:
    traceback.print_exc()
