# Facebook Chatbot System — Detailed Architecture & Implementation Plan

**Date:** 2026-08-30  
**Status:** Design Phase  
**Author:** Copilot  

---

## 📊 Executive Summary

This document outlines a production-ready chatbot system for Nhịp Quán's Facebook Page, following the deterministic orchestration architecture (ADR-002) already established in the codebase.

### Key Decisions:
- ✅ **NO RAG needed initially** — knowledge base is small & stable
- ✅ **Hybrid approach** — deterministic rules + LLM for uncertain cases  
- ✅ **No new database** — extend existing SQLite with new tables
- ✅ **AG-MSG agent** — best fit for message classification & routing
- ✅ **Approval gate** — human review before auto-response (anti-fake signals)

---

## Part 1: Current Architecture Analysis

### 1.1 Existing Infrastructure

```
┌─────────────────────────────────────────────────────┐
│            Facebook Graph API (v26.0)               │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│   packages/agents/facebook_page.py (PARTIAL)        │
├──────────────────────────────────────────────────────┤
│  ✅ graph_get()           — READ operations         │
│  ✅ graph_post()          — WRITE operations        │
│  ✅ page_health()         — Verify token/page       │
│  ✅ fetch_conversations() — Get message threads     │
│  ✅ send_messenger_text() — Send reply to user      │
│  ✅ publish_page_post()   — Post to page feed       │
│  ❌ facebook_webhook()    — MISSING                 │
│  ❌ parse_messenger_msg() — MISSING                 │
│  ❌ conversation_history()— MISSING                 │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│   apps/api/interfaces/http/channels.py              │
├──────────────────────────────────────────────────────┤
│  ✅ process_inbound()      — Classify + queue       │
│  ✅ Telegram support                                │
│  ✅ Zalo support                                    │
│  ❌ Facebook Messenger support (webhook)            │
│  ❌ Auto-response logic                             │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│   apps/api/persist.py (SQLite)                      │
├──────────────────────────────────────────────────────┤
│  Tables (EXISTING):                                 │
│  ✅ users              — Employees (3 roles)        │
│  ✅ kenh_bind          — Channel ↔ Employee map     │
│  ✅ kv                 — Key-value store            │
│  ✅ don_quay           — POS orders                 │
│  ✅ menu_mon           — Menu items                 │
│  ✅ audit              — Action log                 │
│                                                     │
│  Tables (NEEDED):                                   │
│  ❌ fb_conversation_thread  ← Store threads         │
│  ❌ fb_message_log          ← All messages          │
│  ❌ chatbot_kb              ← Knowledge base         │
│  ❌ chatbot_response_rule   ← Auto-responses        │
│  ❌ chatbot_intent          ← Intent definitions    │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│   packages/agents/ag_msg/                           │
├──────────────────────────────────────────────────────┤
│  ✅ classify()    — Intent + confidence (do_tin_cay)│
│  ✅ INTENTS       — Fixed intents list              │
│  ✅ LLM support   — Groq/Gemini/OpenRouter         │
│  ✅ Replay mode   — Deterministic testing           │
└─────────────────────────────────────────────────────┘
```

### 1.2 Current Data Flow

```
Telegram/Zalo message
    ↓
[webhook] → parse_telegram_update() / parse_zalo_webhook()
    ↓
InboundMessage(channel, external_user_id, text)
    ↓
process_inbound()
    ├─ Try /bind {code} → kenh_bind user
    ├─ Try /xem-lich → format_lich(nv_id)
    └─ classify(text) → {intent, do_tin_cay}
         ↓
    IF: /bind or /xem-lich → send immediately via port
    ELSE: → _enqueue_inbox() → kv["inbox_rang_buoc"]
         ↓
[manager review UI] → GET /api/v1/inbox/rang-buoc
    ↓
[manager decides] → POST /api/v1/inbox/rang-buoc/{id}
    └─ → port.send(external_user_id, response)
```

### 1.3 Key Constraints (ADR-002)

✅ **Deterministic** — no LLM orchestration  
✅ **Human approval** — before posting (anti-fake ADR-008)  
✅ **Stateless agents** — no DB writes from agents  
✅ **Structured contracts** — all DTO via ca_contracts  

---

## Part 2: RAG (Retrieval-Augmented Generation) — Analysis

### 2.1 Do We Need RAG?

**Current Knowledge Base Size:**
```
Coffee menu items:        4 items (den, sua, tra, da)
Operating hours:         1 fact (6h - 22h)
FAQ topics:              ~10 expected (hours, reservation, payment, etc.)
Procedures (SOP):        8 playbook steps (documented)
Total unique facts:      ~30-50 items
```

**RAG Trade-offs:**

| Aspect | Pro (RAG) | Con (RAG) |
|--------|-----------|----------|
| **Scalability** | Handles 1000+ docs | Overkill for 50 facts |
| **Flexibility** | Auto-index new docs | Needs vector DB (Pinecone/Weaviate) |
| **Latency** | 2-3 extra API calls | 200-500ms overhead |
| **Cost** | Uses embedding model | $0.02 per req (Cohere) |
| **Accuracy** | Retrieves context | Can hallucinate wrong context |

### ✅ Decision: **NO RAG initially**

**Rationale:**
1. **Small KB** — 50 facts fit in prompt engineering + few-shot examples
2. **Stable content** — menu/hours rarely change
3. **High precision needed** — deterministic rules better than retrieval
4. **Cost conscious** — each chatbot request is ~1000 messages/day
5. **Fast iteration** — rules engine updated within 1 minute, no reindexing

**Future RAG candidates:**
- Customer FAQs (cumulative questions from logs)
- Procedure manuals (when cafe operations scale)
- Multi-location support (different menus, hours per location)

### 2.2 Knowledge Base Structure (NO RAG needed)

Instead of RAG vectors, use **structured data**:

```python
# packages/agents/ag_msg/knowledge_base.py (NEW)

KB = {
    "hours": {
        "fact": "Quán mở 6h sáng - 22h tối",
        "confidence": 1.0,
        "sources": ["config/tham-so-lao-dong.yaml"],
        "last_updated": "2026-08-30"
    },
    "menu": {
        "fact": "Xem menu đầy đủ tại: link-menu.html",
        "items": ["den", "sua", "tra", "da"],  # from db.menu_mon
        "confidence": 1.0,
        "dynamic": True  # loaded from DB
    },
    "reservation": {
        "fact": "Đặt bàn tại web NHỊP QUÁN → Đặt trước",
        "confidence": 0.9,
        "sources": ["SOP step 3"]
    },
    "payment": {
        "fact": "Thanh toán bằng tiền mặt hoặc QR code",
        "confidence": 0.9
    }
}
```

---

## Part 3: Database Schema Design

### 3.1 New Tables (SQL Migrations)

```sql
-- 1. Facebook Conversation Threads
CREATE TABLE fb_conversation_thread (
    id TEXT PRIMARY KEY,           -- thread_id from fetch_conversations()
    psid TEXT NOT NULL,            -- Page Scope ID (customer)
    customer_name TEXT,            -- from Graph API
    topic_inferred TEXT,           -- "order", "question", "feedback" etc.
    last_message_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    status TEXT DEFAULT "open",    -- open|resolved|spam
    assigned_to_nv_id TEXT,        -- NULL = unassigned
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_to_nv_id) REFERENCES users(nv_id)
);

-- 2. Facebook Message Log
CREATE TABLE fb_message_log (
    id TEXT PRIMARY KEY,           -- msg.id from API
    thread_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,       -- psid or page_id
    sender_type TEXT,              -- "customer" or "agent"
    text TEXT,
    reply_to_id TEXT,
    sentiment TEXT,                -- "positive", "neutral", "negative"
    intent_classified TEXT,        -- populated by AG-MSG
    intent_confidence REAL,        -- do_tin_cay
    created_at TIMESTAMP,
    processed_at TIMESTAMP,        -- when AG-MSG classified it
    FOREIGN KEY (thread_id) REFERENCES fb_conversation_thread(id)
);

-- 3. Chatbot Response Rules
CREATE TABLE chatbot_response_rule (
    id TEXT PRIMARY KEY,
    intent TEXT NOT NULL,          -- "hours_query", "menu_query" etc.
    condition TEXT,                -- JSON rule matching (optional)
    response_template TEXT,        -- parameterized response
    confidence_threshold REAL DEFAULT 0.8,
    enabled INTEGER DEFAULT 1,
    created_by_nv_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(intent, condition),
    FOREIGN KEY (created_by_nv_id) REFERENCES users(nv_id)
);

-- 4. Chatbot Intent Definitions
CREATE TABLE chatbot_intent (
    id TEXT PRIMARY KEY,           -- "hours_query", "menu_query"
    display_name TEXT,
    description TEXT,
    sample_questions TEXT,         -- JSON array of examples
    requires_approval INTEGER DEFAULT 0,  -- needs human review
    auto_response_enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(id)
);

-- 5. Chatbot KB (Knowledge Base)
CREATE TABLE chatbot_kb (
    id TEXT PRIMARY KEY,
    category TEXT,                 -- "hours", "menu", "payment" etc.
    key_phrase TEXT,
    content TEXT,
    sources TEXT,                  -- JSON array of doc references
    confidence REAL DEFAULT 1.0,
    dynamic_from_table TEXT,       -- "menu_mon" if loaded from DB
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Chatbot Analytics
CREATE TABLE chatbot_analytics (
    id TEXT PRIMARY KEY,
    thread_id TEXT,
    intent_classified TEXT,
    intent_confidence REAL,
    was_auto_responded INTEGER,    -- 1=yes, 0=required human
    human_response_time_seconds INTEGER,
    customer_satisfied INTEGER,    -- 1=yes, 0=no, NULL=unknown
    feedback_text TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES fb_conversation_thread(id)
);
```

### 3.2 Migration File

```python
# apps/api/alembic/versions/0003_add_chatbot_tables.py

def upgrade():
    op.execute("""
        CREATE TABLE fb_conversation_thread (
            id TEXT PRIMARY KEY,
            psid TEXT NOT NULL,
            customer_name TEXT,
            topic_inferred TEXT,
            last_message_at TIMESTAMP,
            message_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'open',
            assigned_to_nv_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # ... (other tables)

def downgrade():
    op.execute("DROP TABLE IF EXISTS chatbot_analytics")
    # ... (others)
```

---

## Part 4: Agent Selection & Design

### 4.1 Which Agent Should Handle Facebook?

**Current Agents (Lô 1):**

| Agent | Purpose | Suitable for FB? |
|-------|---------|------------------|
| **AG-MSG** | Message classification | ✅ **BEST** — already does intent detection |
| **AG-TKB** | Schedule/roster | ❌ No, focuses on shifts |
| **AG-BRIEF** | Explaining constraints | ❌ No, technical docs |
| **AG-EXPLAIN** | Analysis & reports | ❌ No, data queries |
| **AG-RULE** | Learning SOP rules | ❌ No, offline learning |
| **AG-HANDOVER** | Escalation logic | ⚠️ Maybe — for routing |
| **AG-MEETING** | Transcription & minutes | ❌ No, voice processing |
| **AG-VOC** | Customer voice of customer | ⚠️ Maybe — sentiment |
| **AG-WASTE** | Inventory monitoring | ❌ No, supply chain |
| **AG-SOP** | SOP documentation | ⚠️ Maybe — knowledge source |

### ✅ **Decision: Extend AG-MSG to AG-FBPAGE**

**New Agent: AG-FBPAGE** (Facebook Page Agent)

```
Purpose:
  1. Classify incoming Facebook messages (via AG-MSG)
  2. Match against response rules
  3. Auto-respond or queue for approval
  4. Track conversation lifecycle

Responsibilities:
  - Listen to fb_webhook POST
  - Convert to standardized InboundMessage
  - Call classify(text)
  - Look up response_rule by intent
  - If confidence >= threshold → auto-send
  - Else → enqueue to manager inbox
  - Log all interactions to fb_message_log
  - Track sentiment & satisfaction

Inputs:
  - Facebook Webhook (text from customer)
  - classify() result (intent + confidence)
  - chatbot_response_rule table
  - chatbot_kb table

Outputs:
  - send_messenger_text(psid, response)
  - INSERT fb_message_log
  - INSERT to kv["inbox_rang_buoc"] if needs approval
  - Analytics to chatbot_analytics

Architecture:
  ┌─ Facebook Webhook
  │     ↓
  │  ag_fbpage.receive_webhook()
  │     ├─ Parse message
  │     ├─ Create thread if new
  │     ├─ Call ag_msg.classify()
  │     ├─ Look up response_rule
  │     ├─ IF confidence >= 0.8 AND auto_enabled
  │     │    └─ send_messenger_text()
  │     │         + log to fb_message_log
  │     │         + analytics
  │     └─ ELSE enqueue to inbox
  │           + set assigned_to_nv_id=NULL
  │           + log to fb_message_log
  │           + wait for manager approval
  └─
```

### 4.2 Integration Points

```python
# packages/agents/src/ca_agents/ag_fbpage/ (NEW)

ag_fbpage/
├── __init__.py
├── webhook.py         ← Handle incoming messages
├── message.py         ← Message processing
├── classifier.py      ← Use AG-MSG.classify()
├── rules_engine.py    ← Match response rules
├── sender.py          ← Send via facebook_page.send_messenger_text()
└── analytics.py       ← Log to chatbot_analytics

# apps/api/src/ca_api/interfaces/http/channels.py
# Add endpoint: POST /api/v1/channels/webhook/facebook
```

---

## Part 5: Implementation Roadmap

### Phase 1: Foundation (Week 1)

```
☐ Create migration file (0003_add_chatbot_tables.py)
☐ Seed chatbot_intent table with basic intents
☐ Seed chatbot_response_rule with FAQ responses
☐ Extend facebook_page.py with conversation helpers
```

**Deliverable:** Database ready, no code logic yet

### Phase 2: Webhook Handler (Week 1-2)

```
☐ Add ag_fbpage module with webhook.py
☐ Implement POST /api/v1/channels/webhook/facebook endpoint
☐ Parse incoming Message webhook
☐ Create fb_conversation_thread if new
☐ Call ag_msg.classify(text)
☐ Log to fb_message_log
```

**Deliverable:** Messages are ingested and classified

### Phase 3: Response Engine (Week 2)

```
☐ Implement rules_engine.py to match intent → response_rule
☐ Parameterize responses (e.g., hours in response)
☐ Implement confidence threshold check
☐ Add auto-response logic
☐ Add queue-to-inbox logic for uncertain cases
```

**Deliverable:** Can auto-respond to high-confidence messages

### Phase 4: Manager Review UI (Week 2-3)

```
☐ Create /api/v1/page/fb-inbox endpoint (like inbox_rang_buoc)
☐ Manager can see pending FB messages
☐ Manager can approve + customize response
☐ Send response via send_messenger_text()
☐ Mark thread as resolved
```

**Deliverable:** Manager can review + approve before sending

### Phase 5: Analytics & Monitoring (Week 3)

```
☐ Track auto-response rate
☐ Track approval times
☐ Sentiment analysis on incoming messages
☐ Customer satisfaction tracking
☐ Dashboard: intents distribution, resolution time
```

**Deliverable:** Metrics dashboard

---

## Part 6: Response Rules Database (Initial Seed)

### 6.1 Intent Definitions

```json
{
  "intents": [
    {
      "id": "hours_query",
      "display_name": "Hỏi giờ mở cửa",
      "description": "Customer asks when cafe is open",
      "sample_questions": [
        "Mở mấy giờ?",
        "Các bạn đóng cửa lúc mấy giờ?",
        "Mở hôm nay không?"
      ],
      "requires_approval": false,
      "auto_response_enabled": true
    },
    {
      "id": "menu_query",
      "display_name": "Hỏi về menu",
      "description": "Ask about menu or specific drinks",
      "sample_questions": [
        "Các bạn có gì ngon?",
        "Giá cà phê bao nhiêu?",
        "Menu đầy đủ ở đâu?"
      ],
      "requires_approval": false,
      "auto_response_enabled": true
    },
    {
      "id": "reservation",
      "display_name": "Đặt bàn/tổ chức sự kiện",
      "description": "Request table reservation or event",
      "sample_questions": [
        "Có thể đặt bàn được không?",
        "Tổ chức sinh nhật ở đây được không?",
        "Đặt 5 người hôm thứ sáu"
      ],
      "requires_approval": true,    ← Needs manager approval
      "auto_response_enabled": false
    },
    {
      "id": "order",
      "display_name": "Đặt hàng",
      "description": "Place an order",
      "sample_questions": [
        "Có thể giao hàng không?",
        "2 cà phê sữa, 1 trà đào"
      ],
      "requires_approval": true,
      "auto_response_enabled": false
    },
    {
      "id": "feedback",
      "display_name": "Góp ý/khiếu nại",
      "description": "Feedback or complaint",
      "sample_questions": [
        "Cà phê quá lạnh",
        "Bạn phục vụ rất tốt!",
        "Tại sao phí giao hàng cao vậy?"
      ],
      "requires_approval": true,
      "auto_response_enabled": false
    }
  ]
}
```

### 6.2 Response Rules

```sql
INSERT INTO chatbot_response_rule VALUES
('rule_hours_1', 'hours_query', NULL, 
 'Quán mở 6h sáng - 22h tối, mỗi ngày 👍', 0.85, 1, 'nv_02', NOW()),

('rule_menu_1', 'menu_query', NULL,
 'Menu của chúng tôi: Cà phê đen, cà phê sữa, trà đào, bạc xỉu. Xem chi tiết: [link]', 
 0.8, 1, 'nv_02', NOW()),

('rule_reservation_1', 'reservation', NULL,
 'Cảm ơn! Hãy liên hệ trực tiếp hoặc đặt tại web NHỊP QUÁN. Chúng tôi sẽ xác nhận sớm nhất!',
 0.7, 1, 'nv_02', NOW()),

('rule_feedback_1', 'feedback', NULL,
 'Cảm ơn feedback bạn! Đội ngũ của chúng tôi sẽ cải thiện.',
 0.75, 1, 'nv_02', NOW());
```

---

## Part 7: Code Skeleton

### 7.1 FB Page Agent Structure

```python
# packages/agents/src/ca_agents/ag_fbpage/__init__.py

from ca_agents.ag_fbpage.webhook import receive_webhook
from ca_agents.ag_fbpage.message import process_fb_message

__all__ = ["receive_webhook", "process_fb_message"]

# ─────────────────────────────────────────────────

# packages/agents/src/ca_agents/ag_fbpage/message.py

from dataclasses import dataclass
from ca_agents.ag_msg import classify
from ca_agents.facebook_page import send_messenger_text

@dataclass
class FBMessageInput:
    psid: str               # Page Scope ID (customer)
    text: str
    message_id: str
    timestamp: float

@dataclass  
class FBMessageOutput:
    action: str             # "auto_respond" | "queue_to_inbox"
    response: str | None
    intent: str
    confidence: float

async def process_fb_message(input_msg: FBMessageInput) -> FBMessageOutput:
    """Process message: classify + decide action."""
    
    # 1. Classify
    r = classify(input_msg.text, mode="live")
    
    # 2. Get response rule
    rule = get_response_rule(r.intent, r.do_tin_cay)
    
    # 3. Decide action
    if rule and r.do_tin_cay >= rule.confidence_threshold:
        # Auto-respond
        response_text = render_response(rule, context={...})
        await send_messenger_text(input_msg.psid, response_text)
        
        log_to_analytics(
            thread_id=...,
            intent=r.intent,
            confidence=r.do_tin_cay,
            was_auto_responded=True
        )
        
        return FBMessageOutput(
            action="auto_respond",
            response=response_text,
            intent=r.intent,
            confidence=r.do_tin_cay
        )
    else:
        # Queue to inbox for manager review
        enqueue_to_inbox(
            text=input_msg.text,
            intent=r.intent,
            do_tin_cay=r.do_tin_cay,
            nguon="facebook",
            ...
        )
        
        return FBMessageOutput(
            action="queue_to_inbox",
            response=None,
            intent=r.intent,
            confidence=r.do_tin_cay
        )

# ─────────────────────────────────────────────────

# apps/api/interfaces/http/channels.py (EXTEND)

@router.post("/api/v1/channels/webhook/facebook")
async def facebook_webhook(request: Request):
    """Facebook Messenger webhook entry point."""
    body = await request.json()
    
    # Verify signature (security)
    if not _verify_fb_signature(request, body):
        return Response(status_code=403)
    
    for entry in body.get("entry", []):
        for messaging in entry.get("messaging", []):
            msg = FBMessageInput(
                psid=messaging["sender"]["id"],
                text=messaging["message"].get("text", ""),
                message_id=messaging["message"]["mid"],
                timestamp=messaging["timestamp"]
            )
            
            result = await process_fb_message(msg)
            # (result logged internally)
    
    return {"status": "ok"}  # Always return 200 to ACK webhook
```

---

## Part 8: Deployment Checklist

- [ ] Test token + page ID in .env
- [ ] Set Facebook Webhook URL
- [ ] Create database tables (migration)
- [ ] Seed intents + rules
- [ ] Deploy code changes
- [ ] Test with sample messages
- [ ] Monitor first 24h conversation logs
- [ ] Adjust confidence thresholds based on metrics
- [ ] Train team on manager approval UI

---

## Part 9: Rollback Plan

If issues occur:

```bash
# 1. Disable webhook
export FACEBOOK_WEBHOOK_ENABLED=false

# 2. All messages go to manager inbox (no auto-responses)
# In rules_engine.py: IF webhook_enabled == false → queue all

# 3. Manually review /api/v1/page/fb-inbox
# Respond as needed without automation

# 4. Check logs
SELECT * FROM fb_message_log WHERE created_at > NOW() - INTERVAL '1 hour';

# 5. Rollback schema
alembic downgrade -1

# 6. Re-enable when fixed
export FACEBOOK_WEBHOOK_ENABLED=true
```

---

## Summary Table

| Component | Status | Notes |
|-----------|--------|-------|
| Facebook API helpers | ✅ Mostly done | Extends facebook_page.py |
| Webhook handler | ❌ TODO | POST /api/v1/channels/webhook/facebook |
| Intent classifier (AG-MSG) | ✅ Ready | Already in use |
| Response rules engine | ❌ TODO | Match intent → response_rule |
| Database schema | ❌ TODO | 6 new tables, migration file |
| Manager approval UI | ⚠️ Extend | Reuse inbox_rang_buoc pattern |
| Auto-response logic | ❌ TODO | Confidence threshold check |
| Analytics | ❌ TODO | Track sentiment, satisfaction |
| Documentation | ❌ TODO | Runbook + troubleshooting |

---

**Next Step:** Implement Phase 1 (database schema + seed data)
