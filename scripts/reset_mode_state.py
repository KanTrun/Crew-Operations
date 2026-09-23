"""Xoa trang thai mode do QUA TRINH DO cua toi tao ra, tra kv ve mac dinh fixture.

BOI CANH: khi tai hien vong doi mode, toi da `confirm` mot so mode (gio_cao_diem,
quan_yen_tinh) de kiem tra. Cac khoa kv do se ton tai mai va lam lech trang thai
ban dau cua moi lan chay e2e sau. Script nay xoa dung nhung khoa do.

Chi xoa khoa `experience_mode_*` — KHONG dung du lieu khac cua quan.

Chay: .venv\\Scripts\\python.exe scripts/reset_mode_state.py [--list]
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "quan.db"
FIXTURE = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "grand_experience" / "quanverse.json"


def fixture_state() -> dict[str, dict]:
    """Trang thai mode GOC doc tu chinh fixture — khong hardcode.

    Lan dau toi hardcode tap mode active va da SAI (ghi them gio_cao_diem,
    quan_yen_tinh trong khi fixture chi bat troi_mua). Doc thang tu fixture thi
    khong the lech khi fixture doi.
    """
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {m["mode"]: m for m in data.get("modes", [])}


MODE_KEYS = [f"experience_mode_{m}" for m in
             ("gio_cao_diem", "troi_mua", "khach_doan", "thieu_nhan_su", "quan_yen_tinh", "dem_nhac")]


def read() -> dict[str, dict | None]:
    cx = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    out: dict[str, dict | None] = {}
    for k in MODE_KEYS:
        row = cx.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        out[k] = json.loads(row[0]) if row else None
    cx.close()
    return out


def main() -> int:
    fix = fixture_state()
    before = read()
    print("== Trang thai mode TRUOC ==")
    for k, v in before.items():
        mode = k.removeprefix("experience_mode_")
        fx = fix.get(mode, {})
        fx_desc = f"fixture active={bool(fx.get('active'))}"
        if v:
            print(f"  {k:36} kv active={v.get('active')!r:6} proposal={v.get('proposal_status')!r:9} [{fx_desc}]")
        else:
            print(f"  {k:36} (khong co kv)                           [{fx_desc}]")

    if "--list" in sys.argv:
        return 0

    cx = sqlite3.connect(str(DB), timeout=30)
    deleted = 0
    for k, v in before.items():
        if not v:
            continue
        mode = k.removeprefix("experience_mode_")
        fx_active = bool(fix.get(mode, {}).get("active"))
        kv_active = bool(v.get("active"))
        has_proposal = bool(v.get("proposal_status"))
        # Xoa khi kv KHAC fixture va khong phai mot de xuat dang cho THAT SU
        # (de xuat that thi co proposal_status va khong active).
        stray_active = kv_active != fx_active
        stray_proposal = has_proposal and not kv_active
        if stray_active or stray_proposal:
            cx.execute("DELETE FROM kv WHERE k=?", (k,))
            deleted += 1
    cx.commit()
    cx.close()

    after = read()
    print(f"\n== Da xoa {deleted} khoa kv (tra ve trang thai fixture) ==")
    print("== Trang thai mode SAU ==")
    for k, v in after.items():
        if v:
            print(f"  {k:36} kv active={v.get('active')!r:6} proposal={v.get('proposal_status')!r}")
        else:
            print(f"  {k:36} (khong co kv -> dung fixture)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
