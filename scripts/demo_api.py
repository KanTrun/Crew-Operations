#!/usr/bin/env python3
"""Start API. Other terminal: cd apps/web && npm run dev"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

os.environ.setdefault("NHIPQUAN_PBKDF2_VONG", "1000")
os.environ.setdefault("NHIPQUAN_DISABLE_RATE_LIMIT", "true")
# BẮT BUỘC: không có biến này thì `persist.init_db()` KHÔNG tạo tài khoản demo, và
# dòng "Login lan / nhipquan" in bên dưới là SAI — đăng nhập sẽ trả 401
# `sai_thong_tin_dang_nhap` dù mật khẩu đúng như in. Đã xảy ra thật.
#
# `persist._demo_seed_enabled()` chỉ seed khi biến này bật, cố ý: cơ sở dữ liệu
# production không được tự nhồi tài khoản/menu/bàn minh hoạ. Script này là công cụ
# demo nên bật là đúng vai; `playwright.config.ts` cũng đặt y hệt cho webServer.
os.environ.setdefault("NHIPQUAN_SEED_DEMO", "1")

ROOT = Path(__file__).resolve().parents[1]
for p in [
    "apps/api",
    "packages/contracts",
    "packages/agents",
    "packages/solver",
    "packages/playbook",
    "packages/gates",
    "packages/opsengine",
]:
    sys.path.insert(0, str(ROOT / p / "src"))

if __name__ == "__main__":
    host = os.environ.get("NHIPQUAN_API_HOST", "0.0.0.0")
    port = int(os.environ.get("NHIPQUAN_API_PORT", "8000"))
    print(f"API http://{host}:{port}/health")
    print("Tai khoan demo (NHIPQUAN_SEED_DEMO=1):")
    print("  lan   / nhipquan  — quan_ly")
    print("  minh  / nhipquan  — nhan_vien")
    print("  hung  / nhipquan  — chu_quan")
    print("Mo http://localhost:3000/login")
    print("Web: cd apps/web && npm run dev")
    uvicorn.run("ca_api.interfaces.http.main:app", host=host, port=port)
