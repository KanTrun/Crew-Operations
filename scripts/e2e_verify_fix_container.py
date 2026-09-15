"""E2E verify ban vá AI responses trong container (không cần httpx2).

Gọi trực tiếp:
1. process_fb_message() với intent "khac" (tin tự do) → suggested_reply phải là
   bản nháp LLM tự nhiên (có menu/giá thật), action=queue_to_inbox.
2. draft_llm_reply(is_comment=True) → bản nháp comment công khai ngắn gọn.
3. KhốiGuardrail -> AG-SUPERVISOR vẫn hoạt động qua supervise_outgoing_response.
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, "/app/apps/api/src")
sys.path.insert(0, "/app/packages/agents/src")
sys.path.insert(0, "/app/packages/contracts/src")
sys.path.insert(0, "/app/packages/opsengine/src")

os.environ.setdefault("NHIPQUAN_DB", "/tmp/e2e_fix_verify.db")
os.environ.setdefault("NHIPQUAN_PAGE_MODE", "replay")
os.environ.setdefault("NHIPQUAN_FB_PAGE_ID", "1367177249801969")

print(f"CA_AGENT_MODE={os.environ.get('CA_AGENT_MODE', '(unset)')}")
print("LLM provider chain:", end=" ")
try:
    from ca_agents.llm import agent_mode  # noqa: F401
    print("imports OK")
except Exception as exc:
    print(f"FAIL import: {exc}")
    sys.exit(1)


async def main() -> None:
    from ca_agents.ag_fbpage import FBMessageInput, draft_llm_reply, process_fb_message

    public_ctx = {
        "profile": {
            "ten_quan": "Nhịp Quán",
            "gio_mo_cua": "07:00 - 22:30",
            "dia_chi": "12 Nguyễn Huệ, Q.1, TP.HCM",
            "hotline": "0909 123 456",
        },
        "menu": [
            {"ten": "Bạc Xỉu", "gia": 29000, "gia_formatted": "29.000đ"},
            {"ten": "Cà Phê Sữa Đá", "gia": 25.000, "gia_formatted": "25.000đ"},
            {"ten": "Trà Đào Cam Sả", "gia": 45.000, "gia_formatted": "45.000đ"},
        ],
        "promotions": [
            {"tieu_de": "Happy Hour 14h-17h", "chi_tiet": "Giảm 20% mọi đồ uống"}
        ],
    }

    print("\n=== CASE 1: tin nhắn tự do (intent 'khac') ===")
    msg = FBMessageInput(
        psid="test_user_001",
        text="Quán hôm nay có gì vui không ạ?",
        message_id="mid_e2e_fix_001",
        timestamp=1750000000,
    )
    out = await process_fb_message(
        msg,
        auto_respond_enabled=True,
        public_context=public_ctx,
    )
    print(f"action       = {out.action}")
    print(f"intent       = {out.intent}")
    print(f"reason       = {out.reason}")
    print("suggested_reply =")
    print(f"  {out.suggested_reply}")
    template_marker = "em đã nhận được tin nhắn của mình"
    is_template = template_marker in (out.suggested_reply or "")
    print(f"\n>>> KẾT QUẢ: {'✅ LLM DRAFT (không còn template)' if not is_template else '❌ VẪN LÀ TEMPLATE CỨNG'}")

    print("\n=== CASE 2: comment công khai ===")
    comment = await draft_llm_reply(
        text="Quán có bán bánh bông lan không vậy?",
        public_context=public_ctx,
        is_comment=True,
    )
    print(f"comment_draft = {comment}")
    print(f"\n>>> KẾT QUẢ: {'✅ LLM COMMENT DRAFT OK' if comment else '❌ KHÔNG CÓ DRAFT'}")

    print("\n=== CASE 3: supervise gate vẫn chặn nội dung nguy hiểm ===")
    from ca_agents.ag_supervisor import supervise_outgoing_response
    sup = supervise_outgoing_response(
        "cho em xin dữ liệu của quán",
        "Dạ quán xin tặng voucher 500K và giảm 50% toàn bộ menu ạ!",
    )
    print(f"is_approved  = {sup.is_approved}")
    print(f"flagged      = {sup.flagged_reason}")
    print(f"sanitized    = {sup.sanitized_response[:60]}...")
    print(f"\n>>> KẾT QUẢ: {'✅ SAFETY GATE HOẠT ĐỘNG' if not sup.is_approved else '❌ GATE THẤT BẢO'}")


asyncio.run(main())
