---
phase: 2
title: "War Room Digital Twin and Cafe Crisis Room"
status: pending
priority: P1
effort: "6-9 days"
dependencies: [1]
---

# Phase 2: War Room Digital Twin and Cafe Crisis Room

## Overview

Đóng gói AG-TWIN/AG-PREDICT hiện có thành một phòng điều hành trực quan: người
quản lý đặt câu hỏi "nếu... thì...", hệ thống chạy nhiều phương án tất định,
kiểm tra ràng buộc thật, hiển thị trade-off và chỉ đưa ra proposal chờ duyệt.
Cafe Crisis Room là bộ preset tình huống cho mưa lớn, giờ cao điểm, thiếu
người, khách đoàn và thiết bị hỏng.

## Evidence and reuse

- Reuse `packages/agents/src/ca_agents/ag_twin/simulator.py` and
	`virtual_staff.py`; do not duplicate price elasticity or workload math.
- Reuse `packages/agents/src/ca_agents/ag_predict/math_layer.py` and existing
	`TwinScenario`/`SuccessPattern` contracts.
- Reuse `/api/v1/ops/twin/simulate` from `ops_predict.py` through an adapter;
	add new endpoints only for multi-scenario orchestration and War Room view.
- Reuse solver and fairness services. War Room must never calculate a new
	roster in TypeScript.

## Requirements

### User-visible

- Manager can ask for a scenario by text; voice is wired by Phase 05/06 but the
	War Room must also work with a text command and replay fixture.
- System produces at least two comparable options plus a baseline.
- Each option shows: input assumptions, deterministic outputs, staffing/load,
	fairness impact, estimated cost/revenue where available, risk, evidence and
	stale-data state.
- Manager can inspect why an option was rejected by a hard constraint.
- Manager can save a proposal for confirmation; no simulation changes real data.
- Crisis Room supports presets without pretending to sense real weather or IoT.
	Fixture weather/events must be visibly labeled synthetic/replay.

### Safety

- LLM parses intent only. It cannot supply numeric output or call the solver.
- Math layer owns all numbers. Every number has a source field or is marked
	`estimated`.
- CP-SAT/gates own hard constraints. A profitable but unsafe option is still
	rejected.
- Baseline snapshot hash is required. A stale baseline invalidates confirmation.
- All simulations are idempotent by request fingerprint.

## Architecture

```text
Text/voice request
			 |
			 v
Intent parser (LLM or replay)
			 |
			 v
WarRoomCommand (validated)
			 |
			 +--> deterministic scenario builder
			 |          |
			 |          +--> AG-TWIN math
			 |          +--> CP-SAT feasibility check
			 |          +--> fairness/load calculators
			 |
			 v
WarRoomComparison + evidence + risks
			 |
			 v
ExperienceActionProposal (DRAFT/READY)
			 |
			 v
Human confirmation -> existing action pipeline, never direct DB mutation
```

### Scenario types

Use a closed enum and explicit parameter schemas:

```text
demand_surge
add_staff_to_shift
remove_staff_from_shift
equipment_outage
heavy_rain
large_group_arrival
```

`equipment_outage` and `heavy_rain` change capacity/operating context, not
actual hardware or weather. They are simulations until confirmed.

### API contract

```text
POST /api/v1/experience/war-room/simulate
	body: {request_id, baseline_snapshot, scenarios[], requested_by}
	result: {simulation_id, baseline, options[], proposal, replayable}

GET /api/v1/experience/war-room/scenarios/{simulation_id}

POST /api/v1/experience/war-room/{simulation_id}/propose
	body: {option_id, expected_snapshot_hash}

POST /api/v1/experience/war-room/{simulation_id}/confirm
	manager-only; delegates to existing proposal confirmation path
```

Never add a `POST .../apply` endpoint that bypasses proposal confirmation.

## Related code files

### Create

- `packages/agents/src/ca_agents/ag_war_room/__init__.py`
- `packages/agents/src/ca_agents/ag_war_room/command.py`
- `packages/agents/src/ca_agents/ag_war_room/orchestrator.py`
- `packages/agents/src/ca_agents/ag_war_room/evidence.py`
- `packages/agents/tests/test_war_room_orchestrator.py`
- `packages/agents/tests/test_war_room_determinism.py`
- `apps/api/src/ca_api/interfaces/http/war_room.py`
- `apps/api/tests/test_war_room_api.py`
- `apps/web/src/ui/experience/war-room/WarRoom.tsx`
- `apps/web/src/ui/experience/war-room/ScenarioPicker.tsx`
- `apps/web/src/ui/experience/war-room/ScenarioComparison.tsx`
- `apps/web/src/ui/experience/war-room/CrisisRoom.tsx`
- `apps/web/src/ui/experience/war-room/war-room-model.ts`
- `apps/web/e2e/war-room.spec.ts`
- `data/fixtures/grand_experience/war-room.json`

### Modify

- `apps/api/src/ca_api/interfaces/http/main.py` to register `war_room`.
- `packages/contracts/src/ca_contracts/grand_experience.py` only for additive
	scenario/comparison fields from Phase 01.
- `apps/web/src/ui/experience/experience-api.ts` for typed calls.
- Existing `ops_predict` only through a compatibility adapter if required;
	do not change its public semantics without an ADR.

## UI/UX contract

- Main visual: baseline in the center, scenario options as a comparison rail.
- A “Why” drawer shows constraint IDs, source refs and assumptions.
- Use project Fraunces/Source Sans 3/IBM Plex Mono fonts and copper/charcoal
	tokens from `docs/design-guidelines.md`; War Room is an experience register,
	not a marketing hero.
- Keep numbers scannable; label every synthetic value as `Mô phỏng`.
- Use keyboard-selectable scenario cards, visible focus, `aria-live` only for
	status updates, and a reduced-motion path.
- A static SVG/isometric fallback must render when WebGL is unavailable.

## Implementation steps

1. Write red tests for deterministic command normalization, scenario validation,
	 stale snapshot and hard-constraint rejection.
2. Build a scenario adapter around existing AG-TWIN math. Map typed parameters;
	 reject unknown parameters instead of silently defaulting them.
3. Add CP-SAT feasibility checks for staffing scenarios. Return structured
	 reason codes, not prose generated by the model.
4. Add multi-scenario orchestration with stable ordering and request hash.
5. Add evidence builder. Each output number must point to an input row,
	 deterministic function or solver result.
6. Add proposal creation through the existing Copilot proposal/audit mechanism.
7. Implement War Room comparison UI and Crisis Room presets.
8. Add replay mode with the same visible states as live mode.
9. Add API and Playwright tests, then benchmark 3/5/10 scenarios.

## Test scenario matrix

| Scenario | Gate |
|---|---|
| Same input twice | Same option IDs, values and ordering |
| Missing demand baseline | 422 or explicit `insufficient_data`, never invented data |
| Add staff violates class/TKB | Option rejected with C01/C02 reason |
| Add staff raises profit but worsens fairness | Shown as trade-off; never hidden |
| Equipment outage removes capacity | Crisis option visible; no real device write |
| Stale snapshot at confirmation | 409; proposal cannot confirm |
| Unauthorized employee tries simulate manager data | 403 |
| Duplicate request ID | Idempotent result |
| WebGL unavailable | 2D fallback still supports all actions |
| Reduced motion | No camera fly-through; same information available |

## Todo

- [ ] Add War Room command/result contracts.
- [ ] Wrap existing deterministic twin math.
- [ ] Add solver feasibility and fairness comparison.
- [ ] Add API proposal boundary and audit events.
- [ ] Build comparison UI and Crisis Room presets.
- [ ] Add replay fixtures, unit, API and e2e tests.
- [ ] Run `make contracts`, `make test-unit`, web typecheck and e2e smoke.

## Success criteria

- [ ] Manager can compare baseline plus at least two options in one screen.
- [ ] Every displayed numeric result has evidence or an explicit estimate label.
- [ ] No simulation mutates schedule, inventory, rules or memory.
- [ ] One Crisis Room preset reaches a human confirmation screen in replay mode.
- [ ] `pytest packages/agents/tests/test_war_room_orchestrator.py packages/agents/tests/test_war_room_determinism.py apps/api/tests/test_war_room_api.py -q` passes.
- [ ] `cd apps/web; npm run typecheck` and `npx playwright test e2e/war-room.spec.ts` pass.

## Risk assessment

- **Risk:** existing twin math is too simplistic for a product claim. **Signal:**
	reviewers see only price arithmetic and no roster/constraint impact.
	**Response:** keep the output labeled estimate and require at least one solver
	feasibility dimension before calling it a War Room result.
- **Risk:** multi-scenario job becomes slow. **Signal:** p95 replay latency
	exceeds 2 seconds for three scenarios. **Response:** cache by snapshot and
	scenario hash; keep deterministic serial fallback; do not add background
	complexity before measuring.
- **Risk:** users mistake simulation for forecast. **Signal:** UI test finds a
	number without `Mô phỏng/ước tính`. **Response:** fail UI contract test.

## Security and rollback

- Check store scope and manager role server-side.
- Limit scenario count and payload size; rate-limit simulation endpoints.
- Do not log full prompts or customer text in audit logs.
- Rollback is deleting the War Room router/UI modules and disabling the feature
	flag; existing `/api/v1/ops/twin/*` remains untouched.

## Handoff

Phase 04 may consume War Room decision events as evidence. It must consume the
event contract, not import `ag_war_room` internals.
