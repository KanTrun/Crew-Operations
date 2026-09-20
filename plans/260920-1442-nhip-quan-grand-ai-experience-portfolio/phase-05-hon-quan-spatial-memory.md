---
phase: 5
title: "HON QUAN Spatial Memory and AI Tour Guide"
status: pending
priority: P1
effort: "8-12 days"
dependencies: [1]
---

# Phase 5: HỒN QUÁN Spatial Memory and AI Tour Guide

## Overview

Xây một bản đồ không gian 2D/isometric có progressive 3D, nơi sự cố, quy trình,
ghi chú thoại, lời khen và ký ức vận hành được gắn với khu vực hoặc đồ vật.
Người dùng hỏi bằng giọng nói, nghe trả lời, xem timeline bằng chứng và có thể
đề xuất ký ức mới. AI Tour Guide dùng cùng memory retrieval để dẫn onboarding;
nó không trở thành một chatbot không nguồn.

## Evidence and reuse

- Reuse `ag_explain/episodic_memory.py` only through a spatial memory adapter;
	current `Episode` lacks anchor/consent fields and must not be mutated silently.
- Reuse authenticated `copilot_voice` transport, but add an experience voice
	intent scope. Do not expose raw Gemini connection to the browser.
- Reuse existing 3D asset/rendering conventions and design tokens. Use CSS/SVG
	fallback before adding a model/asset dependency.

## Requirements

### Spatial memory

- Map contains seeded areas and anchors: bar, cashier, stockroom, entrance,
	window table, blender-02, fridge-01, espresso-machine-01.
- Selecting an anchor shows current status, confirmed memories, draft
	memories, evidence timeline and related SOPs.
- Queries can filter by anchor, time range, event type, role visibility and
	confirmation state.
- Every result shows the memory `status` (`draft`, `confirmed`, `superseded`,
	`deleted`) and the consent state (`required`, `granted`, `revoked`,
	`expired`). "Pending" is the user-facing label for `status=draft`; it is not
	a separate enum value.
- Memory creation from text/voice produces a proposal. Manager confirmation or
	explicit customer consent is required before storage as confirmed memory.

### Voice and tour

- Voice input: “Ở đây từng xảy ra chuyện gì?”, “Nhớ điều này...”, “Dẫn tôi đi
	qua khu vực mở quán”.
- Voice output has synchronized transcript and a stop/replay control.
- Text input and browser TTS/replay remain available when Gemini Live is off.
- Tour steps are deterministic anchor sequences with grounded narration; LLM
	may phrase but may not add unsupported facts.

### Privacy

- Customer preference memory requires explicit consent, visibility, retention
	and delete path.
- No face recognition, biometric inference, or hidden identity linking.
- Raw audio is not retained by default; transcript may be retained only when a
	user confirms the memory proposal.
- Customer can inspect/delete their own memories; manager deletion requires an
	audit reason and does not hide the audit event.

## Architecture

```text
Map click / voice turn / text
						|
						v
Anchor resolver + role/consent context
						|
						+--> deterministic memory retrieval (anchor/time/status)
						+--> evidence resolver (event refs only)
						+--> tour planner (closed anchor graph)
						|
						v
Grounded context packet
						|
						v
LLM wording/voice adapter or replay responder
						|
						v
Response + citations + optional MemoryProposal
						|
						v
Human/customer consent -> memory store + audit
```

### Memory data model

Use a relational/KV storage adapter, not an in-memory browser store as the
source of truth:

```text
spatial_anchors(anchor_id, store_id, kind, label, x, y, z, metadata_json)
experience_events(event_id, store_id, anchor_id, type, occurred_at, source, payload_json)
experience_memories(memory_id, store_id, anchor_id, owner_scope, content,
	consent_status, visibility, status, retention_until, created_by, evidence_json)
memory_audit(memory_id, action, actor_id, reason, occurred_at)
```

Add indexes for `(store_id, anchor_id, occurred_at)` and `(owner_scope, status)`.
Do not add vector search in MVP. Deterministic filtering and bounded keyword
search are easier to audit; vector retrieval is a later ADR if needed.

### API contract

```text
GET  /api/v1/experience/map
GET  /api/v1/experience/anchors/{anchor_id}
GET  /api/v1/experience/memories?anchor_id=&from=&to=&status=
POST /api/v1/experience/memories/propose
POST /api/v1/experience/memories/{memory_id}/consent
DELETE /api/v1/experience/memories/{memory_id}
POST /api/v1/experience/tour/start
POST /api/v1/experience/voice/turn
```

`voice/turn` returns `transcript`, `response_text`, `citations`, optional
`audio_ref` and optional proposal. It never returns a direct DB mutation.

## Related code files

### Create

- `packages/contracts/src/ca_contracts/spatial_memory.py`
- `packages/contracts/tests/test_spatial_memory_contracts.py`
- `packages/agents/src/ca_agents/ag_spatial_memory/__init__.py`
- `packages/agents/src/ca_agents/ag_spatial_memory/retrieval.py`
- `packages/agents/src/ca_agents/ag_spatial_memory/grounding.py`
- `packages/agents/src/ca_agents/ag_spatial_memory/tour.py`
- `packages/agents/tests/test_spatial_memory_retrieval.py`
- `packages/agents/tests/test_spatial_memory_grounding.py`
- `apps/api/src/ca_api/interfaces/http/spatial_memory.py`
- `apps/api/tests/test_spatial_memory_api.py`
- `apps/web/src/app/quanverse/spatial-memory/page.tsx`
- `apps/web/src/ui/experience/spatial/SpatialMap.tsx`
- `apps/web/src/ui/experience/spatial/SpatialMap2dFallback.tsx`
- `apps/web/src/ui/experience/spatial/SpatialAnchorDetails.tsx`
- `apps/web/src/ui/experience/spatial/MemoryTimeline.tsx`
- `apps/web/src/ui/experience/spatial/VoiceDock.tsx`
- `apps/web/src/ui/experience/spatial/TourGuide.tsx`
- `apps/web/e2e/spatial-memory.spec.ts`
- `data/fixtures/grand_experience/spatial-memory.json`
- `infra/templates/spatial-map.json` if map seed is treated as a config template

### Modify

- `packages/contracts/src/ca_contracts/__init__.py` exports.
- `apps/api/src/ca_api/interfaces/http/main.py` router registration.
- `apps/web/src/ui/icons.tsx` only for needed non-emoji controls.
- `apps/web/src/ui/experience/experience-api.ts` typed endpoints.
- `apps/web/src/app/AppShell.tsx` only to expose authorized route.
- `docs/design-guidelines.md` only if the experience register becomes durable
	product authority; read/update smallest owning section.

## UI/UX contract

- Spatial map is the first viewport signal; no decorative fake 3D scene.
- Selected anchor has a stable focus target and keyboard equivalent.
- Memory timeline is a real list, not floating labels only.
- Voice dock shows recording, processing, response, unavailable and replay states.
- Use warm dark/copper atmosphere only within existing guidelines; avoid a
	purple or generic sci-fi dashboard.
- Camera motion is T1/T2 only and disabled under reduced motion.
- 2D fallback must have identical anchor IDs and actions.

## Implementation steps

1. Write contracts and privacy tests before persistence.
2. Add anchor/event/memory repositories with an interface and fixture backend.
3. Implement deterministic retrieval and citation construction.
4. Implement consent and retention state transitions with audit events.
5. Implement grounded response context; reject/qualify unsupported claims.
6. Connect authenticated voice turn to existing server-side voice transport;
	 provide replay responder and text fallback.
7. Build 2D map first, then progressive 3D layer using existing dependencies.
8. Add AI Tour Guide as deterministic path + grounded narration.
9. Add customer memory controls: view, consent, revoke/delete, retention label.
10. Run privacy, no-network, keyboard, reduced-motion and e2e tests.

## Test scenario matrix

| Case | Expected result |
|---|---|
| Anchor selected by mouse | Details and timeline load |
| Same anchor selected by keyboard | Same result and visible focus |
| Query with no memories | “Chưa có ký ức đã xác nhận”, no hallucinated story |
| Pending memory (status=draft) | Clearly labeled; excluded from confirmed answer |
| Revoked memory (consent revoked) | Not retrieved; audit remains |
| Customer grants consent | Confirmed preference appears only in allowed scope |
| Customer refuses consent | Proposal discarded; no retained audio |
| Staff requests private customer memory | Redacted/403 |
| Unsupported LLM claim | Grounding gate qualifies or rejects it |
| Voice unavailable | Text/replay response works |
| WebGL unavailable | 2D map works |
| Reduced motion | No camera animation; focus moves logically |
| Retention expires | Memory becomes expired and is excluded |
| Delete request | Content removed from retrieval and audit recorded |

## Todo

- [ ] Add spatial memory contracts and schema migration/adapter.
- [ ] Add deterministic anchor retrieval and grounding.
- [ ] Add consent, retention and deletion audit.
- [ ] Add voice turn and replay fallback.
- [ ] Build 2D map and progressive 3D layer.
- [ ] Build timeline, memory proposal and AI Tour Guide.
- [ ] Add privacy, accessibility, performance and e2e tests.

## Success criteria

- [ ] User can select an anchor, ask a question and hear/read a grounded answer.
- [ ] User can create a draft memory and confirm it through the correct actor.
- [ ] Confirmed memory is retrievable in a later replay session.
- [ ] Revoked/deleted memory is not retrievable.
- [ ] No raw audio is retained without explicit policy/consent.
- [ ] `npx playwright test e2e/spatial-memory.spec.ts` passes with WebGL disabled.
- [ ] Voice and 3D are optional enhancements, not single points of failure.

## Risk assessment

- **Risk:** feature becomes an attractive 3D map with weak utility. **Signal:**
	e2e only checks rendering, not retrieval/consent. **Response:** block phase on
	the anchor question -> grounded evidence -> confirmed memory flow.
- **Risk:** “memory” stores sensitive data indefinitely. **Signal:** any record
	lacks owner, retention or consent status. **Response:** reject at contract
	validation and run retention cleanup before release.
- **Risk:** voice provider changes or fails. **Signal:** live session unavailable
	in replay or demo. **Response:** use text/replay/audio fixture and label live
	state honestly.

## Security and rollback

- Authenticate every store-scoped read/write; apply role projection server-side.
- Sanitize transcript before persistence and enforce size/rate limits.
- Do not expose audio URLs without short-lived authorization.
- Rollback leaves map route disabled and preserves only existing non-spatial
	episodic memory; migration down must be tested before production rollout.

## Handoff

Phase 06 consumes anchors, confirmed events and role projections. It must not
write memories directly; it uses Phase 05 consent/proposal APIs.
