# ADR-010 — Cẩm nang 8 bước fail-closed

- Status: accepted
- Date: 2026-08-22

## Decision

Đúng §9.2: ghi nhận → tìm mẫu (≥3) → AG-RULE một câu → VF-RULE → tập sự 5 lần im lặng → người duyệt → tham số lõi → theo dõi, tự tắt <80%. Năm loại luật §9.1. Cấm luật về người.

## Consequences

Trên đường fixture, bằng chứng là **dựng lại 8 tuần** (`synthetic: true`). Số luật quán thật = 0 cho đến khi có đối tác.
