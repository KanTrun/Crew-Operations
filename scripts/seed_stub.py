"""Seed stub — thay bằng 25 NV / 21 ca / 8 tuần khi có dữ liệu quán."""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "seed"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "nhan_vien": [],
        "ca": [],
        "lich_su_tuan": [],
        "ghi_chu": "chưa có dữ liệu quán — điền sau Tuần 0",
    }
    path = OUT / "sample.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", path.name)


if __name__ == "__main__":
    main()
