# AI Incident Response

1. Open the channel circuit breaker as owner:
   `POST /api/v1/ai/operations/circuit-breaker` with `channel` and `open: true`.
2. Gmail then returns `503 ai_circuit_breaker_open` before mail transport. Facebook Messenger is forced to manager review.
3. Pause the suspected active rule. Preserve generation, evaluation, and feedback evidence; do not delete it during investigation.
4. Review `GET /api/v1/ai/evaluations/summary` and the rule evidence IDs. Roll back the rule when it should not return.
5. Re-open traffic only after an owner approves the remediation and circuit breaker is set to `open: false`.