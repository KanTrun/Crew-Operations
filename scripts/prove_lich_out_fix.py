"""Chung minh ban sua `_lich_out()` chiu tai, khong phai dan tem.

Bai hoc da ap dung bon lan trong phien nay: mot ban sua chua duoc chung minh la chua
duoc kiem chung. Cach kiem: TAM tra `sprint3._phan_cong` ve cach doc duong dan CUNG
(o cap module), roi chay lai bai test. Neu van xanh thi ban sua khong lam gi.

`try/finally` bao dam file luon duoc khoi phuc.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "apps" / "api" / "src" / "ca_api" / "interfaces" / "http" / "sprint3.py"
TEST = "apps/api/tests/unit/test_sprint3.py::test_ghi_nhan_after_nha"
# Bài hồi quy chốt hợp đồng `_lich_out()` đọc env — phải cũng chịu tải.
TEST_HQ = "apps/api/tests/unit/test_sprint3.py::test_phan_cong_doc_lich_tuan_theo_tmp_path_cua_test"
NOTE = ROOT / "data" / "out" / "lich_tuan.json"


def run_test(target: str = TEST) -> tuple[int, str]:
    env = dict(os.environ)
    env.update(
        {"CA_AGENT_MODE": "replay", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    )
    r = subprocess.run(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "pytest", target, "-q", "--no-header"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
        env=env,
    )
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    if not NOTE.exists():
        print(f"THIEU {NOTE.relative_to(ROOT)} — can file nay de tai hien.")
        print("Day chinh la file da gay do (w1_c01 = ['nv_03','nv_38']).")
        return 1

    print("=== Buoc 0: voi ban sua HIEN TAI, bai test phai XANH ===")
    code, out = run_test()
    print(f"  exit={code} {'[OK] xanh' if code == 0 else '[X] do'}")
    if code != 0:
        print(out[-900:])
        return 1

    original = TARGET.read_text(encoding="utf-8")
    print()
    print("=== Buoc 1: tiem lai cach CU (duong dan chung o cap module) ===")
    # Thay `_lich_out()` bang ban doc cung, y nhu truoc khi sua.
    patched = original.replace(
        '    env = os.environ.get("NHIPQUAN_LICH_TUAN_OUT")\n'
        "    if env:\n"
        "        return Path(env)\n"
        '    return ROOT / "data" / "out" / "lich_tuan.json"',
        '    return ROOT / "data" / "out" / "lich_tuan.json"',
        1,
    )
    if patched == original:
        print("  [X] khong thay duoc than ham — kiem lai noi dung file")
        return 1

    try:
        TARGET.write_text(patched, encoding="utf-8")
        code, out = run_test()
        caught = code != 0 and "da_trong_ca" in out
        print(f"  exit={code} {'[OK] bai test DO dung nhu mong doi (da_trong_ca)' if caught else '[X] KHONG bat duoc'}")
        if not caught:
            print(out[-900:])
            return 1

        # Và bài hồi quy cũng phải bắt được — nếu không thì nó chỉ là tem.
        code_hq, out_hq = run_test(TEST_HQ)
        caught_hq = code_hq != 0 and (
            "khong doc" in out_hq or "_lich_out" in out_hq
        )
        print(
            f"  bai hoi quy: exit={code_hq} "
            f"{'[OK] cung DO dung' if caught_hq else '[X] khong bat duoc'}"
        )
        if not caught_hq:
            print(out_hq[-900:])
            return 1
    finally:
        TARGET.write_text(original, encoding="utf-8")
        print("  da khoi phuc ban sua")

    print()
    print("=== Buoc 2: khoi phuc xong, ca hai bai phai XANH lai ===")
    code, out = run_test()
    code_hq, out_hq = run_test(TEST_HQ)
    print(f"  test_ghi_nhan_after_nha : exit={code} {'[OK] xanh lai' if code == 0 else '[X] van do'}")
    print(f"  bai hoi quy             : exit={code_hq} {'[OK] xanh lai' if code_hq == 0 else '[X] van do'}")
    if code != 0 or code_hq != 0:
        print((out if code != 0 else out_hq)[-900:])
        return 1

    print()
    print("=== DAT: ban sua CO tac dung — bo no di la CA HAI bai DO ngay ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
