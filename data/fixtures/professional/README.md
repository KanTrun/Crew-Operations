# Professional synthetic fixture

This bundle is a deterministic, reviewable dataset for local demo and integration testing. It is not real customer or staff data.

## Contents

- `base.json`: 10 staff, 21 shifts, assignments, availability, leave, schedule lifecycle.
- `pos.json`: menu/BOM, active and hidden items, orders for POS/KDS, attendance, inventory catalog and snapshots.
- `operations.json`: checklist runs, pending work, inbox constraints, swaps, playbook rules, schedule edits and handover.
- `channels.json`: Telegram/Zalo bindings, replay messages, Facebook Page threads/drafts and webhook payloads.
- `manifest.json`: version, scenarios, counts, load order and reference rules.

Every bundle is marked `synthetic: true` and `nguon: mo_phong_fixture`. Stable `fx_` IDs make reruns and assertions deterministic.

## Validate

From the repository root on Windows:

```text
py scripts/validate_professional_fixture.py
```

The validator is read-only. It checks JSON syntax, expected status coverage, and foreign-key-like references between records.

## Scenarios

- `manager-dashboard`: base + operations
- `pos-kds-active`: base + pos
- `checklist-in-progress`: base + operations
- `inbox-review`: base + operations + channels
- `channels-replay`: base + channels

This bundle is intentionally separate from `data/seed/sample.json` until an application-specific idempotent loader maps these records to the SQLite/KV store. Do not label these records as data from a real cafe.

## Load into local SQLite

From the repository root on Windows:

```text
"C:\Program Files\Python310\python.exe" scripts/seed_professional_fixture.py
```

The loader keeps the three existing demo accounts, adds seven fixture staff accounts (`an`, `bao`, `chi`, `dung`, `thao`, `quan`, `yen`, password `nhipquan`), and materializes the POS, schedule, checklist, inbox, inventory, bind, and Page surfaces. It is idempotent for fixture IDs and does not remove non-fixture records.
