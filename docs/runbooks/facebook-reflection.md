# Facebook Learning Runbook

The deployed inbound integration is Messenger-only. Its idempotency key is the Messenger `mid` scoped by store, Page, and event type. This system does not claim public Facebook comment ingestion or comment deduplication.

When a Messenger event is processed, the API records a tenant-scoped generation and deterministic policy evaluation. Active Facebook rules are supplied to `process_fb_message(active_rules=...)` only for live prompt construction; the existing safety and policy gates retain final control.

Owner rule lifecycle endpoints are shared with Gmail:

- `GET /api/v1/ai/rules/proposals?channel=facebook`
- `POST /api/v1/ai/rules/proposals/{id}/approve`
- `POST /api/v1/ai/rules/proposals/{id}/activate`
- `POST /api/v1/ai/rules/{id}/pause`
- `POST /api/v1/ai/rules/{id}/rollback`

If the Facebook circuit breaker is open, Messenger responses are forced to the review queue. It never silently continues auto-send.