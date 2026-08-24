---
title: Brainstorm — kết thúc PoC, hoàn thiện UI dở của Kiro
date: 2026-08-24
status: accepted
---

# Brainstorm: làm tiếp tới hoàn thiện PoC

## Summary

`main` đã vượt xa bản “55%” cũ: 9 agent Lô 1, 252 test, tag `v0.1.0-semifinal` và `v1.0.0-final`, 13 commit chưa đẩy. Working tree còn ~3.800 dòng UI chưa commit (Kiro hết token). Hướng: hoàn thiện WIP đó theo `docs/design-guidelines.md` v3, không viết lại từ đầu, không bịa quán.

## Contract

| Field | Value |
|-------|-------|
| **Outcome** | Web PoC dùng được end-to-end: đăng ký, tour, hướng dẫn, 19 route kit thống nhất, e2e xanh. Slide/docs vẫn ghi fixture, không ghi “quán đã dùng”. |
| **Constraints** | 0 đồng, không Sentry/PostHog, không API LLM, không POS, giữ bubble/kit hiện có, tiếng Việt không mã lỗi thô. |
| **Non-goals** | Lô 2, đóng cổng §14.5 NV quán, live LLM, rewrite UI từ zero, force-push `main`. |
| **Acceptance** | `npm run lint` + Playwright 8+ luồng xanh trên WIP; trang `/dang-ky` `/huong-dan` tour chạy; không nháy “chưa có dữ liệu” khi đang tải; `pytest -q` không đỏ. |

## Options

1. **Hoàn thiện WIP Kiro** — giả định diff gần xong. Trượt nếu file dở không compile.
2. **Viết lại toàn bộ UI** — đắt, vứt 13 commit v3.1. Trượt khi hết token lần nữa.
3. **Vứt WIP, ship `HEAD`** — mất đăng ký/tour/hướng dẫn. Trượt so với ý định user.

**Chọn (1).**

## Unresolved

Hội đồng có chấp nhận khung PoC hay chấm cứng §14.5 — không biết trước. Demo 10 phút ×5 vẫn là việc người.
