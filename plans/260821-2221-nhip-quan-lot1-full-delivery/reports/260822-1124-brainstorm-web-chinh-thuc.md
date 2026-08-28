---
title: Brainstorm — web vận hành chính thức S3–S5
date: 2026-08-22
status: accepted
---

# Web chính thức, hết mặt demo trên product

## Contract

| Field | Value |
|-------|-------|
| **Outcome** | Web là bàn làm việc quán: đăng nhập thật, dữ liệu sống sau restart, phiếu/lịch/cẩm nang/hộp thư không mang copy “demo/fixture/máy chủ giả”. |
| **Constraints** | Không bịa quán ký ngoài đời (ADR-012 vẫn đúng trên slide). Cùng quán sản phẩm “NHỊP QUÁN” = instance vận hành. Agent không ghi DB. Windows + SQLite file. |
| **Non-goals** | Zalo OA live, POS, đối tác café ngoài, merge `--ship` (vibe dừng ở PR trừ khi user bảo merge). |
| **Acceptance** | Login không prefill mật khẩu demo; token phiên lưu DB; phiếu/treo/sửa/inbox/lifecycle/cẩm nang persist; UI shell điều hướng ops; test đăng nhập qua API không hard-code banner demo. |

## Options

1. Giữ JSONL + đổi copy — restart mất phiếu. Không đạt “chạy thật”.
2. Postgres Docker only — gãy máy không compose.
3. **SQLite `data/quan.db` + stdlib `sqlite3` (chọn)** — bền, 0đ, CI được. (Không SQLAlchemy trong PR này.)

Giả định tải: seed 25 NV là **dữ liệu vận hành của instance này**, không phải nhãn “synthetic” trên UI.
