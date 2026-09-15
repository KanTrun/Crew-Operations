"""Log bằng chứng bị TRỘN encoding: header do `Out-File -Encoding utf8` ghi,
phần `-Append` lại dùng mặc định Unicode (UTF-16LE) của PowerShell 5.1.

Script này đọc tolerant (bỏ byte null, decode latin-1) để:
1. Trích đúng mã CVE/severity cho commit message — không dựa vào trí nhớ.
2. Báo cáo log nào bị trộn để còn chuẩn hoá.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
THU_MUC = ROOT / "plans" / "260913-1151-kiem-thu-toan-dien-v3"

MAU = re.compile(r"CVE-\d{4}-\d+|GHSA-[0-9a-z-]+|critical|high|moderate|low|next|postcss|sharp|vulnerab", re.I)


def doc_tolerant(p: Path) -> tuple[str, bool]:
    raw = p.read_bytes()
    tron = b"\x00" in raw  # dấu hiệu UTF-16
    return raw.replace(b"\x00", b"").decode("latin-1", errors="replace"), tron


def main() -> int:
    print("=== muc do tron encoding cua tung log ===")
    for p in sorted(THU_MUC.glob("*.log")):
        raw = p.read_bytes()
        print(f"  {p.name:34s} {len(raw):7d}B  utf16={'CO' if b'\x00' in raw else 'khong'}")

    print()
    print("=== audit-deps.log: dong chua CVE / severity ===")
    text, _ = doc_tolerant(THU_MUC / "audit-deps.log")
    for line in text.splitlines():
        s = line.strip()
        if s and MAU.search(s):
            print(f"  {s[:150]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
