# Gmail Reflection Runbook

1. A manager sends a reviewed mail through `/api/v1/mail/send`. The route records a generation, deterministic evaluation, manager feedback diff, and transport outcome under the authenticated store.
2. A manager runs `POST /api/v1/ai/reflection/gmail/run`. Reflection is deterministic and proposes a style rule only after at least three materially edited feedback events show the same greeting or signoff pattern.
3. The owner lists proposals with `GET /api/v1/ai/rules/proposals?channel=gmail` and reviews the evidence IDs.
4. Only `chu_quan` may approve and activate a rule:
   - `POST /api/v1/ai/rules/proposals/{id}/approve`
   - `POST /api/v1/ai/rules/proposals/{id}/activate`
5. Stop a rule immediately with `POST /api/v1/ai/rules/{id}/pause` or retire it with `POST /api/v1/ai/rules/{id}/rollback`.

Activated Gmail rules are returned by `get_active_mail_rules_for_store` and passed to `draft_email(active_style_rules=...)`. Pending, rejected, paused, and rolled-back rules must not influence a draft.

The deterministic quality gate remains authoritative. Reflection rules never bypass score thresholds, hard-fail checks, recipient validation, or the Gmail circuit breaker.