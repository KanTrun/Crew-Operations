"""Kiểm chứng các thay đổi UI/UX đã thực sự nằm trong file — NHỊP QUÁN.

Vì sao cần script này: trong phiên làm việc, một lần revert working tree đã âm
thầm xoá nhiều sửa đổi (token, component, CSS) trong khi các sửa đổi khác vẫn
còn. Đọc lại code bằng mắt không phát hiện được kiểu mất mát đó — chỉ có kiểm
tra từng dấu hiệu kỳ vọng mới phát hiện.

Chạy:  python scripts/verify_ui_changes.py
Trả về exit 0 nếu mọi dấu hiệu đều có mặt.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"

# (file, [các chuỗi phải xuất hiện], mô tả)
EXPECTED: list[tuple[str, list[str], str]] = [
    ("src/app/globals.css", [
        "--nq-t-display:", "--nq-t-h1:", "--nq-t-h2:", "--nq-t-h3:", "--nq-t-body:",
        "--nq-t-small:", "--nq-t-caption:", "--nq-t-micro:", "--nq-t-num-lg:",
    ], "Thang chữ (10 bậc)"),
    ("src/app/globals.css", [
        "--nq-elev-0:", "--nq-elev-1:", "--nq-elev-2:", "--nq-elev-2-hover:", "--nq-elev-4:",
    ], "Bậc nổi (5 bậc)"),
    ("src/app/globals.css", [
        "--nq-st-ok:", "--nq-st-warn:", "--nq-st-danger:", "--nq-st-info:", "--nq-st-idle:",
        "--nq-st-ok-soft:", "--nq-st-warn-soft:", "--nq-st-danger-soft:", "--nq-st-info-soft:",
    ], "Màu trạng thái tách khỏi accent"),
    ("src/app/globals.css", [
        "--nq-beat-ack:", "--nq-beat-settle:", "--nq-beat-focus:", "--nq-beat-chapter:",
        "--nq-ease-inout:",
    ], "Ngôn ngữ chuyển động (nhịp)"),
    ("src/app/globals.css", ["--nq-line-control:"], "Biên ô nhập đạt WCAG 1.4.11"),
    ("src/app/globals.css", ["h3 {", "h4,"], "Thang chữ áp ở tầng thẻ"),
    ("src/app/globals.css", [".nq-chip--info", ".nq-chip--accent", ".nq-chip--dot"],
     "Chip trạng thái hợp nhất"),
    ("src/app/globals.css", [".nq-avatar", ".nq-roster-slot-crew", ".nq-roster-slot-head"],
     "Avatar trong ô lịch tuần"),
    ("src/app/globals.css", [".nq-landing", ".nq-login", ".nq-feature-tile",
                             ".nq-landing-footer"],
     "Nền mặt tiền + khối tính năng"),
    ("src/app/globals.css", ["var(--nq-elev-1), var(--nq-inner-hi)"],
     "Khối nội dung hạ xuống elev-1"),

    ("src/ui/kit.tsx", ["nq-chip${mod}", "nq-chip--info"], "StatusChip dùng hệ chip"),
    ("src/lib/roster.ts", ["export function initialsOf"], "Hàm viết tắt tên"),
    ("src/app/roster/RosterGrid.tsx", ["initialsOf", "nq-roster-slot-crew"],
     "Ô lịch dùng dải avatar"),
    ("src/ui/hom-nay/kpi-card.tsx", ["useHighlightTilt", "TILT_DEG"],
     "Nghiêng chỉ ở thẻ được đánh dấu"),
    ("tailwind.config.js", ["NHIP_QUAN_COLORS"], "Bảng màu gốc"),
    ("src/app/page.tsx", ["nq-landing", "nq-feature-tile", "nq-landing-footer"],
     "Mặt tiền dùng hệ bề mặt"),
    ("src/app/login/page.tsx", ["nq-login"], "Cửa vào dùng chung nền"),
]


def main() -> int:
    missing = 0
    total = 0
    lines: list[str] = []
    for rel, needles, label in EXPECTED:
        p = WEB / rel
        total += 1
        if not p.exists():
            lines.append(f"THIẾU FILE  {rel}  ({label})")
            missing += 1
            continue
        text = p.read_text(encoding="utf-8")
        gone = [n for n in needles if n not in text]
        if gone:
            lines.append(f"THIẾU       {rel}  ({label}) — không thấy: {', '.join(gone)}")
            missing += 1
        else:
            lines.append(f"OK          {rel}  ({label})")

    report = "\n".join(lines)
    out = ROOT / "data" / "out" / "verify-ui.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report + f"\n\nThiếu: {missing}/{total}\n", encoding="utf-8")
    for line in lines:
        print(line.encode("ascii", "replace").decode("ascii"))
    print(f"\nThieu: {missing}/{total}  (bao cao: {out})")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
