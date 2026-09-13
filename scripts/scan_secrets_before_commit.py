"""Quét secret trong các file sắp commit — chặn lộ token ra repo.

Chỉ in TÊN file + số dòng khớp, KHÔNG in giá trị khớp.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]

MAU = re.compile(
    r"EAAG[A-Za-z0-9]{20}"          # FB page token
    r"|EAA[A-Za-z0-9]{20}"          # FB access token
    r"|sk-[A-Za-z0-9]{20}"          # OpenAI/Groq
    r"|AIza[0-9A-Za-z_-]{30}"       # Google API key
    r"|ghp_[A-Za-z0-9]{30}"         # GitHub PAT
    r"|xox[baprs]-[A-Za-z0-9-]{10}"  # Slack
    r"|(?:token|secret|password|passwd|api_?key)\s*[:=]\s*['\"][A-Za-z0-9/+=_-]{16,}['\"]",
    re.I,
)

# Chuỗi khớp nhưng thực chất chỉ là TÊN khoá / giá trị test vô hại.
BO_QUA = re.compile(
    r"['\"](?:tok_test|secret_test|change-me|nhipquan|<[^>]*>|KHONG_[A-Z_]+)['\"]", re.I
)


def main() -> int:
    muc_tieu: list[Path] = []
    for arg in sys.argv[1:]:
        p = ROOT / arg
        if p.is_dir():
            muc_tieu.extend(sorted(p.rglob("*")))
        elif p.is_file():
            muc_tieu.append(p)

    muc_tieu = [p for p in muc_tieu if p.is_file() and p.suffix in {".py", ".yml", ".yaml", ".md", ".json", ".ts", ".tsx", ".cjs", ""}]

    tong = 0
    for p in muc_tieu:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for m in MAU.finditer(line):
                if BO_QUA.search(m.group(0)):
                    continue
                tong += 1
                print(f"NGHI_NGO {p.relative_to(ROOT).as_posix()}:{i}")
    print(f"QUET {len(muc_tieu)} file -> nghi_vu_lo_secret={tong}")
    return 1 if tong else 0


if __name__ == "__main__":
    raise SystemExit(main())
