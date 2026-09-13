"""Quét secret trong các file sắp commit — chặn lộ token ra repo.

Chỉ in TÊN file + số dòng khớp, KHÔNG in giá trị khớp.
"""

from __future__ import annotations

import re
import subprocess
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


def doc_tolerant(p: Path) -> str:
    """Đọc file kể cả khi bị TRỘN encoding.

    PowerShell 5.1 `Out-File -Append` ghi UTF-16LE trong khi header có thể là
    utf8, nên decode thẳng theo một codec sẽ đọc sót nội dung. Bỏ byte null rồi
    decode latin-1 để regex vẫn thấy được chuỗi ASCII (token đều là ASCII).
    """
    return p.read_bytes().replace(b"\x00", b"").decode("latin-1", errors="replace")


def lay_file_da_stage() -> list[str]:
    """Lấy danh sách file đã `git add` — mặc định khi không truyền arg.

    Không có mặc định này thì chạy tay không arg sẽ quét 0 file và in
    `nghi_vu_lo_secret=0`, tức BÁO SẠCH GIẢ — nguy hiểm hơn là không quét.
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if out.returncode != 0:
        return []
    return [d for d in out.stdout.splitlines() if d.strip()]


def duong_dan_hien_thi(p: Path) -> str:
    """Đường ngắn gọn để in — KHÔNG crash khi file nằm ngoài repo.

    `relative_to(ROOT)` raise ValueError với file ở ổ đĩa/thư mục khác (ví dụ
    file tạm), khiến script chết và trả exit code 1. Exit 1 do CRASH bị nhầm
    với exit 1 do TÌM THẤY SECRET — tức một lỗi hiển thị có thể bị đọc thành
    "repo có secret". Bắt lỗi và in đường dẫn tuyệt đối thay thế.
    """
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def main() -> int:
    args = sys.argv[1:] or lay_file_da_stage()
    muc_tieu: list[Path] = []
    for arg in args:
        p = ROOT / arg
        if p.is_dir():
            muc_tieu.extend(sorted(p.rglob("*")))
        elif p.is_file():
            muc_tieu.append(p)

    muc_tieu = [
        p
        for p in muc_tieu
        if p.is_file() and p.suffix in {".py", ".yml", ".yaml", ".md", ".json", ".ts", ".tsx", ".cjs", ".log", ""}
    ]

    tong = 0
    if not muc_tieu:
        print("CANH_BAO khong co file nao duoc quet - ket qua 'sach' la VO NGHIA")
    for p in muc_tieu:
        try:
            text = doc_tolerant(p)
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for m in MAU.finditer(line):
                if BO_QUA.search(m.group(0)):
                    continue
                tong += 1
                print(f"NGHI_NGO {duong_dan_hien_thi(p)}:{i}")
    print(f"QUET {len(muc_tieu)} file -> nghi_vu_lo_secret={tong}")
    return 1 if tong else 0


if __name__ == "__main__":
    raise SystemExit(main())
