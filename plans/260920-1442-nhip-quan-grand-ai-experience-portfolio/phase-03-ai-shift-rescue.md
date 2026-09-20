---
phase: 3
title: "AI Shift Rescue"
status: pending
priority: P1
effort: "5-8 days"
dependencies: [1]
---

# Phase 3: AI Shift Rescue

## Overview

Xây luồng xử lý nhân viên vắng đột xuất từ một câu nói hoặc tin nhắn đến danh
sách người thay ca hợp lệ, có kiểm tra kỹ năng, TKB, nghỉ tối thiểu, trần giờ,
công bằng và quyền xác nhận. Đây là sản phẩm con hỗ trợ toàn quán, không phải
một scheduler mới và không tự đổi lịch.

## Evidence and reuse

- Existing `/api/v1/cho-doi-ca`, inbox, roster and solver policies are the source
	of truth for hard constraints.
- Existing `AG-MSG`/Copilot intent parsing may extract the absence report, but
	deterministic backend normalizes actor, shift and time.
- Existing fairness debt service and audit trail must be reused.
- Do not implement candidate ranking in the browser and do not send an
	unfiltered broadcast to all staff.

## Requirements

### User flow

1. Manager or authorized staff says: “Quân vắng ca sáng hôm nay, tìm người bù.”
2. System shows the identified shift and asks for clarification if ambiguous.
3. Backend finds eligible candidates using current schedule snapshot.
4. Candidate cards show pass/fail reasons, expected hours, skill coverage,
	 fairness delta, response deadline and contact channel.
5. Manager selects one candidate or asks for a different trade-off.
6. System creates a proposal and sends an invitation only after confirmation.
7. Candidate accepts/rejects. Manager confirms final roster mutation through
	 the existing lifecycle.
8. All proposal, invite, response, expiry and final decision events are audited.

### Hard safety rules

- Never recommend a candidate failing a hard constraint as “safe”.
- Soft violations are shown separately and require manager confirmation.
- Do not reveal another staff member's private availability details beyond the
	minimum reason needed to explain eligibility.
- Expired or changed roster snapshots force recomputation.
- If no candidate is safe, present escalation paths: manager covers, reduce
	capacity, close a station, or enter Crisis Room.

## Architecture

```text
Absence message/voice
				|
				v
AbsenceCommand parser -> shift identity resolver
				|
				v
Current roster snapshot + staff skills + TKB + fairness debt
				|
				v
Deterministic eligibility filter
				|
				v
Deterministic multi-objective ranking
				|
				+--> safe candidates
				+--> blocked candidates with reason codes
				+--> no-safe-candidate escalation
				|
				v
ActionProposal -> invite -> response -> existing roster lifecycle
```

### Ranking contract

Ranking is not an LLM judgment. Define a stable lexicographic policy:

1. hard-feasible only;
2. required skill coverage;
3. least fairness debt increase;
4. least added hours/commute metadata only if explicitly available;
5. least schedule disruption;
6. stable staff ID tie-breaker.

Expose each ranking component and weight in the response. Do not expose private
rankings to a normal employee; managers can inspect the explanation.

### API contract

```text
POST /api/v1/experience/shift-rescue/intake
POST /api/v1/experience/shift-rescue/{case_id}/candidates
GET  /api/v1/experience/shift-rescue/{case_id}
POST /api/v1/experience/shift-rescue/{case_id}/propose
POST /api/v1/experience/shift-rescue/{case_id}/invite
POST /api/v1/experience/shift-rescue/{case_id}/respond
POST /api/v1/experience/shift-rescue/{case_id}/confirm
```

`confirm` must call the same lifecycle mutation service used by existing roster
flows. If that service cannot be reused, stop and create an ADR before coding.

## Related code files

### Create

- `packages/agents/src/ca_agents/ag_shift_rescue/__init__.py`
- `packages/agents/src/ca_agents/ag_shift_rescue/intake.py`
- `packages/agents/src/ca_agents/ag_shift_rescue/eligibility.py`
- `packages/agents/src/ca_agents/ag_shift_rescue/ranking.py`
- `packages/agents/tests/test_shift_rescue_eligibility.py`
- `packages/agents/tests/test_shift_rescue_ranking.py`
- `packages/opsengine/src/ca_ops/shift_rescue_policy.py`
- `packages/opsengine/tests/test_shift_rescue_policy.py`
- `apps/api/src/ca_api/interfaces/http/shift_rescue.py`
- `apps/api/tests/test_shift_rescue_api.py`
- `apps/web/src/ui/experience/shift-rescue/ShiftRescuePanel.tsx`
- `apps/web/src/ui/experience/shift-rescue/CandidateCard.tsx`
- `apps/web/e2e/shift-rescue.spec.ts`
- `data/fixtures/grand_experience/shift-rescue.json`

### Modify

- `packages/contracts/src/ca_contracts/grand_experience.py` for additive rescue
	case/candidate/proposal models.
- `apps/api/src/ca_api/interfaces/http/main.py` to register the router.
- Existing shift/inbox service only through public functions/adapters.
- `apps/web/src/ui/experience/experience-api.ts` for typed calls.

## Implementation steps

1. Write failing tests for ambiguous shift, unknown staff, hard conflict,
	 fairness tie-break and no candidate.
2. Implement intake normalization. A parser may suggest IDs, but the resolver
	 must verify them against the current store and schedule.
3. Implement eligibility as pure functions returning reason codes.
4. Implement ranking as pure functions with a versioned policy identifier.
5. Build rescue case state machine:
	 `reported -> resolving -> candidates_ready -> proposed -> invited -> responded -> confirmed/expired/cancelled`.
6. Add stale snapshot checks and idempotency keys for invites and confirmation.
7. Wire existing messaging ports, but keep replay channel local and no-network.
8. Build UI with a clear “safe/blocked/needs approval” distinction.
9. Add a crisis escalation link to War Room without importing War Room internals.
10. Run targeted unit/API/e2e tests and verify no direct DB writes from agents.

## Test scenario matrix

| Case | Expected result |
|---|---|
| Absent staff and exact shift | Candidates generated |
| Ambiguous date or shift | Clarification required; no invite |
| Candidate has TKB conflict | Blocked with C01 reason |
| Candidate lacks skill | Blocked with skill reason |
| Candidate exceeds weekly cap | Blocked with cap reason |
| Candidate is safe but fairness worsens | Listed with visible delta, manager decides |
| No safe candidates | Escalation plan, no broadcast |
| Candidate accepts after roster changed | 409 stale; recompute |
| Duplicate invite request | One outbound invite |
| Unauthorized employee confirms | 403 and no mutation |
| Candidate rejects | Next ranked candidate remains proposal-only |
| Network/replay mode | Local deterministic response and audit |

## Todo

- [ ] Add rescue contracts and case state machine.
- [ ] Implement pure eligibility and ranking policies.
- [ ] Reuse current schedule/fairness/lifecycle adapters.
- [ ] Add invite idempotency and privacy-safe explanations.
- [ ] Build candidate UI and crisis escalation.
- [ ] Add fixtures and all test layers.
- [ ] Add runbook for the 90-second rescue demo.

## Success criteria

- [ ] A manager resolves the seeded Quân absence in under 90 seconds in replay.
- [ ] At least one safe and two blocked candidates render with reasons.
- [ ] No invite or roster mutation occurs before the correct confirmation step.
- [ ] Stale schedule causes recomputation, not silent overwrite.
- [ ] `pytest packages/agents/tests/test_shift_rescue_eligibility.py packages/agents/tests/test_shift_rescue_ranking.py packages/opsengine/tests/test_shift_rescue_policy.py apps/api/tests/test_shift_rescue_api.py -q` passes.
- [ ] `npx playwright test e2e/shift-rescue.spec.ts` passes in replay.

## Risk assessment

- **Risk:** duplication of existing shift swap logic. **Signal:** two code
	paths produce different hard-constraint results. **Response:** route both
	through one policy adapter; add differential tests against current behavior.
- **Risk:** privacy leak through ranking explanation. **Signal:** employee API
	response contains another employee's availability details. **Response:** use
	role-specific response projection and add a redaction test.
- **Risk:** no candidate leads to unsafe pressure. **Signal:** UI primary CTA
	is “choose anyway”. **Response:** replace with capacity/escalation actions and
	fail the e2e assertion.

## Security and rollback

- Authenticate every case by store and actor.
- Sign/expire invitation tokens; do not put sensitive data in URLs.
- Rate-limit intake and invite endpoints.
- Rollback by disabling the experience rescue router/feature flag; existing
	`/api/v1/cho-doi-ca` remains the fallback.

## Handoff

Phase 04 may use confirmed rescue decisions as rule-learning evidence, never
raw candidate ranking details. Phase 06 may render the rescue state on the
Living Map through the read-only projection endpoint.
