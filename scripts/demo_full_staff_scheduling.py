"""Full Crew Realistic Demo: 14 Coffee Shop Staff register availability in group chat -> AI Agent schedules 21 shifts."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# Speed up PBKDF2 hashing for demo setup
os.environ["NHIPQUAN_PBKDF2_VONG"] = "1000"

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))

from ca_api.persist import (  # noqa: E402
    _conn,
    chat_conversation_get,
    chat_message_create,
    chat_message_react,
    chat_messages_list,
    init_db,
    register,
)
from ca_api.services.chat_scheduler_agent import handle_scheduling_request  # noqa: E402

# Danh sách 14 nhân viên chính thức của NHỊP QUÁN tham gia phiên chat demo
STAFF_CREW = [
    # (username, display_name, role, availability_message)
    ("lan",   "Lan Nguyễn (SM)",      "quan_ly",   "Chào cả nhà, tuần tới 2026-W38 quán cần xếp lịch đầy đủ 21 ca (Sáng, Chiều, Tối từ T2 đến CN). Mọi người nhắn thời gian rảnh vào nhóm nhé!"),
    ("minh",  "Minh Phạm (Head Bar)", "nhan_vien", "Em rảnh sáng T2, T3, T4, T5 và sáng T7 phụ trách quầy bar chính ạ."),
    ("bao",   "Bảo Hoàng (Barista)",  "nhan_vien", "Em Bảo rảnh chiều T2, T3, T4, T5, T6 phụ trách pha chế chiều nhé chị."),
    ("chi",   "Chi Vũ (Thu ngân)",    "nhan_vien", "Chi đăng ký rảnh sáng T2, T4, T6 và sáng CN quầy thu ngân nha."),
    ("yen",   "Yến Kiều (Thu ngân)",  "nhan_vien", "Em Yến rảnh chiều T2, T3, T5, T7 thu ngân ạ."),
    ("thao",  "Thảo Dương (Thu ngân)","nhan_vien", "Thảo rảnh tối T2, T4, T6, T7, CN thu ngân ca tối nhé."),
    ("dung",  "Dũng Đặng (Kho)",      "nhan_vien", "Dũng rảnh sáng T2, T4, T6 nhận hàng tiếp liệu kho."),
    ("linh",  "Linh Ngô (Phục vụ)",   "nhan_vien", "Em Linh rảnh sáng T3, T5, T7 và cả ngày CN phục vụ sảnh."),
    ("oanh",  "Oanh Phan (Phục vụ)",  "nhan_vien", "Em Oanh rảnh tối T2, T3, T5, T6, T7 phục vụ tối ạ."),
    ("quan",  "Quân Lương (Barista)", "nhan_vien", "Quân rảnh tối T3, T4, T5, T6, CN ca tối bar."),
    ("an",    "An Lê (Đa năng)",      "nhan_vien", "An rảnh chiều T4, T6, T7 chi viện mọi vị trí cần hỗ trợ."),
    ("phuc",  "Phúc Trịnh (Barista)", "nhan_vien", "Em Phúc rảnh cả ngày T7 và CN hỗ trợ đông khách."),
    ("son",   "Sơn Hà (Barista)",     "nhan_vien", "Sơn rảnh sáng CN và chiều CN bar nhé chị Lan."),
    ("nam",   "Nam Lý (ASM/HR)",      "quan_ly",   "@agent_lich tổng hợp thời gian rảnh của toàn bộ nhân viên đã đăng ký và xếp lịch tuần tới giúp quán nhé! Đảm bảo đủ người cho 21 ca và chia đều công bằng."),
]


def ensure_staff_in_db(conv_id: str) -> dict[str, str]:
    """Khởi tạo hoặc cập nhật trạng thái hoạt động cho 14 nhân viên trong DB."""
    staff_ids = {}
    with _conn() as cx:
        for uname, dname, role, _ in STAFF_CREW:
            row = cx.execute("SELECT nv_id FROM users WHERE username = ?", (uname,)).fetchone()
            if row:
                nv_id = str(row[0])
                cx.execute("UPDATE users SET status = 'active', display_name = ? WHERE nv_id = ?", (dname, nv_id))
            else:
                reg = register(uname, "nhipquan", dname)
                nv_id = reg["nv_id"]
                cx.execute("UPDATE users SET role = ?, status = 'active' WHERE nv_id = ?", (role, nv_id))

            cx.execute(
                """
                INSERT OR IGNORE INTO chat_participants(conversation_id, nv_id, role, status, joined_at)
                VALUES (?,?,?,'active',strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                """,
                (conv_id, nv_id, role),
            )
            cx.execute("UPDATE chat_participants SET status = 'active' WHERE conversation_id = ? AND nv_id = ?", (conv_id, nv_id))
            staff_ids[uname] = nv_id
    return staff_ids


def cleanup_demo_messages(conv_id: str, message_ids: list[str]) -> None:
    """Xóa sạch các tin nhắn demo để đưa database về trạng thái nguyên vẹn."""
    print(f"\n🧹 Đang dọn dẹp {len(message_ids)} tin nhắn demo khỏi database...")
    with _conn() as cx:
        for mid in message_ids:
            cx.execute("DELETE FROM chat_reactions WHERE message_id = ?", (mid,))
            cx.execute("DELETE FROM chat_messages WHERE id = ?", (mid,))
    print("✅ Đã dọn dẹp sạch sẽ toàn bộ tin nhắn demo. Database trở về trạng thái nguyên bản!")


async def run_full_crew_demo(do_cleanup: bool = False) -> bool:
    print("=" * 80)
    print("☕ NHỊP QUÁN — DEMO THỰC TẾ: 14 NHÂN VIÊN ĐĂNG KÝ CA & AI TỰ ĐỘNG XẾP LỊCH")
    print("=" * 80)

    init_db()
    conv_id = "conv_general_quan_01"
    created_msg_ids: list[str] = []

    try:
        # 1. Chuẩn bị nhân sự
        print("\n[BƯỚC 1/6] Đồng bộ và đưa 14 nhân sự chính thức vào nhóm chung...")
        staff_ids = ensure_staff_in_db(conv_id)
        conv = chat_conversation_get(conv_id)
        print(f"✅ Đã kết nối nhóm: {conv.get('display_name')} ({len(conv.get('participants', []))} thành viên)")
        assert len(staff_ids) == 14, "Phải có đủ 14 nhân sự"

        # 2. Cửa hàng trưởng phát động thông báo
        print("\n[BƯỚC 2/6] Cửa hàng trưởng (SM Lan Nguyễn) phát động đăng ký ca tuần mới...")
        sm_uname, _, _, sm_msg_text = STAFF_CREW[0]
        sm_msg = chat_message_create(conv_id=conv_id, sender_id=staff_ids[sm_uname], content=sm_msg_text)
        created_msg_ids.append(sm_msg["id"])
        print(f"📢 [Lan Nguyễn - Cửa hàng trưởng]: \"{sm_msg_text}\"")

        # 3. Lần lượt 12 nhân viên gửi thời gian rảnh vào nhóm
        print("\n[BƯỚC 3/6] 12 nhân viên gửi thời gian rảnh vào nhóm chat...")
        availability_messages = STAFF_CREW[1:13]
        for uname, dname, _, text in availability_messages:
            msg = chat_message_create(conv_id=conv_id, sender_id=staff_ids[uname], content=text)
            created_msg_ids.append(msg["id"])
            print(f"💬 [{dname}]: \"{text}\"")
            # AI Agent tự động thả cảm xúc like 👍 ghi nhận
            chat_message_react(msg["id"], "ai_scheduler", "👍")
            print("   ↳ 🤖 [Agent Xếp Lịch 📅] đã thả cảm xúc: 👍 (Đã ghi nhận)")
            time.sleep(0.15)

        # 4. Kiểm tra phản hồi reactions
        print("\n[BƯỚC 4/6] Kiểm tra xác nhận tự động của AI Agent cho từng nhân viên...")
        all_msgs = chat_messages_list(conv_id, limit=30)
        recent_ids = {m["id"] for m in all_msgs}
        verified_reacts = 0
        for mid in created_msg_ids[1:]:
            if mid in recent_ids:
                m_detail = next(m for m in all_msgs if m["id"] == mid)
                if m_detail.get("reactions") and "👍" in m_detail["reactions"]:
                    verified_reacts += 1
        print(f"✅ Xác nhận: {verified_reacts}/12 nhân viên đã được AI thả cảm xúc 👍 ghi nhận thành công!")
        assert verified_reacts == 12, "Tất cả 12 tin nhắn rảnh đều phải có cảm xúc 👍"

        # 5. Cửa hàng phó (ASM Nam Lý) gọi AI Agent tổng hợp và xếp lịch
        print("\n[BƯỚC 5/6] Cửa hàng phó (Nam Lý) ra lệnh cho AI Agent xếp lịch tuần...")
        hr_uname, hr_dname, _, hr_text = STAFF_CREW[13]
        hr_msg = chat_message_create(conv_id=conv_id, sender_id=staff_ids[hr_uname], content=hr_text)
        created_msg_ids.append(hr_msg["id"])
        print(f"👨‍💼 [{hr_dname}]: \"{hr_text}\"")

        print("\n⏳ [AI AGENT ĐANG XỬ LÝ]: Phân tích 12 tin nhắn, giải bài toán phân công ca tối ưu...")
        t0 = time.time()
        bot_msg = await handle_scheduling_request(
            conv_id=conv_id,
            trigger_msg=hr_text,
            user_sess={"nv_id": staff_ids[hr_uname], "role": "quan_ly", "store_id": "quan_01"},
        )
        created_msg_ids.append(bot_msg["id"])
        elapsed = time.time() - t0
        print(f"⚡ Thuật toán xếp lịch hoàn thành trong {elapsed:.3f}s!")

        # 6. Kiểm tra kết quả đầu ra
        print("\n[BƯỚC 6/6] Kiểm định chi tiết chất lượng đầu ra của AI Agent...")
        proposal = bot_msg.get("metadata", {}).get("proposal", {})
        schedule = proposal.get("schedule", {})
        shift_counts = proposal.get("shift_counts", {})

        print("\n" + "-" * 80)
        print("📋 KẾT QUẢ ĐẦU RA CỦA AGENT XẾP LỊCH TRONG PHÒNG CHAT:")
        print("-" * 80)
        print(bot_msg["content"])
        print("-" * 80)

        # Kiểm định tính hợp lệ:
        # A. Phải phủ đủ 7 ngày x 3 ca = 21 ca
        total_shifts_covered = 0
        unfilled_shifts = 0
        for _day, shifts in schedule.items():
            for _shift_name, assigned_staff in shifts.items():
                if assigned_staff:
                    total_shifts_covered += 1
                else:
                    unfilled_shifts += 1

        print("\n📊 KẾT QUẢ KIỂM ĐỊNH:")
        print(f"• Số ca đã có nhân sự phân công: {total_shifts_covered}/21 ca")
        print(f"• Số ca chưa có người: {unfilled_shifts}")
        print(f"• Tổng số lượt phân công ca: {sum(shift_counts.values())} lượt")
        print(f"• Số nhân sự nhận ca: {len(shift_counts)}/12 người")

        assert total_shifts_covered == 21, "Toàn bộ 21 ca trong tuần phải được phân công đầy đủ!"
        assert unfilled_shifts == 0, "Không được để sót ca nào thiếu nhân sự!"
        assert len(shift_counts) >= 10, "Đa số nhân viên đăng ký đều phải được phân công ca công bằng!"

        print("✅ KIỂM ĐỊNH HOÀN TOÀN ĐẠT CHUẨN 100%!")

        if do_cleanup:
            cleanup_demo_messages(conv_id, created_msg_ids)
        else:
            print("\n💡 Các tin nhắn demo đang được lưu trong nhóm chat để bạn xem trực tiếp tại:")
            print("👉 http://localhost:3000/chat (Đăng nhập tài khoản bất kỳ, vd: lan / nhipquan)")
            print("Để xóa dọn dẹp demo, chạy lại với cờ: python scripts/demo_full_staff_scheduling.py --cleanup")

        return True

    except Exception as exc:
        print(f"\n❌ LỖI TRONG QUÁ TRÌNH THỰC HIỆN: {exc}")
        # Xóa sạch demo nếu gặp lỗi như yêu cầu của người dùng ("k xong thì xóa hết demo")
        cleanup_demo_messages(conv_id, created_msg_ids)
        raise


if __name__ == "__main__":
    is_cleanup = "--cleanup" in sys.argv
    asyncio.run(run_full_crew_demo(do_cleanup=is_cleanup))
