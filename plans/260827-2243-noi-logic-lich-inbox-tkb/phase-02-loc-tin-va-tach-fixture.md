---
title: "Phase 2: Lọc Tin & Tách Fixture"
status: done
---

# Phase 2: Lọc Tin & Tách Fixture

## Overview

- Lọc và bỏ qua tin nhắn không phải ý định lịch (/help, chào, hi, thời tiết, hỏi đáp chung), không đưa vào inbox duyệt.
- Chặn tự động seed 10 fake fixture trong `_seed_inbox()` khi hệ thống đã có tin nhắn từ kênh thật (`telegram`, `zalo`, `facebook`).
- Hỗ trợ biến môi trường `NHIPQUAN_INBOX_SEED_FIXTURE=0` để vô hiệu hoá seed khi kiểm thử hoặc chạy thật.

## Requirements

- [x] Chặn các intent `khac` không enqueue vào `inbox_rang_buoc`.
- [x] Không ghi đè fixture khi inbox đã có tin từ kênh thật.
- [x] Đưa tin độ tin cậy thấp `< 0.7` vào inbox với cờ `can_xac_minh=True`.

