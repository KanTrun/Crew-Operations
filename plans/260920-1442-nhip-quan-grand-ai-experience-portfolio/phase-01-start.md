---
phase: 1
title: "Foundation and shared contracts"
status: pending
priority: P1
effort: "3-5 days"
dependencies: []
---

# Phase 1: Foundation and shared contracts

## Overview

Tạo ranh giới sản phẩm cho Grand AI Experience Portfolio, hợp đồng dữ liệu
dùng chung, fixture replay và adapter đọc dữ liệu. Phase này phải merge trước
các phase 2-6. Không xây feature UI đầy đủ ở phase này.

## Files to read before implementation

- `README.md`
- `docs/design-guidelines.md`
- `docs/github-operating-model.md`
- `docs/adr/ADR-002-deterministic-orchestration.md`
- `docs/adr/ADR-003-contracts-first.md`
- `docs/adr/ADR-008-anti-fake-signals.md`
- `packages/contracts/src/ca_contracts/__init__.py`
- `packages/contracts/src/ca_contracts/ops_predict.py`
- `packages/contracts/src/ca_contracts/episodic_memory.py`
- `apps/api/src/ca_api/interfaces/http/copilot_voice.py`
- `apps/web/package.json`

## Requirements

### Functional

- Define one versioned envelope for experience events, voice turns, actions,
	memories, spatial anchors, role projections and operating modes.
- Define explicit state machines for proposal, memory consent and live event.
- Provide deterministic fixture replay that works with `CA_AGENT_MODE=replay`.
- Provide a read-only adapter boundary between the new experience and NHỊP QUÁN
	existing endpoints/data. The experience layer must not import DB internals.
- Reserve routes and capability names for War Room, Shift Rescue, Rule Learning,
	HỒN QUÁN and QUÁNVERSE without granting mutation by default.

### Non-functional

- Pydantic contracts and generated TypeScript contracts stay compatible.
- All IDs are opaque strings; all timestamps are timezone-aware ISO-8601.
- Unknown enum values fail closed at write boundaries and render safely at read
	boundaries.
- No `Any` added to domain contracts. Use `object` only for bounded metadata.
- Fixtures contain no secrets, real customer data or real voice recordings.
- Contract tests run offline and do not open network connections.

## Architecture

### Product boundary

The first implementation lives in the existing Next.js application as a
separate route and module boundary, not as a second runtime. Use:

```text
apps/web/src/app/quanverse/       experience entry route
apps/web/src/ui/experience/       product UI modules
apps/api/.../http/experience.py   versioned API boundary
packages/contracts/...             shared schemas
```

The module boundary must remain portable so a later implementation can move to
an `apps/experience` runtime without changing contracts. That split is optional
and is not part of the MVP acceptance.

### Shared contract sketch

```python
class ExperienceRole(StrEnum):
		KHACH = "khach"
		NHAN_VIEN = "nhan_vien"
		QUAN_LY = "quan_ly"
		CHU_QUAN = "chu_quan"

class ExperienceProposalStatus(StrEnum):
		DRAFT = "draft"
		READY = "ready"
		CONFIRMED = "confirmed"
		REJECTED = "rejected"
		EXPIRED = "expired"

class SpatialAnchor(BaseModel):
		anchor_id: str
		khu_vuc: str
		label: str
		x: float
		y: float
		z: float = 0.0
		kind: str
		active: bool = True

class ExperienceEvent(BaseModel):
		event_id: str
		event_type: str
		occurred_at: datetime
		actor_id: str | None = None
		role: ExperienceRole | None = None
		anchor_id: str | None = None
		payload: dict[str, object] = Field(default_factory=dict)
		evidence_refs: list[str] = Field(default_factory=list)
		source: Literal["replay", "user", "system", "agent"]

class VoiceTurn(BaseModel):
		turn_id: str
		conversation_id: str
		transcript: str
		response_text: str = ""
		audio_ref: str | None = None
		intent: str | None = None
		confidence: float = Field(ge=0.0, le=1.0, default=0.0)
		proposal_id: str | None = None

class ExperienceMemory(BaseModel):
		memory_id: str
		anchor_id: str | None = None
		owner_scope: str
		content: str
		source_event_ids: list[str] = Field(default_factory=list)
		consent_status: Literal["required", "granted", "revoked", "expired"]
		visibility: Literal["private", "staff", "manager", "public"]
		status: Literal["draft", "confirmed", "superseded", "deleted"]
		retention_until: datetime | None = None

class ExperienceActionProposal(BaseModel):
		proposal_id: str
		action_type: str
		status: ExperienceProposalStatus
		snapshot_hash: str
		evidence_refs: list[str] = Field(default_factory=list)
		deterministic_result: dict[str, object] = Field(default_factory=dict)
		explanation: str = ""
```

The actual contract may rename fields to match local conventions, but it must
preserve these invariants: proposal status, evidence refs, snapshot hash,
source, actor scope and consent cannot be omitted.

### Capability policy

Add capability entries to the existing role matrix only after defining the
corresponding server-side permission. A UI button is never authorization.

```text
experience.read              all authenticated roles
experience.simulate          manager/owner
experience.propose           role-specific, server checked
experience.confirm           manager/owner or explicit customer consent
experience.memory.delete     memory owner or manager with audit reason
experience.mode.activate     manager/owner
```

## Related code files

### Create

- `packages/contracts/src/ca_contracts/grand_experience.py`
- `packages/contracts/tests/test_grand_experience_contracts.py`
- `packages/contracts/schema/GrandExperience.json`
- `packages/contracts/ts/grand-experience.ts`
- `packages/agents/src/ca_agents/grand_experience/__init__.py`
- `packages/agents/src/ca_agents/grand_experience/replay.py`
- `packages/agents/tests/test_grand_experience_replay.py`
- `data/fixtures/grand_experience/events.json`
- `data/fixtures/grand_experience/scenarios.json`
- `data/fixtures/grand_experience/spatial-map.json`
- `apps/api/src/ca_api/interfaces/http/experience.py`
- `apps/api/tests/test_experience_boundary.py`

### Modify

- `packages/contracts/src/ca_contracts/__init__.py` to export contracts.
- `packages/contracts/tests/test_contracts.py` if the repository's contract
	registry requires explicit inclusion.
- `apps/api/src/ca_api/interfaces/http/main.py` to register the router.
- `packages/contracts/schema/index` or its generated equivalent, only through
	the existing `make contracts` command.
- `docs/THIRD_PARTY.md` only if a new dependency is actually introduced.

### Do not modify in this phase

- Existing solver rules.
- Existing copilot action execution semantics.
- Existing `ops_predict` schema semantics.
- Existing customer data or production seed records.

## Implementation steps

1. Create the branch from the latest `origin/main` in a separate worktree as
	 described in Phase 07. Confirm the worktree is clean before editing.
2. Define enums, models, validators and error codes in the contracts package.
3. Add the TypeScript mirror/generated output and run the repository contract
	 generator. Never hand-edit generated output after generation.
4. Add fixture IDs and deterministic replay ordering. Replay must be stable
	 when JSON object key order changes.
5. Implement `ExperienceReadAdapter` as a narrow protocol. Add a fixture
	 implementation and a production adapter that calls existing public service
	 functions only.
6. Add the API health/capability endpoint:
	 `GET /api/v1/experience/capabilities`.
7. Add an audit event helper that records proposal/consent decisions without
	 storing raw audio or secrets.
8. Add contract tests for valid, invalid, stale, unauthorized and revoked
	 payloads.
9. Run `make contracts`, targeted tests, mypy/ruff and web typecheck.
10. Stop and replan if the shared contract requires direct imports from an API
		router or DB module. That would violate the product boundary.

## Test scenario matrix

| Case | Expected result |
|---|---|
| Valid event with anchor/evidence | Accepted and replayable |
| Unknown event type | Rejected at write boundary |
| Proposal missing snapshot hash | Rejected; no action execution |
| Consent revoked | Memory retrieval excludes it |
| Customer visibility requested by staff | 403 and audit event |
| Fixture replay twice | Byte-equivalent deterministic result |
| Malformed timestamp/ID | 422 with safe public error |
| Network unavailable in replay | Replay still completes |

## Todo

- [ ] Create contracts and exports.
- [ ] Generate and validate JSON/TypeScript contracts.
- [ ] Add replay fixtures and deterministic adapter.
- [ ] Register read-only API boundary.
- [ ] Add contract, architecture and no-network tests.
- [ ] Run all phase gates and record outputs in the PR description.

## Success criteria

- [ ] `make contracts` passes.
- [ ] `pytest packages/contracts/tests/test_grand_experience_contracts.py packages/agents/tests/test_grand_experience_replay.py apps/api/tests/test_experience_boundary.py -q` passes.
- [ ] `ruff check` and `mypy --strict` pass for touched Python files.
- [ ] `cd apps/web; npm run typecheck` passes.
- [ ] `ak plan validate` remains green.
- [ ] Phase 02-06 can import contracts without importing each other.

## Risk assessment

- **Risk:** generated TypeScript diverges from Pydantic. **Signal:** contract
	snapshot diff or web type error. **Response:** regenerate; do not patch output.
- **Risk:** new route accidentally exposes mutation. **Signal:** boundary test
	sees write without proposal/permission. **Response:** remove endpoint and add
	a proposal-only route.
- **Risk:** existing pending plan changes the same contract. **Signal:** merge
	conflict or incompatible field names. **Response:** stop, compare with
	`260918-nhip-quan-os-brain`, add ADR, then continue; never silently rename.

## Security and privacy

- Do not put API keys, raw audio, personal phone numbers or real customer names
	in fixtures.
- Validate authenticated store scope on every API call.
- Hash snapshots for stale detection; do not expose internal DB paths.
- Log decision metadata, not transcript/audio content by default.

## Handoff

After this phase is merged, Phase 02-06 may start in separate branches. Every
later phase must use these contracts and must add fields backward-compatibly.
