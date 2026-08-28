# Repo rename: CA-CONG-BANG → Crew-Operations

**Date:** 2026-08-28  
**Product name unchanged:** NHỊP QUÁN

## Context

GitHub repository: `KanTrun/Crew-Operations`. Remote và README/docs đã đồng bộ (2026-08-28).

## Changes

- `git remote set-url origin https://github.com/KanTrun/Crew-Operations.git`
- README viết lại đầy đủ (kiến trúc, Docker, .env, Makefile, docs index)
- Cập nhật `docs/team.md`, `plan.md`, `llm.py` HTTP Referer/UA
- Đồng bộ README + docs sang mọi nhánh remote (`scripts/sync_docs_crew_operations.py`)

## Non-goals

- Không đổi tên sản phẩm NHỊP QUÁN
- Không đổi package Python `nhip-quan` / prefix `ca_*`
- Không bắt buộc đổi tên thư mục clone trên máy dev
