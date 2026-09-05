"""Demo Script: Staff send availability in group chat -> AI Scheduling Agent automatically generates schedule."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add apps/api/src to python path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))

from ca_api.persist import (
    chat_conversation_get,
    chat_conversation_list_for_user,
    chat_message_create,
    chat_message_react,
    chat_messages_list,
    init_db,
    register,
)
from ca_api.services.chat_scheduler_agent import handle_scheduling_request


async def run_demo() -> None:
    print("=" * 70)
    print("🚀 DEMO: AI SCHEDULER AGENT TRONG NHÓM CHAT NHỊP QUÁN")
    print("=" * 70)

    init_db()
    conv_id = "conv_general_quan_01"

    from ca_api.persist import _conn

    def get_or_create_user(uname: str, name: str, role: str = "nhan_vien") -> str:
        with _conn() as cx:
            row = cx.execute("SELECT nv_id, status FROM users WHERE username = ?", (uname,)).fetchone()
            if row:
                nv_id = str(row[0])
                cx.execute("UPDATE users SET status = 'active' WHERE nv_id = ?", (nv_id,))
                cx.execute(
                    """
                    INSERT OR IGNORE INTO chat_participants(conversation_id, nv_id, role, status, joined_at)
                    VALUES (?,?,?,'active',strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                    """,
                    (conv_id, nv_id, role),
                )
                cx.execute("UPDATE chat_participants SET status = 'active' WHERE conversation_id = ? AND nv_id = ?", (conv_id, nv_id))
                return nv_id
        reg = register(uname, "password123", name)
        nv_id = reg["nv_id"]
        with _conn() as cx:
            cx.execute("UPDATE users SET role = ?, status = 'active' WHERE nv_id = ?", (role, nv_id))
            cx.execute(
                """
                INSERT OR IGNORE INTO chat_participants(conversation_id, nv_id, role, status, joined_at)
                VALUES (?,?,?,'active',strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                """,
                (conv_id, nv_id, role),
            )
            cx.execute("UPDATE chat_participants SET status = 'active' WHERE conversation_id = ? AND nv_id = ?", (conv_id, nv_id))
        return nv_id

    # 1. Đăng ký / chuẩn bị 4 nhân sự
    print("\n[BƯỚC 1] Khởi tạo tài khoản nhân sự & tham gia nhóm chung...")
    lan_id = get_or_create_user("lan_quanly", "Lan Quản Lý", "quan_ly")
    hoa_id = get_or_create_user("hoa_barista", "Hoa Barista", "nhan_vien")
    tuan_id = get_or_create_user("tuan_phucvu", "Tuấn Phục Vụ", "nhan_vien")
    minh_id = get_or_create_user("minh_order", "Minh Order", "nhan_vien")

    # Đảm bảo phòng chat đã khởi tạo
    conv = chat_conversation_get(conv_id)
    print(f"✅ Nhóm chat: {conv.get('display_name', 'Hội Quán Chung')} ({conv_id})")

    # 2. Lan Quản Lý mở lời yêu cầu nhân viên gửi lịch rảnh
    print("\n[BƯỚC 2] Lan Quản Lý nhắn vào nhóm kêu gọi gửi lịch rảnh...")
    msg1 = chat_message_create(
        conv_id=conv_id,
        sender_id=lan_id,
        content="Chào cả nhà, mọi người nhắn thời gian rảnh tuần tới vào nhóm để chốt lịch nhé!",
    )
    print(f"👩‍💼 [Lan Quản Lý]: {msg1['content']}")
    time.sleep(0.5)

    # 3. Hoa Barista gửi lịch rảnh
    print("\n[BƯỚC 3] Hoa Barista gửi thời gian rảnh...")
    msg2 = chat_message_create(
        conv_id=conv_id,
        sender_id=hoa_id,
        content="Tuần tới em rảnh sáng T2, T4, T6 và sáng CN nhé ạ!",
    )
    print(f"☕ [Hoa Barista]: {msg2['content']}")
    chat_message_react(msg2["id"], "ai_scheduler", "👍")
    print("   ↳ 🤖 [Agent Xếp Lịch 📅] đã thả cảm xúc: 👍 (Ghi nhận lịch rảnh)")
    time.sleep(0.5)

    # 4. Tuấn Phục Vụ gửi lịch rảnh
    print("\n[BƯỚC 4] Tuấn Phục Vụ gửi thời gian rảnh...")
    msg3 = chat_message_create(
        conv_id=conv_id,
        sender_id=tuan_id,
        content="Em Tuấn rảnh tối T2, T3, T5, T7, CN ạ",
    )
    print(f"🏃 [Tuấn Phục Vụ]: {msg3['content']}")
    chat_message_react(msg3["id"], "ai_scheduler", "👍")
    print("   ↳ 🤖 [Agent Xếp Lịch 📅] đã thả cảm xúc: 👍 (Ghi nhận lịch rảnh)")
    time.sleep(0.5)

    # 5. Minh Order gửi lịch rảnh
    print("\n[BƯỚC 5] Minh Order gửi thời gian rảnh...")
    msg4 = chat_message_create(
        conv_id=conv_id,
        sender_id=minh_id,
        content="Em Minh đăng ký rảnh chiều T3, T4, T5, T6 và sáng T7 ạ",
    )
    print(f"📝 [Minh Order]: {msg4['content']}")
    chat_message_react(msg4["id"], "ai_scheduler", "👍")
    print("   ↳ 🤖 [Agent Xếp Lịch 📅] đã thả cảm xúc: 👍 (Ghi nhận lịch rảnh)")
    time.sleep(0.5)

    # 6. Lan Quản Lý tag @agent_lich để xếp lịch
    print("\n[BƯỚC 6] Lan Quản Lý gọi AI Agent xếp lịch tuần...")
    msg5 = chat_message_create(
        conv_id=conv_id,
        sender_id=lan_id,
        content="@agent_lich tổng hợp thời gian rảnh của mọi người rồi xếp lịch tuần tới giúp quán nhé!",
    )
    print(f"👩‍💼 [Lan Quản Lý]: {msg5['content']}")
    print("\n⏳ AI Agent đang đọc dữ liệu tin nhắn và chạy thuật toán xếp ca tối ưu...")
    time.sleep(1)

    # 7. AI Scheduler Agent xử lý và tạo lịch
    bot_msg = await handle_scheduling_request(
        conv_id=conv_id,
        trigger_msg=msg5["content"],
        user_sess={"nv_id": lan_id, "role": "quan_ly", "store_id": "quan_01"},
    )

    print("\n" + "=" * 70)
    print("📅 [Agent Xếp Lịch 📅 ĐÃ PHẢN HỒI VÀO NHÓM CHAT]:")
    print("=" * 70)
    print(bot_msg["content"])
    print("\n[OPS CARD PROPOSAL ĐÍNH KÈM]:")
    print(f"• Tiêu đề: {bot_msg.get('metadata', {}).get('proposal', {}).get('title')}")
    print(f"• Tóm tắt: {bot_msg.get('metadata', {}).get('proposal', {}).get('summary')}")
    print(f"• Thao tác: Quản lý có thể mở Hộp thư duyệt trực tiếp để đưa vào lịch tuần!")
    print("=" * 70)
    print("🎉 DEMO HOÀN TẤT THÀNH CÔNG RỰC RỠ!")
    print("Mở giao diện Web tại http://localhost:3000/chat để thấy toàn bộ đoạn chat thực tế!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_demo())
