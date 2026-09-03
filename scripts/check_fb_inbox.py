import sys

import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, r"d:\Crew-Operations\scripts")
from facebook_page_poster import FacebookPagePoster


def main():
    poster = FacebookPagePoster()
    token = poster.page_token
    page_id = poster.page_id
    base_url = poster.BASE_URL

    print(f"=== KIỂM TRA FANPAGE: '{poster.page_name}' (ID: {page_id}) ===")

    # 1. Kiểm tra Hộp thư Messenger
    print("\n📬 1. HỘP THƯ TIN NHẮN MESSENGER (/conversations):")
    conv_url = f"{base_url}/{page_id}/conversations"
    r_conv = requests.get(
        conv_url,
        params={
            "fields": "id,snippet,updated_time,message_count,unread_count,senders",
            "access_token": token,
        },
        timeout=15,
    )
    if r_conv.status_code == 200:
        convs = r_conv.json().get("data", [])
        print(f"   Tổng số cuộc hội thoại: {len(convs)}")
        if not convs:
            print("   ℹ️ Chưa có cuộc hội thoại tin nhắn nào.")
        for idx, c in enumerate(convs, 1):
            senders = [s.get("name", "Unknown") for s in c.get("senders", {}).get("data", [])]
            print(f"   [{idx}] Hội thoại ID: {c.get('id')}")
            print(f"       Người gửi: {', '.join(senders)}")
            print(f"       Nội dung gần nhất: {c.get('snippet')}")
            print(f"       Thời gian: {c.get('updated_time')}")
            print(f"       Tổng tin nhắn: {c.get('message_count')}, Chưa đọc: {c.get('unread_count')}")

            msgs_url = f"{base_url}/{c.get('id')}/messages"
            r_msgs = requests.get(
                msgs_url,
                params={"fields": "id,message,from,created_time", "limit": 5, "access_token": token},
                timeout=10,
            )
            if r_msgs.status_code == 200:
                msgs = r_msgs.json().get("data", [])
                for m in msgs:
                    sender_name = m.get("from", {}).get("name", "N/A")
                    print(f"         > {sender_name}: \"{m.get('message')}\" ({m.get('created_time')})")
    else:
        print(f"   ❌ Lỗi lấy tin nhắn: {r_conv.status_code} - {r_conv.text}")

    # 2. Kiểm tra Bình luận trên các bài viết
    print("\n💬 2. BÌNH LUẬN TRÊN CÁC BÀI VIẾT GẦN ĐÂY (/posts):")
    posts_url = f"{base_url}/{page_id}/posts"
    r_posts = requests.get(
        posts_url,
        params={
            "fields": "id,message,created_time,comments{id,message,from,created_time},reactions.summary(true)",
            "limit": 10,
            "access_token": token,
        },
        timeout=15,
    )
    if r_posts.status_code == 200:
        posts = r_posts.json().get("data", [])
        print(f"   Đã kiểm tra {len(posts)} bài viết gần nhất.")
        total_cmts = 0
        for p in posts:
            p_id = p.get("id")
            p_msg = (p.get("message") or "Bài đăng ảnh")[:45].replace("\n", " ")
            reactions_count = p.get("reactions", {}).get("summary", {}).get("total_count", 0)
            cmts = p.get("comments", {}).get("data", [])
            if cmts:
                print(f"\n   📌 Bài viết: \"{p_msg}...\" (Lượt thả tim: {reactions_count})")
                print(f"      ID: {p_id}")
                for c in cmts:
                    total_cmts += 1
                    author = c.get("from", {}).get("name", "Người dùng")
                    print(f"      💬 [{author}]: {c.get('message')} (Lúc: {c.get('created_time')})")
        if total_cmts == 0:
            print("   ℹ️ Hiện tại chưa có bình luận nào trên các bài viết gần đây.")
    else:
        print(f"   ❌ Lỗi lấy bài viết/bình luận: {r_posts.status_code} - {r_posts.text}")

if __name__ == "__main__":
    main()
