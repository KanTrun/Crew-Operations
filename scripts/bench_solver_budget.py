"""Do chat luong loi giai theo ngan sach thoi gian — de chon lai time_limit cho dung.

VI SAO: `scripts/e2e_http_copilot.py` dat timeout client 60s, con
`run_solver` goi `solve_cpsat(..., time_limit_s=60.0)` => solver duoc cap 59.5s va
DUNG HET ngan sach do de chung minh tinh toi uu. Ket qua do duoc: 59.9-60.0s, tuc
la luon sat nut. Lan chay lot, lan chay vo `TimeoutError` — khong phai loi chap chon
ma la dua sát nguong.

Truoc khi ha ngan sach phai tra loi duoc: ha xuong thi lich co TE HON khong?
Script nay chay solver voi nhieu muc thoi gian tren CUNG mot dau vao, roi so sanh:
  - co tim ra loi giai khong (status)
  - gia tri objective (thap hon = tot hon)
  - so rang buoc cung bi vi pham
  - tong thoi gian

Ket luan chi duoc phep rut ra tu so lieu nay, khong tu cam nhan.

Chay: .venv\\Scripts\\python.exe scripts/bench_solver_budget.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for rel in ("apps/api/src", "packages/solver/src", "packages/agents/src", "packages/contracts/src"):
    sys.path.insert(0, str(ROOT / rel))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    from ca_api.services.solver_adapter import build_lich_input  # noqa: PLC0415
    from ca_solver import solve_cpsat  # noqa: PLC0415
    from ca_solver.model import solve_hard_only  # noqa: PLC0415

    print("== Do chat luong theo ngan sach thoi gian ==\n")
    t0 = time.perf_counter()
    data = build_lich_input(nhan_vien_ngoai=[])
    print(f"dung dau vao: {time.perf_counter() - t0:.2f}s")
    print(
        f"  nhan vien={len(data.nhan_vien_ids)}  ca={len(data.ca_ids)}  "
        f"rang buoc tkb={sum(len(v) for v in data.tkb.values())}\n"
    )

    budgets = [2.0, 5.0, 8.0, 10.0, 15.0, 20.0, 30.0, 60.0]
    rows = []
    for b in budgets:
        t = time.perf_counter()
        r = solve_cpsat(data, time_limit_s=b)
        wall = time.perf_counter() - t
        hard = solve_hard_only(
            type(data)(
                nhan_vien_ids=data.nhan_vien_ids,
                ca_ids=data.ca_ids,
                phan_cong=dict(r.phan_cong or {}),
                tkb=data.tkb,
                ca_meta=data.ca_meta,
                ky_nang=data.ky_nang,
                vi_tri_can=data.vi_tri_can,
                so_nguoi_toi_thieu=data.so_nguoi_toi_thieu,
                nghi_phep=data.nghi_phep,
                gio_da_lam=data.gio_da_lam,
                tran_gio_tuan=data.tran_gio_tuan,
                khoang_nghi_gio=data.khoang_nghi_gio,
                debt=data.debt,
                phan_cong_tuan_truoc=data.phan_cong_tuan_truoc,
                nhan_vien_kinh_nghiem=data.nhan_vien_kinh_nghiem,
            )
        ) if r.ok else None
        rows.append(
            {
                "budget": b,
                "wall": wall,
                "status": r.status,
                "ok": r.ok,
                "obj": r.objective,
                "viol": len(r.violations or []),
                "hard_ok": bool(hard.ok) if hard else False,
                "hard_viol": len(hard.violations) if hard else -1,
                "slots": sum(len(v) for v in (r.phan_cong or {}).values()),
            }
        )
        print(
            f"  ngan sach {b:5.1f}s -> thuc te {wall:6.2f}s  status={r.status:10s} "
            f"ok={str(r.ok):5s} obj={str(r.objective):>9s} vi pham={len(r.violations or []):2d}  "
            f"luot phan cong={sum(len(v) for v in (r.phan_cong or {}).values()):3d}"
        )

    print("\n== So sanh voi muc 60s lam chuan ==")
    base = next((x for x in rows if x["budget"] == 60.0), None)
    if base:
        for x in rows:
            if x["budget"] == 60.0:
                continue
            d_obj = (
                "n/a"
                if x["obj"] is None or base["obj"] is None
                else f"{x['obj'] - base['obj']:+d}"
            )
            same_status = "giong" if x["status"] == base["status"] else "KHAC"
            print(
                f"  {x['budget']:5.1f}s: nhanh hon {base['wall'] - x['wall']:6.2f}s  "
                f"status {same_status:5s}  chenh objective {d_obj:>8s}  "
                f"vi pham {x['viol']} vs {base['viol']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
