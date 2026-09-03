---
title: "Phase 1: Start & Extract Cấu Trúc"
status: done
---

# Phase 1: Start & Extract Cấu Trúc

## Overview

Nâng cấp bộ phân loại và trích xuất tin nhắn (`ca_agents.ag_msg.extract:classify`) để rút trích dữ liệu có cấu trúc:
- Thứ (`T2`–`CN`)
- Ngữ cảnh tuần (`tuan_id`, ví dụ `2026-W01`, hỗ trợ từ "tuần sau", "tuần này")
- Khung giờ (`start`, `end`, ví dụ `07:00` - `12:00` hoặc ca sáng/chiều/tối)
- Mã ca (`ca_id`, ví dụ `w1_c01`)
- Đối tác đổi ca (`doi_tac`) kèm đối chiếu danh sách nhân viên để phát hiện trùng tên (`doi_tac_khong_ro`)
- Độ tin cậy trích xuất (`do_tin_cay`), tự động gắn `can_xac_minh=True` nếu `< 0.7`.

## Requirements

- [x] Rút trích `thu`, `tuan_id`, `start`, `end`, `ca_id`, `doi_tac`.
- [x] Đánh dấu `can_xac_minh=True` khi thiếu trường cốt lõi.
- [x] Đánh dấu `doi_tac_khong_ro=True` khi tên nhân viên bị trùng.
- [x] Tuân thủ kiến trúc AST sạch: không import trực tiếp từ API/DB, nhận `staff` qua tham số.

## Implementation Steps

1. Viết các regex & tokenizer bóc tách thứ, giờ, mã ca, tuần trong `extract.py`.
2. Bổ sung `MsgResult.rang_buoc` chứa metadata đầy đủ.
3. Inject `staff` từ tầng `channels.py` qua `list_users()`.

