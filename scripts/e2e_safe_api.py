#!/usr/bin/env python3
"""Khởi động API cho e2e Playwright với môi trường ĐÃ TRUNG HÒA kênh thật.

Lý do tồn tại: trên host có `.env` thật chứa token kênh sống và mạng KHÔNG bị
chặn. `ca_agents.llm.load_dotenv` dùng `override=False`, nghĩa là biến môi
trường tiến trình thắng `.env`. Launcher này nạp `.env.e2e` vào `os.environ`
TRƯỚC khi app chạy, nên mọi token kênh bị làm rỗng => `/channels/status` phải
báo `connected=false` cho zalo/telegram/facebook và `agent_mode=replay`.

Chỉ dùng cho kiểm thử. Không dùng cho vận hành quán thật.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_E2E = ROOT / ".env.e2e"

# `ca_api` và các package nằm trong `<pkg>/src`, không cài vào site-packages.
# Trước đây phải `import demo_api` để mượn side-effect thêm sys.path của nó;
# làm thẳng ở đây để không phụ thuộc side-effect ẩn.
for _p in (
    "apps/api",
    "packages/contracts",
    "packages/agents",
    "packages/solver",
    "packages/playbook",
    "packages/gates",
    "packages/opsengine",
):
    _duong_dan = str(ROOT / _p / "src")
    if _duong_dan not in sys.path:
        sys.path.insert(0, _duong_dan)


def _load_sanitized_env(path: Path) -> bool:
    """Nạp KEY=VALUE vào os.environ, GHI ĐÈ cả giá trị có sẵn (kể cả rỗng).

    Trả về False khi file không tồn tại: `.env.e2e` bị `.gitignore` (`.env*`)
    nên clone mới không có. An toàn không phụ thuộc file này — mọi token đã
    bị làm rỗng cứng trong `main()`, nên thiếu file vẫn chạy được.
    """
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, value = s.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            os.environ[key] = value
    return True


def main() -> int:
    if _load_sanitized_env(ENV_E2E):
        print(f"[e2e] đã nạp {ENV_E2E.name}")
    else:
        print(f"[e2e] không có {ENV_E2E.name} — dùng mặc định an toàn dựng sẵn")
    # Đảm bảo chắc chắn các token kênh rỗng ngay cả khi .env.e2e thiếu dòng nào.
    for k in (
        "NHIPQUAN_ZALO_OA_ACCESS_TOKEN",
        "NHIPQUAN_TELEGRAM_BOT_TOKEN",
        "NHIPQUAN_FB_PAGE_TOKEN",
        "FACEBOOK_PAGE_ACCESS_TOKEN",
        "NHIPQUAN_SMTP_HOST",
        "NHIPQUAN_SMTP_PASSWORD",
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "OPENROUTER_API_KEY",
        "OLLAMA_BASE_URL",
        "APIFY_TOKEN",
    ):
        os.environ[k] = ""
    os.environ["CA_AGENT_MODE"] = "replay"
    os.environ["NHIPQUAN_PAGE_MODE"] = "disconnected"
    os.environ["NHIPQUAN_FB_AUTO_SEND"] = "0"
    os.environ["NHIPQUAN_MSG_BACKEND"] = "console"
    # Ba khoá chỉ có trong `.env.e2e` — đặt mặc định để harness tự đủ khi thiếu file.
    os.environ.setdefault("NHIPQUAN_ALLOW_MSG_REPLAY", "1")
    os.environ.setdefault("NHIPQUAN_ZALO_ENABLED", "0")
    os.environ.setdefault("NHIPQUAN_PBKDF2_VONG", "1000")

    import uvicorn  # noqa: E402

    print("[e2e] sanitized env loaded — starting API on :8000", flush=True)
    uvicorn.run("ca_api.interfaces.http.main:app", host="127.0.0.1", port=8000)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
