# Repo rename: CA-CONG-BANG → Crew-Operations

**Date:** 2026-08-28  
**Product name unchanged:** NHỊP QUÁN

## Context

GitHub repository đã đổi tên thành `KanTrun/Crew-Operations`. Remote local vẫn trỏ `CA-CONG-BANG` và README/docs còn URL cũ.

## Changes

- `git remote set-url origin https://github.com/KanTrun/Crew-Operations.git`
- README viết lại đầy đủ (kiến trúc, Docker, .env, Makefile, docs index)
- Cập nhật `docs/team.md`, `plan.md`, `llm.py` HTTP Referer/UA
- Sửa link lịch sử trong plans/reports và journals

## Non-goals

- Không đổi tên sản phẩm NHỊP QUÁN
- Không đổi package Python `nhip-quan` / prefix `ca_*`
- Không bắt buộc đổi tên thư mục clone trên máy dev
