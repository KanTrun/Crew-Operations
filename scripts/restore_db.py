"""Khoi phuc data/quan.db va KIEM CHUNG bang integrity_check — khong doan.

BOI CANH: `quan.db` bi "database disk image is malformed". Nguyen nhan: khi khoi
phuc tu ban backup, toi da chep de `quan.db` nhung DE LAI `quan.db-wal` va
`quan.db-shm` cua mot THE HE KHAC (WAL sinh luc 12:51, backup chup luc 12:46).
SQLite coi `-wal` la phan mo rong cua chinh `quan.db`; ghep WAL cua database khac
vao lam trang thai khong nhat quan => malformed. Day KHONG phai loi ung dung.

Cach sua dung: xoa `-wal`/`-shm` TRUOC, roi moi dat `quan.db` vao, roi chay
`PRAGMA integrity_check`. Khong bao gio chep de `quan.db` khi con WAL cua the he cu.

Chay:  .venv\\Scripts\\python.exe scripts/restore_db.py [--from <file>] [--list]
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "quan.db"
BACKUPS = ROOT / "data" / "backups"


def check(path: Path) -> tuple[bool, str]:
    """Mo read-only va chay integrity_check. Tra (ok, thong diep)."""
    if not path.exists():
        return False, "khong ton tai"
    try:
        # uri=True + mode=ro: khong tao/ghi gi, khong dung WAL.
        cx = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10)
        try:
            row = cx.execute("PRAGMA integrity_check").fetchone()
            res = str(row[0]) if row else "?"
            n_tab = cx.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
            return res.lower() == "ok", f"integrity={res}  so bang={n_tab}"
        finally:
            cx.close()
    except sqlite3.DatabaseError as e:
        return False, f"DatabaseError: {e}"
    except Exception as e:  # pragma: no cover
        return False, f"{type(e).__name__}: {e}"


def main() -> int:
    args = sys.argv[1:]

    if "--list" in args:
        print("== Ban backup san co ==")
        ok, msg = check(DB)
        print(f"  {'OK ' if ok else 'HONG'}  data/quan.db  ({msg})")
        for p in sorted(BACKUPS.glob("*.db"), key=lambda x: -x.stat().st_mtime):
            ok, msg = check(p)
            size = p.stat().st_size / 1024
            print(f"  {'OK ' if ok else 'HONG'}  {p.name:38} {size:8.0f} KB  ({msg})")
        return 0

    src = DB
    if "--from" in args:
        src = Path(args[args.index("--from") + 1])
        if not src.is_absolute():
            src = BACKUPS / src

    print("== Truoc khi sua ==")
    ok, msg = check(DB)
    print(f"  {'OK ' if ok else 'HONG'}  {DB.name}  ({msg})")
    if ok and "--from" not in args:
        print("  => da tot, khong can khoi phuc.")
        return 0

    ok_src, msg_src = check(src)
    print(f"\n== Nguon khoi phuc ==\n  {'OK ' if ok_src else 'HONG'}  {src.name}  ({msg_src})")
    if not ok_src:
        print("\n  => Nguon HONG. Chay lai voi --list de chon ban khac.")
        return 1

    # Xoa WAL/SHM TRUOC — neu khong se tai dien dung loi vua roi.
    for suffix in ("-wal", "-shm"):
        p = Path(str(DB) + suffix)
        if p.exists():
            p.unlink()
            print(f"  da xoa {p.name} (WAL cua the he cu)")

    if src != DB:
        shutil.copy2(src, DB)
        print(f"  da chep {src.name} -> {DB.name}")

    ok2, msg2 = check(DB)
    print(f"\n== Sau khi sua ==\n  {'OK ' if ok2 else 'HONG'}  {DB.name}  ({msg2})")
    if not ok2:
        print("\n  => VAN HONG. Chay --list roi --from <ten file>.")
        return 1
    print("\n  => quan.db hop le, API co the khoi dong.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
