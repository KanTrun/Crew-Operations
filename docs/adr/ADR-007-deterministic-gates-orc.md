# ADR-007 — Cổng kiểm chứng và điều phối tất định

- Status: accepted
- Date: 2026-08-22

## Decision

Bộ điều phối là máy trạng thái + idempotency store + dispatch song song. Agent không ghi DB (ADR-002). Clock tiêm được (`Clock` / `FrozenClock`).

## Consequences

`make replay` của phiên nằm ở khóa idempotency + FrozenClock; không dùng LLM điều phối.
