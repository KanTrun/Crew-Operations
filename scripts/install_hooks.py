#!/usr/bin/env python3
"""Cài đặt git hooks tự động cho repo NHỊP QUÁN.

Sao chép các hook từ `scripts/hooks/` (được version hoá trong repo) vào
`.git/hooks/` và đặt quyền thực thi. Chạy lại bất cứ lúc nào để cập nhật.

Sử dụng:
    python scripts/install_hooks.py

Các hook được cài:
  - pre-commit: ruff + secret scan (nhanh, chặn commit lỗi)
  - pre-push:   toàn bộ review (ruff + secret + mypy + tsc + pytest, chặn push lỗi)

Bỏ qua hook tạm thời:
  - git commit --no-verify
  - git push --no-verify
  - SKIP_PRE_PUSH=1 git push   (chỉ pre-push)
"""

from __future__ import annotations

import shutil
import stat
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
HOOKS_SRC = ROOT / "scripts" / "hooks"
HOOKS_DST = ROOT / ".git" / "hooks"

HOOKS = ["pre-commit", "pre-push"]


def main() -> int:
    if not HOOKS_DST.is_dir():
        print(f"❌ Không tìm thấy thư mục git hooks: {HOOKS_DST}")
        print("   Đảm bảo bạn đang ở trong repo git (đã `git init` hoặc clone).")
        return 1

    installed = []
    for hook in HOOKS:
        src = HOOKS_SRC / hook
        dst = HOOKS_DST / hook
        if not src.is_file():
            print(f"⚠️  Không tìm thấy hook nguồn: {src}")
            continue
        shutil.copy2(src, dst)
        # Đặt quyền thực thi (quan trọng trên Linux/macOS)
        dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        installed.append(hook)
        print(f"✅ Đã cài hook: {dst}")

    if not installed:
        print("❌ Không cài được hook nào.")
        return 1

    print("\n🎉 Đã cài xong git hooks:")
    for hook in installed:
        print(f"   - {hook}")
    print("\nTừ giờ, mỗi lần commit/push sẽ tự chạy review. Bỏ qua bằng:")
    print("   git commit --no-verify  |  git push --no-verify  |  SKIP_PRE_PUSH=1 git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())