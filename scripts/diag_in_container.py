"""Test LLM + process_fb_message BÊN TRONG CONTAINER — tìm lỗi bị nuốt bởi except:pass."""

from __future__ import annotations

import asyncio
import os
import sys
import time
import traceback

sys.stdout.reconfigure(encoding="utf-8")

print("CA_AGENT_MODE =", os.environ.get("CA_AGENT_MODE", "(chưa set)"))
print("GROQ_API_KEY =", "CÓ" if os.environ.get("GROQ_API_KEY", "").strip() else "KHÔNG")
print("GEMINI_API_KEY =", "CÓ" if os.environ.get("GEMINI_API_KEY", "").strip() else "KHÔNG")
print("OPENROUTER_API_KEY =", "CÓ" if os.environ.get("OPENROUTER_API_KEY", "").strip() else "KHÔNG")
print("NHIPQUAN_FB_AUTO_SEND =", os.environ.get("NHIPQUAN_FB_AUTO_SEND", "(chưa set)"))
print("NHIPQUAN_PAGE_MODE =", os.environ.get("NHIPQUAN_PAGE_MODE", "(chưa set)"))
print("NHIPQUAN_FB_APP_SECRET =", "CÓ" if os.environ.get("NHIPQUAN_FB_APP_SECRET", "").strip() else "KHÔNG CÓ ← webhook thật sẽ bị 403!")
print()

# 1. Test LLM trực tiếp trong container
from ca_agents.llm import agent_mode, complete  # noqa: E402

print("agent_mode() =", agent_mode())
print()
print("Test complete() trực tiếp (timeout 10s)...")
try:
    t0 = time.perf_counter()
    res = complete(
        system="Bạn là nhân viên quán cà phê Việt Nam. Trả lời ngắn, tự nhiên, lễ phép.",
        user="Cho em xin menu với ạ",
        task="text",
        json_mode=False,
        timeout_s=10.0,
    )
    dt = time.perf_counter() - t0
    print(f"  ok={res.ok} provider={res.provider} reason={res.reason} ({dt:.2f}s)")
    print(f"  text={res.text[:150]!r}")
except Exception:
    print("  EXCEPTION:", traceback.format_exc()[-500:])

print()

# 2. Test process_fb_message end-to-end trong container
from ca_agents.ag_fbpage import FBMessageInput, process_fb_message  # noqa: E402

PUBLIC_CTX = {
    "profile": {
        "ten_quan": "Nhịp Quán",
        "gio_mo_cua": "07:00 - 22:30",
        "dia_chi": "123 Đường Cà Phê, P.5, Q.3",
        "hotline": "0901234567",
    },
    "menu": [
        {"ten": "Bạc xỉu", "gia": 32000, "gia_formatted": "32.000đ"},
        {"ten": "Cà phê muối", "gia": 38000, "gia_formatted": "38.000đ"},
    ],
    "promotions": [],
}


async def run() -> None:
    for label, text in [
        ("hỏi menu", "Cho em xin menu với ạ"),
        ("chào hỏi", "Chào quán ơi"),
        ("tự do", "Quán hôm nay có gì vui không ạ"),
    ]:
        msg = FBMessageInput(psid="diag_container", text=text, message_id=f"mid_diag_{label}", timestamp=0)
        t0 = time.perf_counter()
        out = await process_fb_message(msg, auto_respond_enabled=True, public_context=PUBLIC_CTX)
        dt = time.perf_counter() - t0
        print(f"[{label}] ({dt:.2f}s) action={out.action} intent={out.intent} agent={out.delegated_agent}")
        print(f"  response={(out.response or '')[:180]!r}")
        print(f"  suggested={(out.suggested_reply or '')[:120]!r}")
        print()


asyncio.run(run())
