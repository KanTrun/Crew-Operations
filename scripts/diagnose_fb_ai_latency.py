"""Đo latency LLM live — xác minh timeout 3.5s trong process_fb_message có đủ không."""

from __future__ import annotations

import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "packages/agents/src")
sys.path.insert(0, "packages/contracts/src")

from ca_agents.llm import complete, load_dotenv  # noqa: E402

load_dotenv()

SYS = (
    "Bạn là nhân viên trực tin nhắn Fanpage của quán cà phê \"Nhịp Quán\".\n"
    "Tên của bạn khi xưng hô là \"em\", gọi khách là \"mình\".\n"
    "Trả lời ngắn gọn, tự nhiên, lễ phép tiếng Việt như nhân viên thật.\n"
    "Menu: Bạc xỉu 32k, Cà phê muối 38k, Trà đào cam sả 45k."
)

CASES = [
    "Cho em xin menu với ạ",
    "Chào quán ơi, quán mở cửa tới mấy giờ vậy ạ?",
    "Hôm nay quán có ưu đãi gì không em?",
]

for i, user in enumerate(CASES, 1):
    t0 = time.perf_counter()
    res = complete(system=SYS, user=user, task="text", json_mode=False, timeout_s=3.0)
    dt = time.perf_counter() - t0
    verdict = "ĐỦ (dưới 3.5s)" if dt < 3.5 else "VƯỢT TIMEOUT 3.5s → fallback template!"
    print(f"Case {i}: {dt:.2f}s provider={res.provider} ok={res.ok} → {verdict}")
    print(f"  text={res.text[:120]!r}")
    print()
