"""Tự kiểm tra 2 sửa đổi hậu báo cáo V3 (không đụng kênh thật, không xoá gì).

1. `e2e_safe_api._load_sanitized_env` phải trả về False (không SystemExit)
   khi thiếu `.env.e2e` — file đó bị gitignore nên clone mới không có.
2. `seed_professional_fixture.backup_db` phải tạo bản sao trước khi xoá DB,
   và trả về None khi DB chưa tồn tại.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

loi = 0


def kiem(label: str, ok: bool, chi_tiet: str = "") -> None:
    global loi
    print(f"{'PASS' if ok else 'FAIL'} {label} {chi_tiet}")
    if not ok:
        loi += 1


def test_load_sanitized_env_thieu_file() -> None:
    import e2e_safe_api as e

    try:
        ket_qua = e._load_sanitized_env(Path("KHONG_TON_TAI.env"))
    except SystemExit as exc:  # hành vi CŨ — harness chết trên clone mới
        kiem("thieu_env_e2e_khong_SystemExit", False, f"SystemExit({exc})")
        return
    kiem("thieu_env_e2e_tra_ve_False", ket_qua is False, f"ket_qua={ket_qua!r}")


def test_load_sanitized_env_co_file() -> None:
    import e2e_safe_api as e

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "env"
        f.write_text("# comment\nCA_AGENT_MODE=replay\n\nKHONG_CO_DAU=\n", encoding="utf-8")
        kiem("co_env_e2e_tra_ve_True", e._load_sanitized_env(f) is True)


def test_backup_db() -> None:
    import os

    import seed_professional_fixture as s

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "quan.db"
        os.environ["NHIPQUAN_DB"] = str(db)
        # DB chưa tồn tại -> không được tạo file rác, trả về None.
        kiem("backup_db_khong_DB_tra_ve_None", s.backup_db() is None)

        db.write_bytes(b"du-lieu-gia")
        duong_dan = s.backup_db()
        kiem("backup_db_tao_ban_sao", duong_dan is not None and duong_dan.is_file(), str(duong_dan))
        kiem(
            "backup_db_giu_nguyen_noi_dung",
            duong_dan is not None and duong_dan.read_bytes() == b"du-lieu-gia",
        )
        kiem("backup_db_khong_xoa_DB_goc", db.is_file())
        kiem(
            "backup_db_dat_trong_data_backups",
            duong_dan is not None and duong_dan.parent == ROOT / "data" / "backups",
            duong_dan.parent.name if duong_dan else "",
        )
        if duong_dan is not None:
            duong_dan.unlink()  # dọn bản sao thử nghiệm


if __name__ == "__main__":
    test_load_sanitized_env_thieu_file()
    test_load_sanitized_env_co_file()
    test_backup_db()
    print(f"SELF_TEST={'PASS' if loi == 0 else 'FAIL'} loi={loi}")
    raise SystemExit(1 if loi else 0)
