#!/usr/bin/env python3
"""#1 nhóm A — tỉ lệ không cần sửa, 1 tuần demo fixture (W01).

Không phải đường cong W1→W8 (nhóm B).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed" / "sample.json"
OUT = ROOT / "docs" / "metrics-18-2.md"


def main() -> int:
    if not SEED.exists():
        print("MISSING seed", file=sys.stderr)
        return 2
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    week1 = next((w for w in seed.get("lich_su_8_tuan", []) if w.get("tuan") == 1), None)
    if not week1:
        print("no week 1 in lich_su_8_tuan", file=sys.stderr)
        return 2
    phan = week1.get("phan_cong") or {}
    total = sum(len(nvs) for nvs in phan.values())
    sua = [
        g
        for g in seed.get("ghi_nhan_sua", [])
        if str(g.get("ca_id") or "").startswith("w1_") and g.get("nguon") == "mo_phong_fixture"
    ]
    n_sua = len(sua)
    if total == 0:
        print("total decisions = 0", file=sys.stderr)
        return 2
    khong_can_sua = (total - n_sua) / total
    print(f"Demo W01 fixture: quyet_dinh={total} sua={n_sua} khong_can_sua={khong_can_sua:.1%}")
    block = f"""
## Override demo tuần 1 (nhóm A)

| Tuần | Quyết định | Bị sửa | Không cần sửa | Nguồn |
|------|------------|--------|---------------|-------|
| W01 | {total} | {n_sua} | {khong_can_sua:.1%} | `sample.json` `fixture` |

Đường cong W1→W8: **ngoài phạm vi bài thi** (nhóm B).
"""
    if OUT.exists():
        text = OUT.read_text(encoding="utf-8")
        if "## Override demo" in text:
            text = text.split("## Override demo")[0].rstrip()
        OUT.write_text(text + block + "\n", encoding="utf-8")
    else:
        OUT.write_text("# Metrics 18.2\n" + block + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
