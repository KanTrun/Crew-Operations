---
phase: 4
title: "Tra lich qua MessagePort"
status: done
priority: P1
effort: "1d"
dependencies: [3]
---

# Phase 4: Trả lịch qua MessagePort

## Overview

Cho phép nhân viên (đã bind) hỏi lịch → hệ thống đọc cùng nguồn `/toi/lich` → `MessagePort.send` bản tóm tắt ca. Đây là câu trả lời “biết lịch của người đó” đúng DNA ca-centric.

## Requirements

- Functional: nhận diện hỏi lịch (keyword/intent mới `xem_lich` hoặc nhánh `khac` có pattern); trả lời không cần duyệt quản lý nếu chỉ đọc
- Non-functional: không lộ lịch người khác; chỉ `nv_id` của người hỏi

## Architecture

```text
Inbound (bound) → detect xem_lich → load lich(nv_id) → format VI → port.send(chat_id, text)
```

Manager có thể “Gửi lại lịch” từ hồ sơ NV (optional, cùng helper).

## Related Code Files

- Modify: `ag_msg` intents hoặc detector riêng `xem_lich`
- Modify: API helper tái dùng logic `/api/v1/toi/lich`
- Modify: `TelegramPort.send` (live optional; replay ghi file/log)
- Create: golden expected reply snippets

## Implementation Steps

1. Thêm nhận diện “lịch của tôi / ca tuần này / hôm nay làm gì”
2. Format ngắn: ngày · khung · vai trò (tiếng Việt)
3. Send qua port; mode replay ghi `data/out/msg_sent.jsonl`
4. Test: bind minh → hỏi lịch → đúng ca fixture

## Success Criteria

- [ ] Reply chỉ lịch của đúng nv
- [ ] Replay không cần Telegram token
- [ ] Không lộ lịch nhân viên khác

## Risk Assessment

Intent nhầm với `doi_ca` — ưu tiên keyword lịch trước; nếu ambiguous → xếp inbox thay vì auto-reply.
