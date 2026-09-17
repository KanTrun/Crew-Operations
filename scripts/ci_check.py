#!/usr/bin/env python3
"""Script kiểm tra chất lượng mã nguồn (CI Check) trước khi push.

Mô phỏng chính xác các bước kiểm tra của GitHub Actions:
1. Linter: ruff check trên toàn bộ mã nguồn
2. Secret Scan: kiểm tra an toàn, ngăn ngừa lộ lọt secret/token
3. Unit Test: chạy test suite với CA_AGENT_MODE=replay

Sử dụng:
    python scripts/ci_check.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, cmd: list[str], env_extra: dict[str, str] | None = None) -> bool:
    print(f"\n{'=' * 60}")
    print(f"👉 BẮT ĐẦU BƯỚC: {name}")
    print(f"   Lệnh: {' '.join(cmd)}")
    print(f"{'=' * 60}")

    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)

    result = subprocess.run(cmd, cwd=ROOT, env=env)
    if result.returncode != 0:
        print(f"\n❌ THẤT BẠI ở bước: {name} (Exit code: {result.returncode})")
        return False
    print(f"\n✅ HOÀN TẤT THÀNH CÔNG: {name}")
    return True


def find_python() -> str:
    if sys.version_info >= (3, 12):  # noqa: UP036
        return sys.executable
    import shutil
    py_launcher = shutil.which("py")
    if py_launcher:
        try:
            res = subprocess.run(
                [py_launcher, "-3.12", "-c", "import sys; print(sys.executable)"],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
    return sys.executable


def _has_xdist(python_cmd: str) -> bool:
    try:
        res = subprocess.run(
            [python_cmd, "-c", "import xdist"],
            capture_output=True,
        )
        return res.returncode == 0
    except Exception:
        return False


def main() -> int:
    python_cmd = find_python()
    print(f"🐍 Sử dụng Python runtime: {python_cmd}")

    fast_mode = "--fast" in sys.argv or os.environ.get("FAST_CI", "0").lower() in ("1", "true", "yes")
    has_xdist = _has_xdist(python_cmd)

    steps = [
        (
            "1. Ruff Linter Check",
            [python_cmd, "-m", "ruff", "check", "apps/api/src", "packages", "scripts"],
            None,
        ),
        (
            "2. Secret Scanner",
            [python_cmd, "scripts/scan_secrets_before_commit.py"],
            None,
        ),
    ]

    if fast_mode:
        steps.append((
            "3. Fast Sanity & Architecture Tests",
            [
                python_cmd,
                "-m",
                "pytest",
                "packages/agents/tests/test_architecture.py",
                "packages/agents/tests/test_no_network.py",
                "packages/contracts/tests",
                "-q",
            ],
            {"CA_AGENT_MODE": "replay"},
        ))
    else:
        agents_cmd = [
            python_cmd,
            "-m",
            "pytest",
            "packages/agents/tests",
            "-q",
            "--ignore=packages/agents/tests/test_camoufox_source.py",
        ]
        if has_xdist:
            agents_cmd.extend(["-n", "auto"])

        steps.extend([
            (
                "3. Agents Test Suite (Parallel)" if has_xdist else "3. Agents Test Suite",
                agents_cmd,
                {"CA_AGENT_MODE": "replay"},
            ),
            (
                "4. API & Contracts Suite",
                [
                    python_cmd,
                    "-m",
                    "pytest",
                    "apps/api/tests",
                    "packages/contracts/tests",
                    "-q",
                ],
                {"CA_AGENT_MODE": "replay"},
            ),
        ])

    for name, cmd, env_extra in steps:
        if not run_step(name, cmd, env_extra):
            print("\n🚨 VUI LÒNG SỬA CÁC LỖI TRÊN TRƯỚC KHI PUSH CODE LÊN GITHUB!")
            return 1

    print("\n" + "🎉" * 20)
    print("✅ TOÀN BỘ CÁC BƯỚC KIỂM TRA CI ĐỀU ĐÃ XANH! CODE ĐÃ SẴN SÀNG ĐỂ PUSH!")
    print("🎉" * 20 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
