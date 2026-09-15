"""Chẩn đoán vì sao AG-FBPAGE trả lời theo mẫu thay vì LLM thông minh.

Chạy: python scripts/diagnose_fb_ai.py
Kết luận in ra màn hình từng bước: mode, keys, LLM live, process_fb_message.
"""

from __future__ import annotations

import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "packages/agents/src")
sys.path.insert(0, "packages/contracts/src")

import asyncio  # noqa: E402
import os  # noqa: E402

from ca_agents.llm import agent_mode, complete, load_dotenv, provider_status  # noqa: E402

load_dotenv()

print("=" * 60)
print("BƯỚC 1: CA_AGENT_MODE =", os.environ.get("CA_AGENT_MODE", "(chưa set)"))
print("agent_mode() =", agent_mode())
print()
print("BƯỚC 2: Provider keys có trong env?")
status = provider_status()
for name, ok in status.items():
    print(f"  {name:12s}: {'CÓ KEY' if ok else 'KHÔNG CÓ KEY'}")

print()
print("BƯỚC 3: Test LLM live trực tiếp (timeout 20s)...")
try:
    res = complete(
        system="Bạn là nhân viên quán cà phê. Trả lời ngắn gọn, tự nhiên tiếng Việt.",
        user="Cho em xin menu với ạ",
        task="text",
        json_mode=False,
        timeout_s=20.0,
    )
    print(f"  ok={res.ok} provider={res.provider} reason={res.reason}")
    print(f"  text={res.text[:200]!r}")
except Exception as exc:  # noqa: BLE001
    print(f"  LỖI NGOÀI EXPECTED: {exc!r}")

print()
print("BƯỚC 4: Test process_fb_message end-to-end (giống webhook thật)...")
from ca_agents.ag_fbpage import FBMessageInput, process_fb_message  # noqa: E402

PUBLIC_CTX = {
    "profile": {
        "ten_quan": "Nhịp Quán",
        "gio_mo_cua": "07:00 - 22:30",
        "dia_chi": "123 Đường Cà Phê, P.5, Q.3",
        "hotline": "0901234567",
        "wifi_ssid": "NhipQuan_Free",
        "wifi_pass": "nhipquan2026",
    },
    "menu": [
        {"ten": "Bạc xỉu", "gia": 32000, "gia_formatted": "32.000đ"},
        {"ten": "Cà phê muối", "gia": 38000, "gia_formatted": "38.000đ"},
        {"ten": "Trà đào cam sả", "gia": 45000, "gia_formatted": "45.000đ"},
    ],
    "promotions": [
        {"tieu_de": "Happy Hour", "chi_tiet": "Giảm 20% từ 14h-17h"}
    ],
}


async def run_case(label: str, text: str) -> None:
    msg = FBMessageInput(psid="test_psid_1", text=text, message_id="mid_test_1", timestamp=0)
    out = await process_fb_message(
        msg,
        auto_respond_enabled=True,
        public_context=PUBLIC_CTX,
    )
    print(f"  [{label}] text={text!r}")
    print(f"    action={out.action} intent={out.intent} conf={out.confidence} agent={out.delegated_agent}")
    print(f"    reason={out.reason}")
    print(f"    response={(out.response or '')[:150]!r}")
    print()


asyncio.run(run_case("hỏi menu", "Cho em xin menu với ạ"))
asyncio.run(run_case("tư vấn", "Em chưa biết uống gì, mình không uống được cà phê đắng"))
asyncio.run(run_case("thường", "Quán hôm nay có gì vui không"))
print("=" * 60)
print("Chẩn đoán xong. Nếu BƯỚC 3 ok=False → LLM không chạy được (key/hết quota).")
print("Nếu BƯỚC 3 ok=True nhưng BƯỚC 4 response giống template → lỗi ở pipeline.")
