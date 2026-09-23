"""Doi `text-white` tren nen copper sang ink toi — sua tuong phan + nhat quan.

VI SAO: `#ffffff` tren `#c4a574` chi dat 2.34:1 (can 4.5). Day KHONG phai loi
trang tri: nut "Tat ca"/tab dang bat trong /chat va /page-quan gan nhu khong doc
duoc nhan. Token `--nq-accent-ink` (#14100c) dat 8.10:1 va da duoc he thong dung
o `.nq-ink-on-solid`, `.nq-btn-primary` — nen day la sua cho DUNG QUY UOC, khong
phai them ngoai le. `hover:brightness` giu nguyen hanh vi cu.

Sua bang script de lam duoc o MOI file tsx (ke ca file co dau tieng Viet) va de
kiem lai duoc so luong — sua tay 17 cho de sot.

Chay: .venv\\Scripts\\python.exe scripts/fix_white_on_copper.py [--dry]
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "apps" / "web" / "src"

# Chi doi khi `text-white` di LIEN NGAY sau nen copper — dung cap ngu ca.
PAIRS = [
    ("bg-[var(--nq-copper)] text-white ", "bg-[var(--nq-copper)] text-[var(--nq-accent-ink)] "),
    ('bg-[var(--nq-copper)] text-white"', 'bg-[var(--nq-copper)] text-[var(--nq-accent-ink)]"'),
    ("bg-[var(--nq-warn)] text-white ", "bg-[var(--nq-warn)] text-[var(--nq-accent-ink)] "),
    ('bg-[var(--nq-warn)] text-white"', 'bg-[var(--nq-warn)] text-[var(--nq-accent-ink)]"'),
    ("bg-[var(--nq-ok)] text-white ", "bg-[var(--nq-ok)] text-[var(--nq-accent-ink)] "),
    ('bg-[var(--nq-ok)] text-white"', 'bg-[var(--nq-ok)] text-[var(--nq-accent-ink)]"'),
    ('bg-[#27ae60] px-3 py-1 text-xs font-bold text-white',
     'bg-[var(--nq-ok)] px-3 py-1 text-xs font-bold text-[var(--nq-accent-ink)]'),
    ('bg-amber-600 px-4 py-2 text-xs font-bold text-white hover:bg-amber-500',
     'bg-[var(--nq-warn)] px-4 py-2 text-xs font-bold text-[var(--nq-accent-ink)] hover:brightness-110'),
    ('bg-emerald-600 px-4 py-1.5 text-xs font-bold text-white shadow-md hover:bg-emerald-500',
     'bg-[var(--nq-ok)] px-4 py-1.5 text-xs font-bold text-[var(--nq-accent-ink)] shadow-md hover:brightness-110'),
]


def main() -> int:
    dry = "--dry" in sys.argv
    files = sorted(p for p in SRC.rglob("*.tsx"))
    total = 0
    touched = 0
    for p in files:
        try:
            t = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"  BO QUA (khong phai UTF-8): {p}")
            continue
        orig = t
        n = 0
        for old, new in PAIRS:
            c = t.count(old)
            if c:
                t = t.replace(old, new)
                n += c
        if n:
            total += n
            touched += 1
            print(f"  {n:3d}  {p.relative_to(ROOT).as_posix()}")
            if not dry:
                p.write_text(t, encoding="utf-8")
        elif t != orig:  # pragma: no cover - phong khi encoding doi byte
            print(f"  !! {p} doi noi dung ngoai du kien")
    print(f"\nTONG: {total} cho trong {touched} file{' (DRY RUN)' if dry else ''}")
    if not dry and total:
        print("Kiem lai bang: node scripts/contrast.mjs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
