"""Seed stub — chỉ dựng `data/seed/sample.json` TRỐNG cho lần khởi tạo đầu.

Bộ sinh thật là `scripts/generate_fixture_data.py` (`make seed`), và bộ nạp 6 bề
mặt vận hành là `scripts/seed_operational.py` (`make seed-ops`).

Script này ghi một payload rỗng. Trước đây nó ghi đè vô điều kiện, nên ai gõ
nhầm `python scripts/seed_stub.py` là xoá sạch fixture ADR-012 (25 NV · 21 ca ·
8 tuần · 6 bề mặt vận hành) mà không cảnh báo gì. Giờ nó từ chối ghi đè lên
fixture đã có; muốn ghi đè thật thì thêm `--force`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "seed"


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "sample.json"
    if path.exists() and "--force" not in args:
        try:
            cu = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cu = {}
        if cu.get("nhan_vien"):
            print(
                f"bỏ qua: {path.name} đã có fixture "
                f"({len(cu['nhan_vien'])} nhân viên). "
                "Sinh lại bằng `python scripts/generate_fixture_data.py`, "
                "hoặc ép ghi rỗng bằng `--force`."
            )
            return 0
    payload = {
        "nhan_vien": [],
        "ca": [],
        "lich_su_tuan": [],
        "ghi_chu": "chưa có dữ liệu quán — điền sau Tuần 0",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
