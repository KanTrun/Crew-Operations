# ADR-015: Human-Gated AI Learning Records

## Decision

Store tenant-scoped, redacted AI generation, feedback, evaluation, and rule-proposal records in the API persistence layer. Use deterministic quality gates and reflection for evidence aggregation. Require owner approval and activation for every rule transition.

## Consequences

Agents remain pure: they receive active rules but do not access API persistence or activate rules. The repository checks same-store references and idempotency. Active rules are deterministically ordered and only `active` records are injected. Ambiguous semantic conflicts remain an owner decision.

The circuit breaker is an operational override. It blocks Gmail before transport and forces Messenger through human review. Integrity manifests and encrypted-volume attestation are separate controls: SHA-256 verifies data integrity, while environment-attested storage boundaries control encryption-at-rest policy.# ADR-015: AI generation feedback learning persistence

## Status

Accepted for PR 1.

## Context

AG-FBPAGE and AG-MAILWRITER need an auditable learning loop without allowing an LLM to activate behavior or bypass human approval. The system also needs a tenant boundary before multi-store administration exists.

## Decision

Four strict contracts form the persistence boundary: `AIGenerationRecord`, `AIFeedbackEvent`, `AIEvaluation`, and `AIRuleProposal`. Each requires `store_id`. SQLite rows retain validated payloads plus queryable tenant, channel, idempotency, and time fields.

`users.store_id` is authoritative. The server copies it into the session at authentication. Existing data is migrated to `quan_01`; registrations receive the server configuration `NHIPQUAN_DEFAULT_STORE_ID`, never a request-provided tenant.

Facebook Messenger retry receipts are atomic and scoped by tenant, Page, event type, and external message ID. Missing external IDs do not enter the pipeline.

Production encryption-at-rest is provided by an infrastructure-managed encrypted volume. `NHIPQUAN_ENCRYPTED_VOLUME_VERIFIED=true` is a deployment attestation. If absent in production, the process enters minimal-data mode for AI Learning persistence. SQLCipher remains future defense-in-depth work, not a PR 1 dependency.

## Consequences

### Backup integrity and comment scope

PR 1 writes tenant-scoped AI Learning snapshots with a SHA-256 manifest. Snapshot acceptance requires matching schema version, store coverage, and checksum before restore. Scheduling and retention automation are operational follow-up work, not implied by the snapshot primitive.

The Facebook scoped-receipt helper is live for Messenger `mid` events only. Public-comment ingestion and reply handling do not yet exist, so public-comment `comment_id` dedupe is not a deployed behavior.

PR 1 makes no decision to auto-send, activate a rule, or promote a model. Later PRs must use this repository and preserve the server-derived tenant scope. The operational runbook documents recovery and attestation responsibilities.