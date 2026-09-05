# AG-COPILOT Rollout Runbook

## Release gates

1. Run the focused safety suites:
   `python -m pytest -q apps/api/tests/unit/test_copilot_api.py apps/api/tests/unit/test_mail_quality_gate.py`
2. Run the deterministic agent replay suite:
   `python -m pytest -q packages/agents/tests/test_no_network.py packages/agents/tests/test_ag_copilot.py`
3. Run web validation from `apps/web`:
   `npm run typecheck`
   `npm run build`
4. Confirm no real credentials, SMTP settings, channel tokens, or production database are present in replay CI.

## Feature flags

- Keep mutating Copilot intents disabled in production during test-only and shadow phases.
- Enable one intent per store, in this order: inventory draft, rule proposal, schedule, shift swap, mail.
- Keep mail last. Require an exact content hash and an idempotency key for every external send.

## Approval and stale handling

- Only `ready_for_approval` may be approved or rejected.
- `stale_rejected` and `expired` are terminal for the proposal. Create a new proposal from current data.
- Never edit the stored snapshot hash to force approval.
- Cross-tenant action reads and execution must return an authorization failure without exposing payload details.

## Mail outcomes

- `sent`: the adapter returned a successful send result; the action may become `executed`.
- `transport_failed`: the adapter failed before a send was confirmed; keep the action failed and require review.
- `delivery_unknown`: transport state is uncertain. Do not retry blindly. Reconcile using the durable delivery receipt and provider message ID.
- Reusing the same store-scoped idempotency key replays the stored outcome. A different request with the same key is a conflict.

## Rollback

1. Disable the affected intent flag for the store.
2. Do not delete draft, receipt, or audit rows.
3. Reconcile actions left in `executing` before enabling the intent again.
4. Do not retry `delivery_unknown` until the external provider has been reconciled.
5. Redeploy the previous application version only if it can read the new state values; do not run a destructive schema rollback.

## Evidence to record

Record the release commit, interpreter version, focused suite result, web build result, enabled store/intent, stale rate, execution failure rate, cross-tenant denials, and mail outcome counts. Never record raw mail bodies, tokens, passwords, or secrets.
