#!/usr/bin/env python3
"""
Seed Facebook Chatbot - Intent & Response Rules

Run this after migration to populate initial chatbot configuration.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


def seed_chatbot_data(db_path: Path = None) -> None:
    """Populate chatbot_intent and chatbot_response_rule tables."""
    
    if db_path is None:
        from ca_api.persist import db_path as get_db_path
        db_path = get_db_path()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    
    # Sample questions as JSON
    sample_questions_hours = json.dumps([
        "Mở mấy giờ?",
        "Các bạn đóng cửa lúc mấy giờ?",
        "Mở hôm nay không?",
        "Còn mở thêm không?"
    ], ensure_ascii=False)
    
    sample_questions_menu = json.dumps([
        "Các bạn có gì ngon?",
        "Giá cà phê bao nhiêu?",
        "Menu đầy đủ ở đâu?",
        "Có đồ ăn kèm không?",
        "Cà phê sữa giá bao nhiêu?"
    ], ensure_ascii=False)
    
    sample_questions_reservation = json.dumps([
        "Có thể đặt bàn được không?",
        "Tổ chức sinh nhật ở đây được không?",
        "Đặt 5 người hôm thứ sáu",
        "Phí tổ chức sự kiện bao nhiêu?"
    ], ensure_ascii=False)
    
    sample_questions_order = json.dumps([
        "Có thể giao hàng không?",
        "2 cà phê sữa, 1 trà đào",
        "Giao hàng tính phí không?",
        "Bao giờ giao?"
    ], ensure_ascii=False)
    
    sample_questions_feedback = json.dumps([
        "Cà phê quá lạnh",
        "Bạn phục vụ rất tốt!",
        "Tại sao phí giao hàng cao vậy?",
        "Có ý kiến gì tôi có thể góp",
        "Tôi muốn phàn nàn về..."
    ], ensure_ascii=False)
    
    sample_questions_payment = json.dumps([
        "Thanh toán bằng cách nào?",
        "Có chấp nhận thẻ tín dụng không?",
        "Thanh toán bằng ví điện tử được không?",
        "Có hoá đơn không?"
    ], ensure_ascii=False)
    
    # 1. Insert Intent Definitions
    intents = [
        ('hours_query', 'Hỏi giờ mở cửa', 'Khách hỏi giờ mở cửa/đóng cửa', sample_questions_hours, 0, 1),
        ('menu_query', 'Hỏi về menu', 'Hỏi về menu, giá cà phê, đồ ăn', sample_questions_menu, 0, 1),
        ('reservation', 'Đặt bàn/tổ chức sự kiện', 'Yêu cầu đặt bàn hoặc tổ chức sự kiện', sample_questions_reservation, 1, 0),
        ('order', 'Đặt hàng', 'Đặt hàng hoặc giao hàng', sample_questions_order, 1, 0),
        ('feedback', 'Góp ý/khiếu nại', 'Phản hồi, góp ý, hoặc khiếu nại', sample_questions_feedback, 1, 0),
        ('payment', 'Hỏi thanh toán', 'Hỏi về phương thức thanh toán', sample_questions_payment, 0, 1),
        ('other', 'Khác', 'Các câu hỏi khác không rõ ý định', json.dumps([], ensure_ascii=False), 0, 0),
    ]
    
    for intent_id, display_name, description, samples, requires_approval, auto_enabled in intents:
        cursor.execute("""
            INSERT OR REPLACE INTO chatbot_intent 
            (id, display_name, description, sample_questions, requires_approval, auto_response_enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (intent_id, display_name, description, samples, requires_approval, auto_enabled, now))
    
    # 2. Insert Response Rules
    rules = [
        # Hours
        ('rule_hours_1', 'hours_query', None, 
         '⏰ Quán mở 6h sáng - 22h tối hôm nay. Chúng tôi đóng cửa lúc 22h 🌙', 
         0.85, 1, 'nv_02'),
        
        # Menu
        ('rule_menu_1', 'menu_query', None,
         '☕ Menu của chúng tôi gồm: Cà phê đen, Cà phê sữa, Trà đào, Bạc xỉu. '
         'Xem chi tiết giá và món khác tại: [https://nhipquan.local/menu]',
         0.8, 1, 'nv_02'),
        
        # Payment
        ('rule_payment_1', 'payment', None,
         '💳 Chúng tôi chấp nhận: Tiền mặt, Chuyển khoản QR, Ví điện tử (Momo, ZaloPay, Viettel Pay). '
         'Có hoá đơn điện tử nếu cần!',
         0.85, 1, 'nv_02'),
        
        # Reservation - requires approval
        ('rule_reservation_1', 'reservation', None,
         '🎉 Cảm ơn bạn quan tâm! Chúng tôi sẽ liên hệ lại ngay để xác nhận chi tiết. '
         'Bạn có thể đặt tại: https://nhipquan.local/booking',
         0.7, 1, 'nv_02'),
        
        # Order - requires approval
        ('rule_order_1', 'order', None,
         '📦 Cảm ơn bạn! Đơn hàng của bạn đang được xử lý. '
         'Chúng tôi sẽ giao trong 30-45 phút. Phí giao hàng từ 15k. '
         'Vui lòng chờ xác nhận!',
         0.65, 1, 'nv_02'),
        
        # Feedback - requires approval
        ('rule_feedback_1', 'feedback', None,
         '❤️ Cảm ơn bạn đã góp ý! Đội ngũ của chúng tôi sẽ cải thiện dựa trên phản hồi của bạn. '
         'Chúng tôi rất trân trọng mỗi khách hàng!',
         0.75, 1, 'nv_02'),
    ]
    
    for rule_id, intent, condition, response, threshold, enabled, created_by in rules:
        cursor.execute("""
            INSERT OR REPLACE INTO chatbot_response_rule
            (id, intent, condition, response_template, confidence_threshold, enabled, created_by_nv_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (rule_id, intent, condition, response, threshold, enabled, created_by, now))
    
    # 3. Insert Knowledge Base Entries
    kb_entries = [
        ('kb_hours_1', 'hours', 'giờ mở cửa', 'Quán mở 6h sáng - 22h tối hàng ngày', 
         json.dumps(['config/tham-so-lao-dong.yaml'], ensure_ascii=False), 1.0, None),
        
        ('kb_menu_1', 'menu', 'danh sách đồ uống',
         'Menu đầy đủ: Cà phê đen, Cà phê sữa, Trà đào, Bạc xỉu, và các đồ uống khác',
         json.dumps(['data/menu_mon'], ensure_ascii=False), 0.95, 'menu_mon'),
        
        ('kb_payment_1', 'payment', 'phương thức thanh toán',
         'Chấp nhận: Tiền mặt, QR code, Ví điện tử (Momo, ZaloPay, Viettel Pay)',
         json.dumps(['SOP step 5'], ensure_ascii=False), 0.9, None),
        
        ('kb_delivery_1', 'order', 'giao hàng',
         'Hỗ trợ giao hàng trong vùng nội thành. Phí giao từ 15,000 VND. Thời gian giao 30-45 phút.',
         json.dumps(['SOP step 7'], ensure_ascii=False), 0.85, None),
        
        ('kb_reservation_1', 'reservation', 'đặt bàn',
         'Hỗ trợ đặt bàn cho nhóm hoặc tổ chức sự kiện. Liên hệ trước ít nhất 1 ngày.',
         json.dumps(['SOP step 3'], ensure_ascii=False), 0.8, None),
    ]
    
    for kb_id, category, key_phrase, content, sources, confidence, dynamic_table in kb_entries:
        cursor.execute("""
            INSERT OR REPLACE INTO chatbot_kb
            (id, category, key_phrase, content, sources, confidence, dynamic_from_table, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (kb_id, category, key_phrase, content, sources, confidence, dynamic_table, now))
    
    conn.commit()
    conn.close()
    
    print("✅ Chatbot seed data loaded successfully!")
    print(f"   - {len(intents)} intents created")
    print(f"   - {len(rules)} response rules created")
    print(f"   - {len(kb_entries)} knowledge base entries created")


if __name__ == '__main__':
    seed_chatbot_data()
