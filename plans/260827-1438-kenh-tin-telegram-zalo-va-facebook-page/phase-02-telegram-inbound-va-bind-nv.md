---
phase: 2
title: "Telegram inbound va bind nv"
status: done
priority: P1
effort: "2d"
dependencies: [1]
---

# Phase 2: Telegram inbound + bind nv

## Overview

Nhận tin Telegram (webhook + đường replay), bắt buộc bind chat_id ↔ `nv_id` trước khi vào classify. Chưa gửi hiệu lực ca.

## Requirements

- Functional: `POST /api/v1/channels/telegram/webhook` (verify secret); replay ingest; NV tự bind bằng mã một lần trên `/toi` hoặc QL gán
- Non-functional: webhook không auth Bearer (dùng secret Telegram); rate-limit cơ bản

## Architecture

```text
Telegram → webhook → verify → InboundMessage → nếu chưa bind: trả hướng dẫn
                                         → nếu đã bind: queue nội bộ / gọi phase 3 hook
```

## Related Code Files

- Create: router webhook trong `apps/api/src/ca_api/interfaces/http/`
- Modify: `apps/web/src/app/toi/page.tsx` (UI mã bind)
- Modify: `packages/agents/src/ca_agents/messaging.py` (`TelegramPort` nhận + gửi stub→optional live)

## Implementation Steps

1. Webhook handler: chỉ nhận `message` text; bỏ attachment phức tạp
2. Lookup `kenh_bind`; nếu thiếu → outbound “gửi /bind &lt;mã&gt;” hoặc deep-link `/toi`
3. UI `/toi`: hiện mã bind + trạng thái “đã nối Telegram”
4. Replay path: script `scripts/replay_telegram_inbound.py` đẩy fixture

## Success Criteria

- [ ] Replay inbound tạo sự kiện có `nv_id` sau bind
- [ ] Tin chưa bind không vào inbox ràng buộc
- [ ] Manager có thể gán/gỡ bind

## Risk Assessment

Webhook HTTPS — signal: Meta/Telegram reject; response: chỉ bật live khi có tunnel/domain; CI luôn replay.
