"""Chung minh cong `audit_motion_tokens.py` that su bat duoc loi, khong phai luon xanh.

Bai hoc tu chinh phien lam viec nay: mot bai kiem thu chi co gia tri khi da chung
minh duoc no DO khi loi quay lai. Cong nay duoc viet sau khi da sua het loi, nen
neu chi chay mot lan va thay "0 vi pham" thi khong biet duoc no co bat duoc gi
khong — co the no dang xanh vi viet sai regex.

Cach lam: voi tung loai loi, tiem lai dung loi do vao mot tep tam trong
`apps/web/src/`, chay cong, doi no BAO DO, roi xoa di. Neu cong van xanh thi
chinh cong hong.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"
GATE = ROOT / "scripts" / "audit_motion_tokens.py"
PROBE = WEB_SRC / "ui" / "_probe_motion_gate.tsx"


def run_gate() -> tuple[int, str]:
    r = subprocess.run(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), str(GATE)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
    )
    return r.returncode, (r.stdout or "") + (r.stderr or "")


CASES: list[tuple[str, str, str]] = [
    (
        "thoi luong khai bang so",
        """import { motion } from "framer-motion";
export function P() {
  return <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.42 }} />;
}
""",
        "thoi luong khai bang so",
    ),
    (
        "duong cong khai bang so",
        """import { motion } from "framer-motion";
export function P() {
  return <motion.div animate={{ opacity: 1 }} transition={{ ease: [0.22, 1, 0.36, 1] }} />;
}
""",
        "duong cong khai bang so",
    ),
    (
        "lo xo khai truc tiep",
        """import { motion } from "framer-motion";
export function P() {
  return <motion.div animate={{ opacity: 1 }} transition={{ type: "spring", stiffness: 250, damping: 25 }} />;
}
""",
        "lo xo khai bang so",
    ),
    (
        "vong lap vo han tu chay",
        """import { motion } from "framer-motion";
export function P() {
  return <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity }} />;
}
""",
        "vong lap vo han",
    ),
    (
        "thieu xu ly giam chuyen dong",
        """import { motion } from "framer-motion";
export function P() {
  return <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ type: "tween" }} />;
}
""",
        "KHONG xu ly giam chuyen dong",
    ),
]


def main() -> int:
    print("=== Buoc 0: cong phai XANH khi chua tiem loi ===")
    code, out = run_gate()
    print(f"  exit={code} {'[OK]' if code == 0 else '[X] cong dang do san'}")
    if code != 0:
        print(out)
        return 1
    print()

    failures = 0
    for i, (name, source, expect) in enumerate(CASES, 1):
        PROBE.write_text(source, encoding="utf-8")
        try:
            code, out = run_gate()
        finally:
            PROBE.unlink(missing_ok=True)

        caught = code != 0 and expect in out
        mark = "[OK]" if caught else "[X]"
        print(f"=== Buoc {i}: tiem loi '{name}' ===")
        print(f"  {mark} cong exit={code}, {'bat duoc' if caught else 'KHONG bat duoc'}")
        if not caught:
            failures += 1
            print("  --- ket qua cong ---")
            for line in out.splitlines():
                if line.strip():
                    print(f"  {line}")
        # Xac nhan tep tam da bi xoa, tranh de lai rac trong src/
        if PROBE.exists():
            print(f"  [X] tep tam con sot: {PROBE}")
            failures += 1
        print()

    print("=== Buoc cuoi: cong phai XANH lai sau khi xoa het loi tiem ===")
    code, out = run_gate()
    print(f"  exit={code} {'[OK]' if code == 0 else '[X]'}")
    if code != 0:
        failures += 1
        print(out)

    print()
    if failures:
        print(f"=== THAT BAI: {failures} truong hop cong khong lam dung viec ===")
    else:
        print(f"=== DAT: ca {len(CASES)}/{len(CASES)} loai loi deu bi bat, cong xanh lai sau khi xoa ===")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
