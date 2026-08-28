---
phase: 5
title: "Zalo cung port sau R8"
status: done
priority: P2
effort: "1-2d"
dependencies: [4]
---

# Phase 5: Zalo cùng port sau R8

## Overview

Cùng pipeline Phase 2–4 cho Zalo OA **chỉ sau** khi xác minh phí/ToS (R8). Trước đó giữ stub + tài liệu.

## Requirements

- Functional: `ZaloPort` receive/send thật khi `NHIPQUAN_ZALO_ENABLED=1` và có credential
- Non-functional: mặc định tắt; ghi rõ chi phí trong THIRD_PARTY

## Architecture

Reuse inbound→bind→classify→inbox; `nguon=zalo`. Không UI riêng.

## Related Code Files

- Modify: `messaging.py` `ZaloPort`
- Modify: webhook router (path `/channels/zalo/webhook`)
- Modify: `docs/THIRD_PARTY.md`

## Implementation Steps

1. Checklist R8: phí OA, hạn mức, ToS — ghi kết quả vào docs
2. Nếu chưa OK: phase đóng với stub + “blocked R8”
3. Nếu OK: mirror Telegram bind + webhook verify

## Success Criteria

- [ ] Docs R8 có quyết định bật/tắt có ngày
- [ ] Nếu tắt: CI không gọi Zalo mạng
- [ ] Nếu bật: replay + 1 smoke live (thủ công)

## Risk Assessment

Phí bất ngờ — signal: bill; response: kill switch env, fallback Telegram.
