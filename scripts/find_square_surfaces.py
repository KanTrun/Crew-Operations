"""Liệt kê các chỗ còn dùng chuỗi bề mặt vuông / bóng lệch cứng — NHỊP QUÁN.

Nguồn của cảm giác "toàn khung vuông như máy dựng" là hai chuỗi Tailwind trần
lặp đi lặp lại trong markup:
    border-2 border-[var(--nq-dim)]        → viền 2px, KHÔNG bo góc
    shadow-[Npx_Npx_0px_0px_var(--...)]    → bóng lệch cứng (kiểu brutalist)
Script này liệt kê chính xác từng chỗ còn lại để sửa theo lớp bề mặt chung
(`.nq-surface-*`, `.nq-cta`, `.nq-btn`), tránh sót.

Chạy:  python scripts/find_square_surfaces.py
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "apps" / "web" / "src"

PATTERNS: list[tuple[str, str]] = [
    (r"border-2\s+border-\[var", "viền 2px không bo góc"),
    (r"border-2\s+p-\d", "viền 2px không bo góc"),
    (r"shadow-\[\d+px_\d+px_0(?:px)?", "bóng lệch cứng (brutalist)"),
    (r"translate-[xy]-\[-\d+px\]", "dịch chuyển brutalist khi hover"),
    (r"rounded-none", "bo góc bị tắt"),
    (r"tracking-tighter", "siết khoảng chữ quá mức"),
]


def main() -> int:
    total = 0
    by_file: dict[str, list[str]] = {}
    for p in sorted(SRC.rglob("*.tsx")):
        rel = p.relative_to(SRC).as_posix()
        lines = open(p, encoding="utf-8").read().splitlines()
        hits: list[str] = []
        for i, line in enumerate(lines, 1):
            for pat, label in PATTERNS:
                if not re.search(pat, line):
                    continue
                # `rounded-full` = HINH TRON, khong phai khung vuong. Vien 2px quanh
                # mot cham trang thai 8-12px la dung (tao vanh tach cham khoi avatar),
                # khong phai loi bo goc. Neu khong loai, bo quet bao dong gia cho
                # moi cham hien dien.
                if "rounded-full" in line:
                    continue
                # Bo qua dong CHU THICH: mo ta "da bo tracking-tighter" khong phai
                # la dang dung no. Nhan biet: dong bat dau bang mo chu thich JSX
                # ({/* hoac *), hoac ten class nam trong backtick (cau van xuoi).
                stripped = line.strip()
                if stripped.startswith(("{/*", "*", "//")):
                    continue
                if re.search(r"`[^`]*tracking-tighter[^`]*`", line):
                    continue
                if "`." + "tracking-tighter" in line or "tighter`." in line:
                    continue
                hits.append(f"  {i:4}  [{label}]  {line.strip()[:96]}")
                break
        if hits:
            by_file[rel] = hits
            total += len(hits)

    print(f"== Chỗ còn dùng chuỗi vuông/brutalist: {total} ==")
    for rel, hits in sorted(by_file.items(), key=lambda kv: -len(kv[1])):
        print(f"\n{rel}  ({len(hits)})")
        for h in hits[:14]:
            print(h)

    out = ROOT / "data" / "out" / "square-surfaces.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    report = [f"{rel} ({len(h)})\n" + "\n".join(h) for rel, h in by_file.items()]
    out.write_text("\n\n".join(report) + f"\n\nTONG: {total}\n", encoding="utf-8")
    print(f"\nbáo cáo: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
