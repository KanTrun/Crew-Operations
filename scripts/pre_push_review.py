#!/usr/bin/env python3
"""Cổng review tự động trước khi push (Pre-Push Review Gate).

Chạy toàn bộ chuỗi kiểm tra chất lượng ngay tại máy local TRƯỚC khi `git push`,
đảm bảo code không lỗi trước khi đẩy lên GitHub. Đây là "cổng an toàn" tương
đương CI nhưng chạy ở local, chặn push nếu bất kỳ bước nào fail.

Các bước kiểm tra (mô phỏng CI `ci.yml`):
  1. Ruff lint (Python)
  2. Secret scan (chặn lộ token/key ra repo)
  3. Mypy --strict (type check Python)
  4. tsc --noEmit (type check TypeScript web)
  5. Pytest (unit + integration, CA_AGENT_MODE=replay)

Sử dụng:
    python scripts/pre_push_review.py            # chạy đầy đủ
    python scripts/pre_push_review.py --fast     # chỉ lint + secret + type (nhanh)
    python scripts/pre_push_review.py --skip-web # bỏ qua tsc (khi không có node_modules)

Exit code: 0 = sẵn sàng push, 1 = có lỗi (chặn push).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "apps" / "web"

# Test files gọi MẠNG THẬT (API ngoài, webhook, scraping) — bị treo/fail khi
# mạng bị chặn ở máy local. Chúng vẫn chạy trên CI (có mạng). Pre-push LOẠI TRỪ
# để không treo, CI là gate cuối cho các test này.
NETWORK_TESTS = {
    "apps/api/tests/unit/test_apify_client.py",
    "apps/api/tests/unit/test_channels.py",
    "apps/api/tests/unit/test_channels_reflection_api.py",
    "apps/api/tests/unit/test_threads_apify_source.py",
    "apps/api/tests/unit/test_threads_google_bridge.py",
    "apps/api/tests/unit/test_tiktok_apify_source.py",
    "apps/api/tests/unit/test_tiktok_smart_fallback.py",
    "apps/api/tests/unit/test_trends_api.py",
    "apps/api/tests/unit/test_worker.py",
    "packages/agents/tests/test_camoufox_client.py",
    "packages/agents/tests/test_camoufox_source.py",
}


def run_step(name: str, cmd: list[str], env_extra: dict[str, str] | None = None,
             cwd: Path | None = None) -> bool:
    """Chạy một bước kiểm tra, trả True nếu thành công."""
    print(f"\n{'=' * 60}")
    print(f"👉 BẮT ĐẦU BƯỚC: {name}")
    print(f"   Lệnh: {' '.join(cmd)}")
    print(f"{'=' * 60}")

    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)

    try:
        result = subprocess.run(cmd, cwd=cwd or ROOT, env=env)
    except FileNotFoundError:
        print(f"\n❌ KHÔNG TÌM THẤY LỆNH: {cmd[0]} — bỏ qua bước này.")
        return True

    if result.returncode != 0:
        print(f"\n❌ THẤT BẠI ở bước: {name} (Exit code: {result.returncode})")
        return False
    print(f"\n✅ HOÀN TẤT THÀNH CÔNG: {name}")
    return True


def find_python() -> str:
    """Tìm Python 3.12+ (ưu tiên `py -3.12` nếu có)."""
    if sys.version_info >= (3, 12):  # noqa: UP036
        return sys.executable
    py_launcher = shutil.which("py")
    if py_launcher:
        try:
            res = subprocess.run(
                [py_launcher, "-3.12", "-c", "import sys; print(sys.executable)"],
                capture_output=True, text=True,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
    return sys.executable


def _has_xdist(python_cmd: str) -> bool:
    try:
        res = subprocess.run([python_cmd, "-c", "import xdist"], capture_output=True)
        return res.returncode == 0
    except Exception:
        return False


def _has_node_modules() -> bool:
    return (WEB_DIR / "node_modules").is_dir()


def _changed_files() -> list[str]:
    """Lấy danh sách file đã thay đổi so với origin/main (hoặc HEAD~1 nếu chưa có remote).

    Dùng để chỉ chạy test liên quan đến thay đổi (Cách 2 — nhanh hơn nhiều).
    """
    try:
        # Ưu tiên so với origin/main
        res = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            capture_output=True, text=True, cwd=ROOT,
        )
        if res.returncode == 0 and res.stdout.strip():
            return [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
    except Exception:
        pass
    try:
        # Fallback: so với commit trước
        res = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, cwd=ROOT,
        )
        if res.returncode == 0 and res.stdout.strip():
            return [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
    except Exception:
        pass
    return []


def _map_changed_to_tests(changed: list[str]) -> list[str]:
    """Ánh xạ file đã đổi sang test files liên quan.

    Quy tắc (chỉ chạy test file CỤ THỂ, không chạy toàn bộ thư mục để tránh
    test mạng gây treo):
    - File test đã đổi → chính nó.
    - File trong `packages/*/src/` → KHÔNG map sang toàn bộ `packages/*/tests`
      (tránh chạy test mạng). Chỉ chạy test file đã đổi trực tiếp.
    - File trong `apps/api/src/` → bỏ qua (CI chạy đầy đủ test API).
    - File web/tsx/ts → không có test Python (bỏ qua).
    """
    tests: set[str] = set()
    for f in changed:
        p = Path(f)
        # File test đã đổi → chạy chính nó
        if "tests" in p.parts and p.suffix == ".py":
            tests.add(f)
    return sorted(tests)


def main() -> int:
    python_cmd = find_python()
    print(f"🐍 Sử dụng Python runtime: {python_cmd}")

    fast_mode = "--fast" in sys.argv or os.environ.get("FAST_CI", "0").lower() in ("1", "true", "yes")
    skip_web = "--skip-web" in sys.argv or os.environ.get("SKIP_WEB", "0").lower() in ("1", "true", "yes")
    # Mypy mặc định là CẢNH BÁO (không chặn) — nhất quán với CI gốc chạy `mypy ... || true`.
    # Dùng `--strict-mypy` để bắt buộc mypy phải xanh mới cho push.
    strict_mypy = "--strict-mypy" in sys.argv or os.environ.get("STRICT_MYPY", "0").lower() in ("1", "true", "yes")
    has_xdist = _has_xdist(python_cmd)

    steps: list[tuple[str, list[str], dict[str, str] | None, Path | None]] = [
        (
            "1. Ruff Linter Check",
            [python_cmd, "-m", "ruff", "check", "apps/api/src", "packages", "scripts"],
            None, None,
        ),
        (
            "2. Secret Scanner",
            [python_cmd, "scripts/scan_secrets_before_commit.py"],
            None, None,
        ),
        (
            "3. Mypy Type Check (strict)",
            [python_cmd, "-m", "mypy", "packages", "apps/api/src", "--ignore-missing-imports"],
            None, None,
        ),
    ]

    # TypeScript web (chỉ khi có node_modules)
    if not skip_web and _has_node_modules():
        steps.append((
            "4. TypeScript Check (tsc --noEmit)",
            ["npx", "tsc", "--noEmit"],
            None, WEB_DIR,
        ))
    elif not skip_web:
        print("⚠️  Bỏ qua tsc: chưa có apps/web/node_modules (chạy `cd apps/web && npm install`).")

    # Pytest — Cách 2: chỉ chạy test liên quan đến thay đổi (nhanh hơn nhiều)
    changed = _changed_files()
    related_tests = _map_changed_to_tests(changed)
    print(f"\n📁 File đã thay đổi: {len(changed)} → Test liên quan: {related_tests or '(không có)'}")

    if fast_mode:
        steps.append((
            "5. Fast Sanity & Architecture Tests",
            [
                python_cmd, "-m", "pytest",
                "packages/agents/tests/test_architecture.py",
                "packages/agents/tests/test_no_network.py",
                "packages/contracts/tests",
                "-q",
            ],
            {"CA_AGENT_MODE": "replay"}, None,
        ))
    elif related_tests:
        # Chỉ chạy test liên quan đến thay đổi, LOẠI TRỪ test mạng (tránh treo)
        filtered = [t for t in related_tests if t not in NETWORK_TESTS]
        if not filtered:
            print("   ⚠️  Chỉ có test mạng liên quan — bỏ qua pytest (CI sẽ chạy).")
        else:
            pytest_cmd = [python_cmd, "-m", "pytest", *filtered, "-q"]
            # Cách 1: xdist với worker giới hạn (tránh crash Windows)
            use_xdist = has_xdist and ("--xdist" in sys.argv or os.environ.get("XDIST", "0").lower() in ("1", "true", "yes"))
            if use_xdist:
                pytest_cmd.extend(["-n", "4"])
            steps.append((
                "5. Related Tests (Parallel)" if use_xdist else "5. Related Tests",
                pytest_cmd,
                {"CA_AGENT_MODE": "replay"}, None,
            ))
    else:
        # Không có test liên quan → chạy test nhanh mặc định
        steps.append((
            "5. Fast Sanity & Architecture Tests",
            [
                python_cmd, "-m", "pytest",
                "packages/agents/tests/test_architecture.py",
                "packages/agents/tests/test_no_network.py",
                "packages/contracts/tests",
                "-q",
            ],
            {"CA_AGENT_MODE": "replay"}, None,
        ))

    failed = False
    for name, cmd, env_extra, cwd in steps:
        ok = run_step(name, cmd, env_extra, cwd)
        # Mypy là cảnh báo (không chặn) trừ khi --strict-mypy
        if not ok and name.startswith("3. Mypy") and not strict_mypy:
            print("   ⚠️  Mypy có cảnh báo (không chặn push). Dùng `--strict-mypy` để bắt buộc xanh.")
            continue
        if not ok:
            failed = True
            break

    if failed:
        print("\n🚨 VUI LÒNG SỬA CÁC LỖI TRÊN TRƯỚC KHI PUSH CODE LÊN GITHUB!")
        print("   Chạy lại: python scripts/pre_push_review.py")
        return 1

    print("\n" + "🎉" * 20)
    print("✅ TOÀN BỘ CÁC BƯỚC KIỂM TRA ĐỀU ĐÃ XANH! CODE ĐÃ SẴN SÀNG ĐỂ PUSH!")
    print("🎉" * 20 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())