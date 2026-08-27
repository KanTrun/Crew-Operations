---
phase: 1
title: "Khung ChannelPort + fixture"
status: done
priority: P1
effort: "1d"
dependencies: []
---

# Phase 1: Khung ChannelPort + fixture

## Overview

Mở rộng MessagePort thành nhận tin (receive) + chế độ replay/fixture, schema lưu bind kênh↔nv và metadata nguồn — chưa nối mạng thật.

## Requirements

- Functional: `receive` abstraction; fixture JSON tin mẫu; bảng/KV bind `channel_user_id` → `nv_id`; env `NHIPQUAN_MSG_BACKEND=console|telegram|zalo|replay`
- Non-functional: không gọi mạng trong CI; secret token chỉ env, không commit

## Architecture

- Extend `packages/agents/src/ca_agents/messaging.py` (hoặc module `channel_inbound.py` cạnh đó)
- Fixture: `data/golden/msg/` hoặc `data/fixtures/channels/`
- Persist bind trong SQLite qua `persist.py` (bảng `kenh_bind`)

## Related Code Files

- Modify: `packages/agents/src/ca_agents/messaging.py`
- Create: `packages/agents/src/ca_agents/channel_inbound.py` (nếu tách)
- Create: `data/golden/msg/inbound_01.jsonl` (hoặc tương đương)
- Modify: `apps/api/src/ca_api/persist.py`
- Modify: `docs/THIRD_PARTY.md` (ghi replay vs live)

## Implementation Steps

1. Định nghĩa `InboundMessage` (text, channel, external_user_id, ts, raw_id)
2. Implement `ReplayPort` đọc fixture theo thứ tự
3. Schema `kenh_bind` + API nội bộ list/upsert (manager-only)
4. Unit test: replay trả N tin ổn định

## Success Criteria

- [ ] `ReplayPort` trả tin fixture không cần mạng
- [ ] Bind schema có migration/seed test
- [ ] CI typecheck/tests xanh

## Risk Assessment

Fixture lệch shape Meta/Telegram sau này — giữ `raw` blob + field chuẩn tối thiểu; adapter parse per-channel ở phase sau.
