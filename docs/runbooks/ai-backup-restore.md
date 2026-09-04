# AI Learning Backup and Restore

AI learning snapshots include generation, feedback, evaluation, and rule-proposal records. The manifest SHA-256 values prove snapshot integrity only; they do not prove encryption at rest.

In production, backup creation must run with both:

- `NHIPQUAN_ENCRYPTED_VOLUME_VERIFIED=true`
- an absolute `NHIPQUAN_ENCRYPTED_DATA_ROOT` containing the backup path

The persistence layer fails closed if this attestation is missing or the path is outside the configured root. Verify a backup manifest before a restore and test restores only in an isolated environment. Preserve tenant boundaries and do not copy one store's learning records into another store.