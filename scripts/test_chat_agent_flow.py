#!/usr/bin/env python3
"""
End-to-end test script for Facebook AI Chatbot Agent.
Tests:
1. Token & Fanpage connectivity
2. AI Agent responses for various customer intents (hours, address, menu, promo, greeting, complaint)
3. Webhook simulation through API router
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for pkg in [
    "apps/api",
    "packages/contracts",
    "packages/agents",
    "packages/solver",
    "packages/playbook",
    "packages/gates",
    "packages/opsengine",
]:
    pkg_path = str(ROOT / pkg / "src")
    if pkg_path not in sys.path:
        sys.path.insert(0, pkg_path)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

from ca_agents.ag_fbpage import FBMessageInput, process_fb_message  # noqa: E402
from ca_agents.facebook_page import _page_id, _token, page_health  # noqa: E402
from ca_agents.llm import agent_mode  # noqa: E402
from ca_api.services.fb_moderation import fb_auto_send_enabled, moderate_fb_message  # noqa: E402
from ca_api.services.store_public_context import (  # noqa: E402
    get_active_promotions,
    get_public_menu,
    get_store_profile,
)


async def test_page_connection():
    print("=" * 60)
    print("1. KIỂM TRA KẾT NỐI FANPAGE & TOKEN")
    print("=" * 60)
    token = _token()
    page_id = _page_id()
    print(f"Token (prefix): {token[:20]}... (len={len(token)})")
    print(f"Page ID: {page_id}")
    print(f"Agent mode: {agent_mode()}")
    print(f"Auto send enabled: {fb_auto_send_enabled()}")

    health = page_health()
    print(f"Page Health: {health}")
    if health.get("ok"):
        print(f"✅ Kết nối Fanpage '{health.get('page_name')}' THÀNH CÔNG!")
    else:
        print(f"❌ Kết nối Fanpage thất bại: {health.get('detail')}")
    return health.get("ok", False)


async def test_ai_agent_scenarios():
    print("\n" + "=" * 60)
    print("2. KIỂM TRA AI AGENT XỬ LÝ CÁC TÌNH HUỐNG KHÁCH NHẮN")
    print("=" * 60)

    public_ctx = {
        "profile": get_store_profile(),
        "menu": get_public_menu(),
        "promotions": get_active_promotions(),
    }

    test_cases = [
        {
            "category": "Giờ mở cửa",
            "text": "Quán mở cửa mấy giờ vậy em?",
            "expected_intent": "hoi_gio_dia_chi",
        },
        {
            "category": "Địa chỉ",
            "text": "Địa chỉ quán mình ở đâu thế ad?",
            "expected_intent": "hoi_gio_dia_chi",
        },
        {
            "category": "Hỏi Menu / Món",
            "text": "Menu quán có những món gì em ơi?",
            "expected_intent": "hoi_menu_gia",
        },
        {
            "category": "Hỏi Giá món cụ thể",
            "text": "Cà phê sữa và bạc xỉu bao nhiêu tiền một ly?",
            "expected_intent": "hoi_menu_gia",
        },
        {
            "category": "Khuyến mãi",
            "text": "Bên mình đang có ưu đãi hay khuyến mãi gì không?",
            "expected_intent": "hoi_khuyen_mai",
        },
        {
            "category": "Chào hỏi",
            "text": "Chào shop, tư vấn giúp mình với",
            "expected_intent": "chao_hoi",
        },
        {
            "category": "Khiếu nại (De-escalation)",
            "text": "Hôm qua mình ghé quán uống cà phê phục vụ chậm và thái độ quá tệ!",
            "expected_intent": "khieu_nai_gop_y",
        },
    ]

    for idx, tc in enumerate(test_cases, 1):
        print(f"\n--- [Test #{idx}: {tc['category']}] ---")
        print(f"Khách nhắn: \"{tc['text']}\"")

        psid = f"test_customer_{idx}"
        # Step A: Moderation check
        mod = moderate_fb_message(
            psid=psid,
            text=tc["text"],
            message_id=f"mid_test_{idx}",
            timestamp=1726300000.0,
            public_context=public_ctx,
        )
        print(f"Policy Action: {mod.get('action')}, Lý do: {mod.get('reason')}")

        # Step B: Agent Squad processing
        msg_in = FBMessageInput(
            psid=psid,
            text=tc["text"],
            message_id=f"mid_test_{idx}",
            timestamp=1726300000.0,
        )
        out = await process_fb_message(
            msg_in,
            auto_respond_enabled=True,
            public_context=public_ctx,
        )

        print(f"Agent phụ trách: {out.delegated_agent}")
        print(f"Ý định nhận diện: {out.intent} (độ tin cậy: {out.confidence:.2f})")
        print(f"Hành động Agent: {out.action}")
        reply = out.response or out.suggested_reply or mod.get("response")
        print(f"🤖 Bot phản hồi:\n\"{reply}\"")


async def main():
    ok = await test_page_connection()
    if not ok:
        print("Dừng test do không kết nối được Page.")
        return
    await test_ai_agent_scenarios()
    print("\n" + "=" * 60)
    print("HOÀN TẤT KIỂM THỬ LUỒNG AI AGENT CHO FACEBOOK MESSENGER!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
