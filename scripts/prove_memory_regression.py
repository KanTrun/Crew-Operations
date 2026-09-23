"""Chung minh bai hoi quy `test_clear_spatial_state_dung_lai_kho_ky_uc` chiu tai.

Mot bai hoi quy viet sau khi da sua loi thi khong bao ve duoc gi neu no van XANH
khi loi quay lai. Cach kiem: tam tra ham ve ban cu (chi xoa bo dem tan suat),
chay bai test, doi no DO; roi khoi phuc va doi no XANH.

`try/finally` bao dam ham luon duoc khoi phuc du tien trinh bi ngat.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "apps" / "api" / "src" / "ca_api" / "interfaces" / "http" / "spatial_memory.py"
TEST = "apps/api/tests/unit/test_spatial_memory_api.py::test_clear_spatial_state_dung_lai_kho_ky_uc"

OLD_BODY = """def clear_spatial_state() -> None:
    with _LOCK:
        _USER_TS.clear()
"""


def run_test() -> tuple[int, str]:
    # Phải KẾ THỪA môi trường đầy đủ: lọc còn vài biến làm Windows không nạp được
    # `_overlapped` (WinError 10106) vì thiếu SYSTEMROOT — pytest chết ở bước
    # import chứ chưa tới bài test, và kết quả đọc ra sẽ là "đỏ" một cách vô nghĩa.
    import os

    env = dict(os.environ)
    env.update(
        {
            "CA_AGENT_MODE": "replay",
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    r = subprocess.run(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "pytest", TEST, "-q", "--no-header"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
        env=env,
    )
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    print("=== Buoc 0: voi ban sua HIEN TAI, bai test phai XANH ===")
    code, out = run_test()
    print(f"  exit={code} {'[OK] xanh' if code == 0 else '[X] do sai'}")
    if code != 0:
        print(out[-1200:])
        return 1

    original = TARGET.read_text(encoding="utf-8")
    print()
    print("=== Buoc 1: tiem ban CU (chi xoa bo dem, khong dung lai kho) ===")
    start = original.index("def clear_spatial_state() -> None:")
    end = original.index("\n\n", original.index("_REPO_STORE = None", start))
    patched = original[:start] + OLD_BODY + original[end + 2 :]

    try:
        TARGET.write_text(patched, encoding="utf-8")
        code, out = run_test()
        # Doi bai test DO. Chuoi duoi day chi xuat hien khi khang dinh that bai.
        caught = code != 0 and "consent song qua reset" in out
        print(f"  exit={code} {'[OK] bai test DO dung nhu mong doi' if caught else '[X] KHONG bat duoc'}")
        if not caught:
            print(out[-1200:])
            return 1
    finally:
        TARGET.write_text(original, encoding="utf-8")
        print("  da khoi phuc ban sua")

    print()
    print("=== Buoc 2: khoi phuc xong, bai test phai XANH lai ===")
    code, out = run_test()
    print(f"  exit={code} {'[OK] xanh lai' if code == 0 else '[X] van do'}")
    if code != 0:
        print(out[-1200:])
        return 1

    print()
    print("=== DAT: bai hoi quy DO khi loi quay lai, XANH khi loi da sua ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
