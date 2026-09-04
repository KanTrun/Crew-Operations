# AI Learning Loop Runbook

## PR 1 boundary

PR 1 persists generation, feedback, evaluation, and rule-proposal records only. It does not enable automatic learning, rule activation, auto-send, or model rollout.

## Tenant scope

`users.store_id` is the server-side source of tenant identity. Login copies it into `sessions.store_id`; API callers do not supply tenant identity. Existing users and sessions migrate to `quan_01`. New registrations use `NHIPQUAN_DEFAULT_STORE_ID`, defaulting to `quan_01`, until a multi-store administration flow exists.

Every AI Learning repository read requires `store_id`. Records use tenant-scoped idempotency keys. Investigations must query the tenant named in the incident rather than attempting a global record export.

## Facebook idempotency

Messenger receipts use SHA-256 of `store_id:page_id:event_type:external_event_id`. A duplicate is acknowledged without running moderation, agent generation, Graph API calls, or persistence again. An inbound message without `mid` is ignored; there is no timestamp fallback.

Public Facebook-comment ingestion and reply handling do not exist in this PR. Consequently, no live comment path currently calls the receipt helper with `event_type="comment"` and `comment_id`; Messenger dedupe must not be described as comment dedupe. The helper supports that scoped input when a comment handler is approved and implemented.

## Data protection

In `NHIPQUAN_ENV=production`, deployment infrastructure must set `NHIPQUAN_ENCRYPTED_VOLUME_VERIFIED=true` only after it has verified the database volume/disk encryption control. The service cannot portably inspect host disk encryption itself.

Missing or false attestation logs a critical event and sets AI Learning to minimal-data mode. The persistence boundary redacts email addresses, Vietnamese phone numbers, and direct-identifier fields; minimal-data mode hashes draft and feedback content. Check `/health` for `minimal_data_mode`.

## Gmail quality gate

`POST /api/v1/mail/send` evaluates every resolved recipient, subject, body, and optional `ops_context` before calling the mail transport. The deterministic Gmail score is `0.30 accuracy + 0.20 safety + 0.15 completeness + 0.15 tone + 0.10 actionability + 0.10 personalization`; `threshold_version` is `gmail-v1`. The lookup receives the authoritative session `store_id`, while the persisted evaluation contains that store scope and `channel=gmail`. A send requires score at least `0.80`, accuracy and safety at least `0.90`, and no hard-fail flag.

Missing or invalid recipients, factual mismatch with supplied operational context, internal-data exposure, and prompt injection are hard failures and block transport. Missing subject prefix, placeholders, financial commitments, missing greeting/signature, and unusual length queue the message for review. Every attempt records a generation plus manager approve/reject feedback; successful or failed transport records a system send outcome. Supplying `original_subject` and `original_body` records exact subject/body differences in the feedback event.

## Backup and recovery

`AILearningRepository.backup(store_id=..., directory=...)` writes an atomic per-store JSON snapshot plus a `.sha256.json` manifest. By default it writes to `data/backups` under the repository root; `NHIPQUAN_AI_LEARNING_BACKUP_DIR` overrides that path. The manifest records backup format/schema versions, timestamp, store coverage, per-record-type counts, snapshot filename, and SHA-256 checksum. `AILearningRepository.verify_backup(...)` must return true before a restore workflow accepts a snapshot; a mismatch means the file is tampered or corrupt and must be rejected.

Checksum is integrity control only, not encryption at rest. In production, backups require both `NHIPQUAN_ENCRYPTED_VOLUME_VERIFIED=true` and an absolute `NHIPQUAN_ENCRYPTED_DATA_ROOT`; the chosen output path must be under that root or backup fails closed. Infrastructure must mount both the SQLite/WAL files and this root on the same attested encrypted volume. Any future offsite sync must use provider-managed encryption with customer-managed keys (or equivalent envelope encryption), restricted service credentials, and independent retention/access auditing.

PR 1 provides the verified backup primitive, not a scheduler. Production operations still need an approved schedule for daily snapshots, hourly WAL handling, 35-day online retention, and monthly archival snapshots. Reflection, proposal review, and active-rule promotion remain deferred. Do not treat persisted records as approved knowledge.