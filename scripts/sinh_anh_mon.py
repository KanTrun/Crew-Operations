#!/usr/bin/env python3
"""Sinh ảnh sản phẩm **tại máy**, tất định, không gọi mạng.

Bọc quanh `ca_api.services.menu_image` — phần vẽ nằm ở đó, đây chỉ là lớp dòng
lệnh để chạy vận hành. Nhờ vậy ảnh sinh từ CLI và ảnh phục vụ qua
`GET /api/v1/menu/{id}/anh` là **cùng một hàm vẽ**, không thể lệch nhau.

Vì sao sinh tại máy thay vì gọi API ảnh: xem ADR-019 và
`docs/THIRD_PARTY.md` — demo phải chạy khi rút mạng (§14.9), ngân sách 0 đồng, và
free tier cloud "dễ thu hồi".

Dùng:
    python scripts/sinh_anh_mon.py                 # sinh cho mọi món còn thiếu ảnh
    python scripts/sinh_anh_mon.py --force         # sinh lại tất cả
    python scripts/sinh_anh_mon.py --mon latte     # chỉ một món
    python scripts/sinh_anh_mon.py --kiem-tra      # kiểm, không ghi
    python scripts/sinh_anh_mon.py --tu-danh-muc   # lấy món từ data/seed/danh-muc.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DANH_MUC = ROOT / "data" / "seed" / "danh-muc.json"

for _p in (ROOT / "apps" / "api" / "src",):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _thu_muc_anh() -> Path:
    """Thư mục ảnh món. Tôn trọng `NHIPQUAN_DB` để test không ghi vào repo."""
    override = os.environ.get("NHIPQUAN_DB")
    if override:
        return Path(override).parent / "menu_images"
    return ROOT / "data" / "menu_images"


def _mon_tu_db() -> list[dict[str, object]]:
    """Danh mục món đang có trong quán (nguồn thật khi chạy vận hành)."""
    from ca_api.persist import menu_list

    return list(menu_list(gom_an=True))


def nap_mon(*, tu_danh_muc: bool, file: Path | None) -> list[dict[str, object]]:
    if tu_danh_muc or file:
        path = file or DANH_MUC
        if not path.exists():
            raise SystemExit(f"thiếu {path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        return list(raw.get("mon") or [])
    return _mon_tu_db()


def main() -> int:
    ap = argparse.ArgumentParser(description="Sinh ảnh sản phẩm tại máy (không cần mạng).")
    ap.add_argument("--force", action="store_true", help="sinh lại cả ảnh đã có")
    ap.add_argument("--mon", default="", help="chỉ sinh cho một mã món")
    ap.add_argument("--kiem-tra", action="store_true", help="chỉ kiểm, không ghi ảnh")
    ap.add_argument("--file", type=Path, default=None, help="danh mục khác (mặc định: DB)")
    ap.add_argument("--tu-danh-muc", action="store_true", help="lấy món từ data/seed/danh-muc.json")
    args = ap.parse_args()

    from ca_api.services.menu_image import ghi_anh

    mon = nap_mon(tu_danh_muc=args.tu_danh_muc, file=args.file)
    if args.mon:
        mon = [m for m in mon if str(m.get("id")) == args.mon]
        if not mon:
            print(f"không có món `{args.mon}`")
            return 1

    thu_muc = _thu_muc_anh()
    if args.kiem_tra:
        thieu = [str(m.get("id")) for m in mon if not (thu_muc / f"{m.get('id')}.png").exists()]
        print(f"Kiểm: {len(mon)} món, {len(thieu)} món thiếu ảnh.")
        if thieu:
            print("  thiếu: " + ", ".join(thieu[:12]) + ("…" if len(thieu) > 12 else ""))
        return 1 if thieu else 0

    ket_qua: list[dict[str, object]] = []
    for m in mon:
        dich = thu_muc / f"{str(m.get('id'))}.png"
        if dich.exists() and not args.force:
            continue
        ghi_anh(m, thu_muc)
        ket_qua.append(
            {
                "id": str(m.get("id")),
                "byte": dich.stat().st_size,
                "bam": hashlib.sha256(dich.read_bytes()).hexdigest()[:16],
            }
        )

    print(f"Ảnh sản phẩm: sinh {len(ket_qua)} ảnh vào {thu_muc}")
    for r in ket_qua[:8]:
        print(f"  {r['id']:24s} {r['byte']:>7,} byte  #{r['bam']}")
    if len(ket_qua) > 8:
        print(f"  … và {len(ket_qua) - 8} ảnh nữa")
    if not ket_qua:
        print("  (không có ảnh nào cần sinh — dùng --force để sinh lại)")
    print("Không gọi mạng. Chạy lại ra cùng byte.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
