---
title: "Kênh tin Zalo/Telegram + Facebook page"
description: "Zalo-first: tin NV thật → AG-MSG live → /inbox → hiệu lực ca; Page quán trống tới khi nối Meta. Không fixture làm dữ liệu quán."
status: in-progress
priority: P1
effort: "10-14d"
tags: [nhip-quan, messaging, zalo, telegram, facebook, inbox]
created: 2026-08-27
blockedBy: []
blocks: []
---

# Kênh tin Zalo/Telegram + Facebook page

## Overview

Đường ống **tin nhân viên (ưu tiên Zalo OA) → AG-MSG → `/inbox` → hiệu lực ca / trả lịch**, rồi **Page quán** (Facebook) riêng. Replay/fixture **chỉ CI** (`NHIPQUAN_ALLOW_MSG_REPLAY=1`). UI ops trống / «Chưa nối» cho đến khi quán gắn token thật + `CA_AGENT_MODE=live`.

**Không** biến `/inbox` ràng buộc thành CRM. **Không** để AG-MSG tự ghi `phan_cong`. **Không** nhồi thread giả trên `/page-quan`.

## Brainstorm contract (accepted — Duyệt 1+2, pivot Zalo-first)

| Field | Value |
|-------|-------|
| **Outcome** | NV nhắn Zalo (hoặc Telegram) → bind `nv_id` → classify → `/inbox` (chip kênh) → QL duyệt → hiệu lực; hỏi lịch → MessagePort. `/page-quan` trống tới Meta. |
| **Constraints** | Zalo trước; AG-MSG không ghi DB; tái dùng `/inbox`; Facebook surface riêng; bí mật token chỉ env; replay không phải path ops. |
| **Non-goals** | Tạo OA/Page hộ chủ quán; Meta Suite; ads; LLM tự duyệt đổi ca; CRM khách. |
| **Acceptance** | CI replay xanh; chip kênh; approve có `hieu_luc`; status `connected: false` khi chưa token; runbook Zalo/Telegram/FB. |

## Phases

| # | Phase | Status | Depends |
|---|-------|--------|---------|
| 1 | [Khung ChannelPort + fixture CI](./phase-01-start.md) | Done | — |
| 2 | [Inbound + bind nv (Zalo+Telegram)](./phase-02-telegram-inbound-va-bind-nv.md) | Done | 1 |
| 3 | [Classify → inbox + hiệu lực ca](./phase-03-classify-vao-inbox-va-hieu-luc-ca.md) | Done | 2 |
| 4 | [Trả lịch qua MessagePort](./phase-04-tra-lich-qua-messageport.md) | Done | 3 |
| 5 | [Zalo OA live + R8 doc](./phase-05-zalo-cung-port-sau-r8.md) | Done (wire+runbook; OA do quán) | 4 |
| 6 | [Facebook `/page-quan` empty+API](./phase-06-facebook-page-surface-replay.md) | Done | 1 |
| 7 | [Facebook connect khi có page](./phase-07-facebook-connect-khi-co-page.md) | Pending (chờ Page thật) | 6 |

## Success Criteria

- [x] CI: bind → inbound → `/inbox` → duyệt → `hieu_luc` / swap
- [x] Hỏi lịch (sau bind) → outbound replay/outbox
- [x] `/page-quan` trống khi chưa Meta; không seed fixture mặc định
- [x] Runbooks tạo OA / bot / Page
- [ ] Quán gắn token thật + webhook HTTPS (ngoài code)

## Risks

| Risk | Signal | Response |
|------|--------|----------|
| Chưa có OA/Page | `connected: false` | Runbook; UI «Chưa nối» |
| Zalo phí R8 | gửi tin fail | Doc bảng giá; giữ Telegram phụ |
| Approve silent rewrite | phan_cong đổi | Chỉ `hieu_luc` + chợ |

<!-- slug: kenh-tin-telegram-zalo-va-facebook-page -->
