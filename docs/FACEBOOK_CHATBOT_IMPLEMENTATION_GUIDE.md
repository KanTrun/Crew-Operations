# Facebook Chatbot - Implementation Guide (Step by Step)

**Status:** Foundation Ready - Ready for Phase 1-2 Implementation  
**Date:** 2026-08-30

---

## 📋 Quick Summary

**What was built:**
- ✅ Comprehensive architecture document (ADR-014)
- ✅ Database migration (6 new tables with indices)
- ✅ Seed script for intents + response rules + FAQ
- ✅ AG-FBPAGE agent skeleton
- ✅ No RAG needed (small, stable knowledge base)

**What's left (next phase):**
- Webhook handler implementation
- Rules engine (intent → response matching)
- Auto-response logic
- Manager approval UI extension

---

## Phase 1: Database Setup (1-2 hours)

### Step 1.1: Apply Migration

```bash
cd d:\Crew-Operations
python -m alembic upgrade head
```

Expected output:
```
INFO: Running upgrade 0002_... -> 0003_add_facebook_chatbot_tables
```

### Step 1.2: Seed Initial Data

```bash
python scripts/seed_chatbot.py
```

Expected output:
```
✅ Chatbot seed data loaded successfully!
   - 7 intents created
   - 6 response rules created
   - 5 knowledge base entries created
```

### Step 1.3: Verify Tables

```bash
sqlite3 data/quan.db ".schema chatbot"
```

Should list:
```
chatbot_intent
chatbot_response_rule
chatbot_kb
chatbot_analytics
fb_conversation_thread
fb_message_log
```

### Step 1.4: Verify Data

```bash
sqlite3 data/quan.db "SELECT COUNT(*) as count FROM chatbot_intent"
# Output: 7
```

---

## Phase 2: Webhook Handler (2-4 hours)

### Step 2.1: Add Facebook Webhook Endpoint

**File:** `apps/api/src/ca_api/interfaces/http/channels.py`

Add this endpoint after existing Telegram/Zalo handlers:

```python
@router.post("/api/v1/channels/webhook/facebook")
async def facebook_webhook(request: Request) -> dict[str, str]:
    """
    Facebook Messenger Platform webhook.
    
    Facebook POST format:
    {
      "entry": [
        {
          "messaging": [
            {
              "sender": {"id": "<PSID>"},
              "message": {"mid": "<MID>", "text": "hello"}
            }
          ]
        }
      ]
    }
    """
    
    # Import needed
    from ca_agents.ag_fbpage import parse_fb_webhook_message, process_fb_message
    
    try:
        body = await request.json()
    except Exception:
        # Facebook will retry if we don't return 200
        return {"status": "ok"}
    
    # Process each message entry
    for entry in body.get("entry", []):
        messaging_data = entry.get("messaging", [])
        
        for msg_entry in messaging_data:
            # Skip non-message events (delivery, read, etc.)
            if "message" not in msg_entry:
                continue
            
            # Parse message
            input_msg = await parse_fb_webhook_message(msg_entry)
            if not input_msg:
                continue
            
            try:
                # Process asynchronously (fire and forget)
                await process_fb_message(input_msg)
            except Exception as e:
                # Log error but don't fail webhook response
                _audit("fb_webhook", "error", {"error": str(e), "psid": input_msg.psid})
    
    # Always return 200 to acknowledge webhook
    return {"status": "ok"}


@router.get("/api/v1/channels/webhook/facebook/verify")
def facebook_webhook_verify(
    hub_mode: str = Query(None),
    hub_challenge: str = Query(None),
    hub_verify_token: str = Query(None)
) -> str:
    """
    Facebook Messenger webhook verification (GET).
    
    Used by Facebook to verify webhook URL on setup.
    """
    
    expected_token = os.getenv("NHIPQUAN_FB_WEBHOOK_VERIFY", "change-me")
    
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        return hub_challenge  # Echo back challenge
    else:
        raise HTTPException(status_code=403, detail="verification_failed")
```

### Step 2.2: Configure .env

```bash
# .env file - add/update:

FACEBOOK_PAGE_ACCESS_TOKEN=<your_token_here>
FACEBOOK_PAGE_ID=1367177249801969
FACEBOOK_WEBHOOK_VERIFY=my-secret-verify-token
```

### Step 2.3: Register Webhook in Facebook App

1. Go to: https://developers.facebook.com/apps/
2. Select your app
3. Messenger → Settings
4. Scroll to "Webhooks"
5. Click "Edit Subscription"
6. Set:
   - **Callback URL:** `https://your-domain/api/v1/channels/webhook/facebook/verify`
   - **Verify Token:** `my-secret-verify-token` (must match .env)
   - **Subscribe to:** ✅ messages ✅ messaging_postbacks
7. Click "Verify and Save"

### Step 2.4: Test Webhook

```bash
# Send test message to page
curl -X POST https://graph.facebook.com/v26.0/{PSID}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": {"id": "'$PSID'"},
    "message": {"text": "Hello from test!"},
    "access_token": "'$FB_TOKEN'"
  }'

# Check API logs
tail -f data/logs/api.log | grep "fb_webhook"
```

---

## Phase 3: Response Rules Engine (2-3 hours)

### Step 3.1: Create Rules Matcher

**File:** `packages/agents/src/ca_agents/ag_fbpage.py` (extend)

```python
async def get_matching_rule(
    intent: str,
    confidence: float,
    conn: sqlite3.Connection
) -> dict[str, Any] | None:
    """
    Find best matching response rule for intent.
    
    Rules are retrieved from chatbot_response_rule table.
    Returns None if no enabled rule found.
    """
    
    cursor = conn.cursor()
    
    # Get enabled rules for this intent, ordered by specificity
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
    Decide if message should auto-respond based on:
    - Intent confidence
    - Rule threshold
    - Intent settings (requires_approval)
    """
    
    if not rule:
        return False
    
    if confidence < rule["threshold"]:
        return False
    
    # Check if intent requires approval
    from ca_api.persist import _conn
    cursor = _conn().cursor()
    cursor.execute(
        "SELECT requires_approval FROM chatbot_intent WHERE id = ?",
        (intent,)
    )
    row = cursor.fetchone()
    
    if row and row[0] == 1:
        return False  # Requires approval
    
    return True
```

### Step 3.2: Extend process_fb_message

**File:** `packages/agents/src/ca_agents/ag_fbpage.py`

```python
async def process_fb_message(
    input_msg: FBMessageInput,
    *,
    confidence_threshold: float = 0.8,
    auto_respond_enabled: bool = True
) -> FBMessageOutput:
    """
    Full implementation of message processing.
    """
    
    from ca_agents.ag_msg import classify
    from ca_agents.facebook_page import send_messenger_text
    from ca_api.persist import _conn, _now
    
    try:
        # 1. Classify intent
        result = classify(input_msg.text, mode="live")
        
        # 2. Get matching rule
        rule = await get_matching_rule(
            result.intent,
            result.do_tin_cay,
            _conn()
        )
        
        # 3. Decide action
        should_auto = await should_auto_respond(
            result.intent,
            result.do_tin_cay,
            rule
        )
        
        if should_auto and auto_respond_enabled:
            # AUTO-RESPOND
            response_text = rule["response"]
            
            # Send via Facebook
            send_result = await send_messenger_text(
                input_msg.psid,
                response_text
            )
            
            # Log to database
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
                reason=f"Intent confidence {result.do_tin_cay:.2f} >= threshold"
            )
        
        else:
            # QUEUE FOR APPROVAL
            _enqueue_for_approval(
                message_id=input_msg.message_id,
                psid=input_msg.psid,
                text=input_msg.text,
                intent=result.intent,
                confidence=result.do_tin_cay
            )
            
            # Log to database
            _log_fb_message(
                message_id=input_msg.message_id,
                psid=input_msg.psid,
                text=input_msg.text,
                intent=result.intent,
                confidence=result.do_tin_cay,
                was_auto_responded=False
            )
            
            reason = "Requires human approval"
            if not rule:
                reason = "No matching response rule"
            elif result.do_tin_cay < rule["threshold"]:
                reason = f"Confidence {result.do_tin_cay:.2f} < threshold {rule['threshold']}"
            
            return FBMessageOutput(
                action="queue_to_inbox",
                response=None,
                intent=result.intent,
                confidence=result.do_tin_cay,
                reason=reason
            )
    
    except Exception as e:
        import traceback
        
        # Log error
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


def _log_fb_message(
    message_id: str,
    psid: str,
    text: str,
    intent: str,
    confidence: float,
    was_auto_responded: bool
) -> None:
    """Log message to fb_message_log."""
    
    from ca_api.persist import _conn, _now
    import uuid
    
    # Get or create thread
    thread_id = _get_or_create_thread(psid)
    
    with _conn() as cx:
        cx.execute("""
            INSERT INTO fb_message_log
            (id, thread_id, sender_id, sender_type, text, intent_classified, 
             intent_confidence, created_at, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"msg_{uuid.uuid4().hex[:8]}",
            thread_id,
            psid,
            "customer",
            text,
            intent,
            confidence,
            _now(),
            _now()
        ))


def _get_or_create_thread(psid: str) -> str:
    """Get existing thread or create new one."""
    
    from ca_api.persist import _conn, _now
    import uuid
    
    with _conn() as cx:
        # Try to find existing
        row = cx.execute(
            "SELECT id FROM fb_conversation_thread WHERE psid = ? ORDER BY created_at DESC LIMIT 1",
            (psid,)
        ).fetchone()
        
        if row:
            return row[0]
        
        # Create new
        thread_id = f"fb_th_{uuid.uuid4().hex[:8]}"
        cx.execute("""
            INSERT INTO fb_conversation_thread
            (id, psid, status, created_at)
            VALUES (?, ?, ?, ?)
        """, (thread_id, psid, "open", _now()))
        
        return thread_id


def _enqueue_for_approval(...) -> None:
    """Queue message to manager inbox (using existing inbox_rang_buoc logic)."""
    # Reuse existing _enqueue_inbox() from channels.py
    pass
```

---

## Phase 4: Testing & Validation (1-2 hours)

### Step 4.1: Unit Tests

```python
# apps/api/tests/test_ag_fbpage.py

import pytest
from ca_agents.ag_fbpage import FBMessageInput, process_fb_message


@pytest.mark.asyncio
async def test_auto_respond_hours_query():
    """Test auto-response for hours query."""
    
    msg = FBMessageInput(
        psid="123456",
        text="mở mấy giờ?",  # Should classify as hours_query
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
    """Test queueing order to inbox."""
    
    msg = FBMessageInput(
        psid="123456",
        text="2 cà phê sữa, 1 trà đào",  # Should classify as order
        message_id="msg_002",
        timestamp=1234567890
    )
    
    result = await process_fb_message(msg)
    
    assert result.action == "queue_to_inbox"
    assert result.intent == "order"
    # Should be queued because order requires_approval=true


@pytest.mark.asyncio
async def test_low_confidence_queued():
    """Test low-confidence messages are queued."""
    
    msg = FBMessageInput(
        psid="123456",
        text="xyz abc random text",  # Should have low confidence
        message_id="msg_003",
        timestamp=1234567890
    )
    
    result = await process_fb_message(msg)
    
    assert result.action == "queue_to_inbox"
    assert result.confidence < 0.8
```

### Step 4.2: Manual Testing

```bash
# 1. Start API server
cd apps/api
python -m uvicorn ca_api.main:app --reload --host 0.0.0.0 --port 8000

# 2. In another terminal, test webhook endpoint
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

# 3. Check database for logged message
sqlite3 data/quan.db "SELECT * FROM fb_message_log WHERE sender_id = 'test_psid_123'"
```

### Step 4.3: Integration Test

Send real message to page (via Facebook Messenger):
```
Message: "cà phê sữa bao nhiêu tiền?"
Expected: Auto-response with price
Check: fb_message_log should have entry with intent="menu_query"
```

---

## Phase 5: Manager UI Extension (2-3 hours)

### Step 5.1: Create Inbox Endpoint

**File:** `apps/api/src/ca_api/interfaces/http/channels.py`

```python
@router.get("/api/v1/page/fb-inbox")
def fb_inbox(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    """
    Get pending Facebook messages requiring approval.
    Similar to /api/v1/inbox/rang-buoc but for FB messages.
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
    body: dict[str, str],  # {"response": "...custom response..."}
    authorization: Annotated[str | None, Header()] = None
) -> dict[str, Any]:
    """
    Manager approves and sends response to Facebook message.
    """
    
    role = _require_manager(authorization)
    
    response_text = body.get("response", "")
    if not response_text:
        raise HTTPException(status_code=400, detail="response_required")
    
    # Get message details
    with _conn() as cx:
        msg = cx.execute(
            "SELECT thread_id, sender_id FROM fb_message_log WHERE id = ?",
            (message_id,)
        ).fetchone()
    
    if not msg:
        raise HTTPException(status_code=404, detail="message_not_found")
    
    thread_id, psid = msg
    
    # Send via Facebook
    from ca_agents.facebook_page import send_messenger_text
    send_messenger_text(psid, response_text)
    
    # Mark thread as resolved
    with _conn() as cx:
        cx.execute(
            "UPDATE fb_conversation_thread SET status = ? WHERE id = ?",
            ("resolved", thread_id)
        )
    
    _audit(role, "fb_inbox_approve", {"message_id": message_id})
    
    return {"ok": True}
```

---

## 🚀 Deployment Checklist

Before going live:

- [ ] Database migration applied successfully
- [ ] Seed data loaded (7 intents, 6 rules)
- [ ] Webhook endpoint implemented
- [ ] Facebook webhook URL configured & verified
- [ ] Response rules tested manually
- [ ] Unit tests passing
- [ ] Manager UI tested
- [ ] Error handling in place
- [ ] Rollback procedure documented
- [ ] Team trained on new inbox feature

---

## 📊 Monitoring & Maintenance

### Daily Checks

```bash
# Check webhook errors
sqlite3 data/quan.db "SELECT * FROM fb_message_log WHERE intent_classified = 'error' LIMIT 10"

# Check response times
sqlite3 data/quan.db """
  SELECT intent_classified, AVG(intent_confidence)
  FROM fb_message_log
  WHERE created_at > datetime('now', '-24 hours')
  GROUP BY intent_classified
"""

# Check approval queue depth
sqlite3 data/quan.db """
  SELECT COUNT(*) 
  FROM fb_conversation_thread 
  WHERE status = 'open'
"""
```

### Adjusting Thresholds

If too many false positives (auto-responding incorrectly):
```sql
UPDATE chatbot_response_rule 
SET confidence_threshold = 0.9 
WHERE intent = 'menu_query';
```

If too many false negatives (queuing things that could auto-respond):
```sql
UPDATE chatbot_response_rule 
SET confidence_threshold = 0.7 
WHERE intent = 'hours_query';
```

---

## ✅ What's Next?

After implementing Phase 2-3:

1. **Analytics Dashboard** - Track performance metrics
2. **Customer Satisfaction Survey** - After each auto-response
3. **Sentiment Analysis** - Detect upset customers
4. **Multi-intent Handling** - Handle questions like "hours AND menu?"
5. **Context Memory** - Store conversation history for follow-up questions

---

**Ready to implement? Pick a phase and start coding!** 🚀
