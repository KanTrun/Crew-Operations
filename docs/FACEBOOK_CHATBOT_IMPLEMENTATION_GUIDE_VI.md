# Facebook Chatbot - Hướng Dẫn Triển Khai (Từng Bước)

**Trạng thái:** Nền tảng sẵn sàng - Sẵn sàng cho Giai đoạn 1-2  
**Ngày:** 2026-08-30

---

## 📋 Tóm Tắt Nhanh

**Những gì đã được xây dựng:**
- ✅ Tài liệu kiến trúc toàn diện (ADR-014)
- ✅ Migration cơ sở dữ liệu (6 bảng mới với chỉ số)
- ✅ Script seed cho ý định + quy tắc phản hồi + FAQ
- ✅ Khung AG-FBPAGE
- ✅ Không cần RAG (cơ sở tri thức nhỏ, ổn định)

**Những gì còn lại (giai đoạn tiếp theo):**
- Triển khai webhook handler
- Engine quy tắc (ý định → khớp phản hồi)
- Logic phản hồi tự động
- Mở rộng UI phê duyệt của quản lý

---

## Giai đoạn 1: Thiết Lập Cơ Sở Dữ Liệu (1-2 giờ)

### Bước 1.1: Áp Dụng Migration

```bash
cd d:\Crew-Operations
python -m alembic upgrade head
```

Kết quả dự kiến:
```
INFO: Running upgrade 0002_... -> 0003_add_facebook_chatbot_tables
```

### Bước 1.2: Seed Dữ Liệu Ban Đầu

```bash
python scripts/seed_chatbot.py
```

Kết quả dự kiến:
```
✅ Dữ liệu seed chatbot được tải thành công!
   - Tạo 7 ý định
   - Tạo 6 quy tắc phản hồi
   - Tạo 5 mục cơ sở tri thức
```

### Bước 1.3: Xác Minh Bảng

```bash
sqlite3 data/quan.db ".schema chatbot"
```

Phải hiển thị:
```
chatbot_intent
chatbot_response_rule
chatbot_kb
chatbot_analytics
fb_conversation_thread
fb_message_log
```

### Bước 1.4: Xác Minh Dữ Liệu

```bash
sqlite3 data/quan.db "SELECT COUNT(*) as count FROM chatbot_intent"
# Output: 7
```

---

## Giai đoạn 2: Webhook Handler (2-4 giờ)

### Bước 2.1: Thêm Endpoint Webhook Facebook

**File:** `apps/api/src/ca_api/interfaces/http/channels.py`

Thêm endpoint này sau các handler Telegram/Zalo hiện có:

```python
@router.post("/api/v1/channels/webhook/facebook")
async def facebook_webhook(request: Request) -> dict[str, str]:
    """
    Facebook Messenger Platform webhook.
    
    Định dạng POST của Facebook:
    {
      "entry": [
        {
          "messaging": [
            {
              "sender": {"id": "<PSID>"},
              "message": {"mid": "<MID>", "text": "xin chào"}
            }
          ]
        }
      ]
    }
    """
    
    # Import cần thiết
    from ca_agents.ag_fbpage import parse_fb_webhook_message, process_fb_message
    
    try:
        body = await request.json()
    except Exception:
        # Facebook sẽ gửi lại nếu chúng ta không trả về 200
        return {"status": "ok"}
    
    # Xử lý từng mục nhập tin nhắn
    for entry in body.get("entry", []):
        messaging_data = entry.get("messaging", [])
        
        for msg_entry in messaging_data:
            # Bỏ qua các sự kiện không phải tin nhắn (delivery, read, v.v.)
            if "message" not in msg_entry:
                continue
            
            # Phân tích tin nhắn
            input_msg = await parse_fb_webhook_message(msg_entry)
            if not input_msg:
                continue
            
            try:
                # Xử lý không đồng bộ (fire and forget)
                await process_fb_message(input_msg)
            except Exception as e:
                # Ghi lại lỗi nhưng không làm cho phản ứng webhook thất bại
                _audit("fb_webhook", "error", {"error": str(e), "psid": input_msg.psid})
    
    # Luôn trả về 200 để xác nhận webhook
    return {"status": "ok"}


@router.get("/api/v1/channels/webhook/facebook/verify")
def facebook_webhook_verify(
    hub_mode: str = Query(None),
    hub_challenge: str = Query(None),
    hub_verify_token: str = Query(None)
) -> str:
    """
    Xác minh webhook Facebook Messenger (GET).
    
    Được sử dụng bởi Facebook để xác minh URL webhook trong quá trình thiết lập.
    """
    
    expected_token = os.getenv("NHIPQUAN_FB_WEBHOOK_VERIFY", "change-me")
    
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        return hub_challenge  # Trả lại challenge
    else:
        raise HTTPException(status_code=403, detail="verification_failed")
```

### Bước 2.2: Cấu Hình .env

```bash
# Tệp .env - thêm/cập nhật:

FACEBOOK_PAGE_ACCESS_TOKEN=<token_của_bạn_ở_đây>
FACEBOOK_PAGE_ID=1367177249801969
FACEBOOK_WEBHOOK_VERIFY=my-secret-verify-token
```

### Bước 2.3: Đăng Ký Webhook trong Ứng Dụng Facebook

1. Truy cập: https://developers.facebook.com/apps/
2. Chọn ứng dụng của bạn
3. Messenger → Cài đặt
4. Cuộn đến "Webhooks"
5. Nhấp "Chỉnh sửa Đăng ký"
6. Đặt:
   - **Callback URL:** `https://your-domain/api/v1/channels/webhook/facebook/verify`
   - **Verify Token:** `my-secret-verify-token` (phải khớp .env)
   - **Subscribe to:** ✅ messages ✅ messaging_postbacks
7. Nhấp "Verify and Save"

### Bước 2.4: Kiểm Tra Webhook

```bash
# Gửi tin nhắn kiểm tra đến trang
curl -X POST https://graph.facebook.com/v26.0/{PSID}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": {"id": "'$PSID'"},
    "message": {"text": "Xin chào từ bài kiểm tra!"},
    "access_token": "'$FB_TOKEN'"
  }'

# Kiểm tra nhật ký API
tail -f data/logs/api.log | grep "fb_webhook"
```

---

## Giai đoạn 3: Engine Quy Tắc Phản Hồi (2-3 giờ)

### Bước 3.1: Tạo Trình Khớp Quy Tắc

**File:** `packages/agents/src/ca_agents/ag_fbpage.py` (mở rộng)

```python
async def get_matching_rule(
    intent: str,
    confidence: float,
    conn: sqlite3.Connection
) -> dict[str, Any] | None:
    """
    Tìm quy tắc phản hồi phù hợp nhất cho ý định.
    
    Quy tắc được truy xuất từ bảng chatbot_response_rule.
    Trả về None nếu không tìm thấy quy tắc được bật.
    """
    
    cursor = conn.cursor()
    
    # Nhận quy tắc được bật cho ý định này, sắp xếp theo chi tiết
    cursor.execute("""
        SELECT id, response_template, confidence_threshold
        FROM chatbot_response_rule
        WHERE intent = ? AND enabled = 1
        ORDER BY confidence_threshold DESC
        LIMIT 1
    """, (intent,))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    rule_id, response_template, threshold = row
    
    return {
        "id": rule_id,
        "response": response_template,
        "threshold": threshold
    }


async def should_auto_respond(
    intent: str,
    confidence: float,
    rule: dict[str, Any] | None
) -> bool:
    """
    Quyết định nếu tin nhắn nên phản hồi tự động dựa trên:
    - Độ tin cậy của ý định
    - Ngưỡng quy tắc
    - Cài đặt ý định (yêu cầu phê duyệt)
    """
    
    if not rule:
        return False
    
    if confidence < rule["threshold"]:
        return False
    
    # Kiểm tra xem ý định có yêu cầu phê duyệt không
    from ca_api.persist import _conn
    cursor = _conn().cursor()
    cursor.execute(
        "SELECT requires_approval FROM chatbot_intent WHERE id = ?",
        (intent,)
    )
    row = cursor.fetchone()
    
    if row and row[0] == 1:
        return False  # Yêu cầu phê duyệt
    
    return True
```

### Bước 3.2: Mở Rộng process_fb_message

**File:** `packages/agents/src/ca_agents/ag_fbpage.py`

```python
async def process_fb_message(
    input_msg: FBMessageInput,
    *,
    confidence_threshold: float = 0.8,
    auto_respond_enabled: bool = True
) -> FBMessageOutput:
    """
    Triển khai đầy đủ của xử lý tin nhắn.
    """
    
    from ca_agents.ag_msg import classify
    from ca_agents.facebook_page import send_messenger_text
    from ca_api.persist import _conn, _now
    
    try:
        # 1. Phân loại ý định
        result = classify(input_msg.text, mode="live")
        
        # 2. Lấy quy tắc khớp
        rule = await get_matching_rule(
            result.intent,
            result.do_tin_cay,
            _conn()
        )
        
        # 3. Quyết định hành động
        should_auto = await should_auto_respond(
            result.intent,
            result.do_tin_cay,
            rule
        )
        
        if should_auto and auto_respond_enabled:
            # PHẢN HỒI TỰ ĐỘNG
            response_text = rule["response"]
            
            # Gửi qua Facebook
            send_result = await send_messenger_text(
                input_msg.psid,
                response_text
            )
            
            # Ghi vào cơ sở dữ liệu
            _log_fb_message(
                message_id=input_msg.message_id,
                psid=input_msg.psid,
                text=input_msg.text,
                intent=result.intent,
                confidence=result.do_tin_cay,
                was_auto_responded=True
            )
            
            return FBMessageOutput(
                action="auto_respond",
                response=response_text,
                intent=result.intent,
                confidence=result.do_tin_cay,
                reason=f"Độ tin cậy ý định {result.do_tin_cay:.2f} >= ngưỡng"
            )
        
        else:
            # XẾP HÀNG CHO PHÊ DUYỆT
            _enqueue_for_approval(
                message_id=input_msg.message_id,
                psid=input_msg.psid,
                text=input_msg.text,
                intent=result.intent,
                confidence=result.do_tin_cay
            )
            
            # Ghi vào cơ sở dữ liệu
            _log_fb_message(
                message_id=input_msg.message_id,
                psid=input_msg.psid,
                text=input_msg.text,
                intent=result.intent,
                confidence=result.do_tin_cay,
                was_auto_responded=False
            )
            
            reason = "Yêu cầu phê duyệt của con người"
            if not rule:
                reason = "Không có quy tắc phản hồi phù hợp"
            elif result.do_tin_cay < rule["threshold"]:
                reason = f"Độ tin cậy {result.do_tin_cay:.2f} < ngưỡng {rule['threshold']}"
            
            return FBMessageOutput(
                action="queue_to_inbox",
                response=None,
                intent=result.intent,
                confidence=result.do_tin_cay,
                reason=reason
            )
    
    except Exception as e:
        import traceback
        
        # Ghi lại lỗi
        _log_fb_message(
            message_id=input_msg.message_id,
            psid=input_msg.psid,
            text=input_msg.text,
            intent="error",
            confidence=0.0,
            was_auto_responded=False
        )
        
        return FBMessageOutput(
            action="error",
            response=None,
            intent="error",
            confidence=0.0,
            error=str(e)
        )
```

---

## Giai đoạn 4: Kiểm Tra & Xác Thực (1-2 giờ)

### Bước 4.1: Bài Kiểm Tra Đơn Vị

```python
# apps/api/tests/test_ag_fbpage.py

import pytest
from ca_agents.ag_fbpage import FBMessageInput, process_fb_message


@pytest.mark.asyncio
async def test_auto_respond_hours_query():
    """Kiểm tra phản hồi tự động cho truy vấn giờ mở cửa."""
    
    msg = FBMessageInput(
        psid="123456",
        text="mở mấy giờ?",  # Phải phân loại thành hours_query
        message_id="msg_001",
        timestamp=1234567890
    )
    
    result = await process_fb_message(msg)
    
    assert result.action == "auto_respond"
    assert result.intent == "hours_query"
    assert result.confidence > 0.8
    assert "6h" in result.response


@pytest.mark.asyncio
async def test_queue_for_approval_order():
    """Kiểm tra xếp hàng đơn đặt để phê duyệt."""
    
    msg = FBMessageInput(
        psid="123456",
        text="2 cà phê sữa, 1 trà đào",  # Phải phân loại thành order
        message_id="msg_002",
        timestamp=1234567890
    )
    
    result = await process_fb_message(msg)
    
    assert result.action == "queue_to_inbox"
    assert result.intent == "order"
    # Phải được xếp hàng vì order requires_approval=true


@pytest.mark.asyncio
async def test_low_confidence_queued():
    """Kiểm tra tin nhắn độ tin cậy thấp được xếp hàng."""
    
    msg = FBMessageInput(
        psid="123456",
        text="xyz abc random text",  # Phải có độ tin cậy thấp
        message_id="msg_003",
        timestamp=1234567890
    )
    
    result = await process_fb_message(msg)
    
    assert result.action == "queue_to_inbox"
    assert result.confidence < 0.8
```

### Bước 4.2: Kiểm Tra Thủ Công

```bash
# 1. Khởi động máy chủ API
cd apps/api
python -m uvicorn ca_api.main:app --reload --host 0.0.0.0 --port 8000

# 2. Trong terminal khác, kiểm tra endpoint webhook
curl -X POST http://localhost:8000/api/v1/channels/webhook/facebook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [
      {
        "messaging": [
          {
            "sender": {"id": "test_psid_123"},
            "message": {
              "mid": "msg_test_001",
              "text": "mở mấy giờ?"
            },
            "timestamp": 1693494169
          }
        ]
      }
    ]
  }'

# 3. Kiểm tra cơ sở dữ liệu cho tin nhắn đã ghi
sqlite3 data/quan.db "SELECT * FROM fb_message_log WHERE sender_id = 'test_psid_123'"
```

### Bước 4.3: Bài Kiểm Tra Tích Hợp

Gửi tin nhắn thực tế đến trang (qua Facebook Messenger):
```
Tin nhắn: "cà phê sữa bao nhiêu tiền?"
Dự kiến: Phản hồi tự động với giá
Kiểm tra: fb_message_log phải có mục với intent="menu_query"
```

---

## Giai đoạn 5: Mở Rộng Giao Diện Manager (2-3 giờ)

### Bước 5.1: Tạo Endpoint Inbox

**File:** `apps/api/src/ca_api/interfaces/http/channels.py`

```python
@router.get("/api/v1/page/fb-inbox")
def fb_inbox(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    """
    Lấy tin nhắn Facebook đang chờ phê duyệt.
    Tương tự /api/v1/inbox/rang-buoc nhưng cho tin nhắn FB.
    """
    
    role = _require_manager(authorization)
    
    with _conn() as cx:
        messages = cx.execute("""
            SELECT 
                m.id,
                t.psid,
                t.customer_name,
                m.text,
                m.intent_classified,
                m.intent_confidence,
                m.created_at
            FROM fb_message_log m
            JOIN fb_conversation_thread t ON m.thread_id = t.id
            WHERE t.status = 'open'
                AND m.intent_classified IN (
                    SELECT id FROM chatbot_intent 
                    WHERE requires_approval = 1
                )
            ORDER BY m.created_at DESC
            LIMIT 50
        """).fetchall()
    
    return {
        "items": [
            {
                "id": str(r[0]),
                "psid": str(r[1]),
                "customer_name": str(r[2]),
                "text": str(r[3]),
                "intent": str(r[4]),
                "confidence": float(r[5]),
                "created_at": str(r[6])
            }
            for r in messages
        ]
    }


@router.post("/api/v1/page/fb-inbox/{message_id}/approve")
def approve_fb_message(
    message_id: str,
    body: dict[str, str],  # {"response": "...phản hồi tùy chỉnh..."}
    authorization: Annotated[str | None, Header()] = None
) -> dict[str, Any]:
    """
    Manager phê duyệt và gửi phản hồi đến tin nhắn Facebook.
    """
    
    role = _require_manager(authorization)
    
    response_text = body.get("response", "")
    if not response_text:
        raise HTTPException(status_code=400, detail="response_required")
    
    # Lấy chi tiết tin nhắn
    with _conn() as cx:
        msg = cx.execute(
            "SELECT thread_id, sender_id FROM fb_message_log WHERE id = ?",
            (message_id,)
        ).fetchone()
    
    if not msg:
        raise HTTPException(status_code=404, detail="message_not_found")
    
    thread_id, psid = msg
    
    # Gửi qua Facebook
    from ca_agents.facebook_page import send_messenger_text
    send_messenger_text(psid, response_text)
    
    # Đánh dấu thread là đã giải quyết
    with _conn() as cx:
        cx.execute(
            "UPDATE fb_conversation_thread SET status = ? WHERE id = ?",
            ("resolved", thread_id)
        )
    
    _audit(role, "fb_inbox_approve", {"message_id": message_id})
    
    return {"ok": True}
```

---

## 🚀 Danh Sách Kiểm Tra Triển Khai

Trước khi đưa vào hoạt động:

- [ ] Migration cơ sở dữ liệu áp dụng thành công
- [ ] Dữ liệu seed được tải (7 ý định, 6 quy tắc)
- [ ] Endpoint webhook được triển khai
- [ ] URL webhook Facebook được cấu hình & xác minh
- [ ] Quy tắc phản hồi được kiểm tra thủ công
- [ ] Bài kiểm tra đơn vị đang vượt qua
- [ ] Giao diện manager được kiểm tra
- [ ] Xử lý lỗi đã được thực hiện
- [ ] Thủ tục rollback được ghi chép
- [ ] Đội được đào tạo về tính năng mới

---

## 📊 Giám Sát & Bảo Trì

### Kiểm Tra Hàng Ngày

```bash
# Kiểm tra lỗi webhook
sqlite3 data/quan.db "SELECT * FROM fb_message_log WHERE intent_classified = 'error' LIMIT 10"

# Kiểm tra thời gian phản hồi
sqlite3 data/quan.db """
  SELECT intent_classified, AVG(intent_confidence)
  FROM fb_message_log
  WHERE created_at > datetime('now', '-24 hours')
  GROUP BY intent_classified
"""

# Kiểm tra độ sâu hàng đợi phê duyệt
sqlite3 data/quan.db """
  SELECT COUNT(*) 
  FROM fb_conversation_thread 
  WHERE status = 'open'
"""
```

### Điều Chỉnh Ngưỡng

Nếu quá nhiều dương tính giả (phản hồi không chính xác):
```sql
UPDATE chatbot_response_rule 
SET confidence_threshold = 0.9 
WHERE intent = 'menu_query';
```

Nếu quá nhiều âm tính giả (xếp hàng những thứ có thể phản hồi tự động):
```sql
UPDATE chatbot_response_rule 
SET confidence_threshold = 0.7 
WHERE intent = 'hours_query';
```

---

## ✅ Tiếp Theo Là Gì?

Sau khi triển khai Giai đoạn 2-3:

1. **Bảng Điều Khiển Phân Tích** - Theo dõi các số liệu hiệu suất
2. **Khảo Sát Thỏa Mãn Khách Hàng** - Sau mỗi phản hồi tự động
3. **Phân Tích Cảm Xúc** - Phát hiện khách hàng khó tính
4. **Xử Lý Nhiều Ý Định** - Xử lý các câu hỏi như "giờ VÀ menu?"
5. **Bộ Nhớ Ngữ Cảnh** - Lưu trữ lịch sử cuộc hội thoại để trả lời theo sau

---

**Sẵn sàng triển khai? Chọn một giai đoạn và bắt đầu viết code!** 🚀
