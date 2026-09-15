"""In CẤU TRÚC của `.env.e2e` — chỉ tên khoá và độ dài, KHÔNG in giá trị.

Dùng để quyết định file nào an toàn để commit mà không lộ secret ra log.
"""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    for ten in sys.argv[1:] or [".env.e2e"]:
        p = ROOT / ten
        print(f"=== {ten} ===")
        if not p.is_file():
            print("  KHONG_TON_TAI")
            continue
        co_gia_tri = []
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                print(f"  [comment] {s[:90]}")
                continue
            if "=" not in s:
                print(f"  [la] {s[:40]}")
                continue
            k, _, v = s.partition("=")
            v = v.strip().strip("'").strip('"')
            print(f"  {k.strip():38s} len={len(v):4d} {'CO_GIA_TRI' if v else '(rong)'}")
            if v:
                co_gia_tri.append(k.strip())
        print(f"  --> so khoa CO GIA TRI: {len(co_gia_tri)}")
        if co_gia_tri:
            print(f"  --> ten khoa: {co_gia_tri}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
