---
phase: 4
title: "Quan tu viet luat"
status: pending
priority: P1
effort: "5-8 days"
dependencies: [1, 2, 3]
---

# Phase 4: Quán tự viết luật

## Overview

Nâng “cẩm nang sống” thành trải nghiệm học có thể nhìn thấy: hệ thống gom các
quyết định lặp lại của con người, phát hiện mẫu, đề xuất một luật rõ ràng,
chạy shadow test trên lịch sử, rồi đưa qua vòng đời playbook 8 bước. Đây là
phần biến War Room/Shift Rescue từ các hành động rời rạc thành trí nhớ tổ chức.

## Evidence and reuse

- Reuse `packages/playbook/src/ca_playbook/vong_doi.py` and ADR-010's 8-step
	lifecycle. Do not create a second rule state machine.
- Reuse `AG-RULE`, `AG-PREDICT`, `ag_explain/episodic_memory.py` and existing
	`PositiveRule`/playbook contracts.
- Existing data is mostly fixture/synthetic; every UI must distinguish fixture
	evidence from measured cafe evidence.
- Rule language is generated/rewritten by AI only after deterministic evidence
	selection. The rule condition and effect are validated by code.

## Requirements

### User-visible

- Show “why this rule was proposed”: repeated decisions, dates, actors,
	affected shifts, counterexamples and confidence.
- Ask one confirmation question in Vietnamese:
	“Có phải đây là luật của quán mình không?”
- Let manager edit wording only within a structured condition/effect form.
- Run a shadow simulation against historical fixtures before activation.
- Compare before/after hard constraints, fairness, workload and operational
	outcomes.
- Move accepted rule through existing states:
	`de_xuat -> qua_vf_rule -> du_tap_su -> hieu_luc -> da_go`.
- Keep rejection, expiry, rollback and rule supersession visible.

### Hard rules

- A rule needs the configured minimum evidence; default remains the existing
	threshold (at least three repeated signals where the lifecycle requires it).
- No rule may invent a field absent from the contract or condition namespace.
- No rule may weaken a hard constraint or bypass a gate.
- Shadow test never changes production roster, playbook or solver config.
- Only manager/owner can activate or remove a rule.

## Architecture

```text
Decision events + rescue/twin outcomes
							|
							v
Deterministic grouping and counterexample scan
							|
							v
AG-RULE wording proposal (one rule only)
							|
							v
VF-RULE + schema + conflict + evidence gates
							|
							v
Shadow test on historical fixture
							|
							v
Human apprenticeship / confirmation
							|
							v
Existing playbook 8-step lifecycle -> active rule
```

### Rule contract

Keep structured fields separate from the natural-language sentence:

```python
class RuleCandidate(BaseModel):
		candidate_id: str
		condition: dict[str, str | int | float | bool]
		effect: dict[str, str | int | float | bool]
		sentence: str
		evidence_refs: list[str]
		counterexample_refs: list[str]
		confidence: float
		source_kind: Literal["decision", "rescue", "twin", "episode"]
		playbook_status: PositiveRuleStatus
		shadow_result: ShadowTestResult | None = None
```

`condition` keys must come from a closed registry, for example `day_part`,
`station`, `skill`, `demand_band`, `absence_type`. Reject arbitrary executable
expressions. Store a `rule_version` and `created_from_snapshot_hash`.

### API contract

```text
GET  /api/v1/experience/rules/candidates
POST /api/v1/experience/rules/discover
GET  /api/v1/experience/rules/{candidate_id}/evidence
POST /api/v1/experience/rules/{candidate_id}/shadow-test
POST /api/v1/experience/rules/{candidate_id}/confirm
POST /api/v1/experience/rules/{candidate_id}/reject
POST /api/v1/experience/rules/{candidate_id}/revoke
```

Confirmation delegates to the existing playbook lifecycle. If lifecycle state
transition fails, preserve candidate and show the failure; never partially
activate.

## Related code files

### Create

- `packages/agents/src/ca_agents/ag_rule_learning/__init__.py`
- `packages/agents/src/ca_agents/ag_rule_learning/discover.py`
- `packages/agents/src/ca_agents/ag_rule_learning/evidence.py`
- `packages/agents/src/ca_agents/ag_rule_learning/shadow_test.py`
- `packages/agents/tests/test_rule_learning_discover.py`
- `packages/agents/tests/test_rule_learning_shadow_test.py`
- `packages/playbook/tests/test_experience_rule_bridge.py`
- `apps/api/src/ca_api/interfaces/http/experience_rules.py`
- `apps/api/tests/test_experience_rules_api.py`
- `apps/web/src/ui/experience/rules/RuleDiscovery.tsx`
- `apps/web/src/ui/experience/rules/RuleEvidenceDrawer.tsx`
- `apps/web/src/ui/experience/rules/RuleShadowResult.tsx`
- `apps/web/e2e/experience-rules.spec.ts`
- `data/fixtures/grand_experience/rule-learning.json`

### Modify

- `packages/contracts/src/ca_contracts/grand_experience.py` for candidate and
	shadow result fields.
- `packages/agents/src/ca_agents/ag_rule` only through a small compatibility
	adapter if its existing contract requires it; preserve current behavior.
- `apps/api/src/ca_api/interfaces/http/main.py` to register the router.
- `apps/web/src/ui/experience/experience-api.ts` for typed calls.
- `docs/THIRD_PARTY.md` only if dependencies change.

## UI/UX contract

- Timeline of evidence first; proposed sentence second; structured condition
	third; shadow result fourth; action buttons last.
- Use clear chips: `Bằng chứng fixture`, `Đã đo ở quán`, `Chưa đủ bằng chứng`.
- Never use “AI đã học” for a draft. Use “AI đề xuất, quản lý quyết định”.
- The rule sentence must have a “show data” affordance, not an opaque chat bubble.
- Deletion/revoke is a destructive action with reason and confirmation.

## Implementation steps

1. Write tests for evidence threshold, field registry, counterexample and
	 conflicting rule behavior.
2. Create a read model of confirmed decision events; do not query KV internals
	 from an agent.
3. Implement deterministic grouping and candidate IDs based on stable hashes.
4. Call AG-RULE only to phrase a candidate from the selected evidence; validate
	 its sentence against the structured condition/effect.
5. Run all VF gates and return machine-readable rejection reasons.
6. Implement shadow test by invoking read-only solver/playbook logic with an
	 isolated parameter snapshot.
7. Bridge candidate state into the existing playbook 8-step lifecycle.
8. Build evidence-first UI and tests.
9. Add replay fixture with one candidate accepted and one rejected.

## Test scenario matrix

| Case | Expected result |
|---|---|
| Two repeated decisions only | No candidate if threshold is three |
| Three same decisions, no counterexample | Candidate with evidence |
| Three decisions with conflicting outcome | Candidate marked needs review |
| AI invents unknown condition key | VF-RULE rejects |
| Sentence number absent from evidence | VF-NUM rejects |
| Rule weakens C01-C06 | Rejected; hard constraints remain unchanged |
| Shadow test improves fairness but lowers staffing | Trade-off shown, no auto-activation |
| Manager confirms with stale snapshot | 409, candidate remains draft |
| Manager revokes active rule | Rule disabled and audit reason recorded |
| Employee attempts activation | 403 |
| Fixture evidence shown as real | UI/e2e failure; label must be present |

## Todo

- [ ] Define candidate/shadow contracts and condition registry.
- [ ] Implement deterministic evidence grouping and counterexamples.
- [ ] Add AG-RULE wording adapter and all gates.
- [ ] Add isolated shadow test runner.
- [ ] Bridge existing playbook lifecycle.
- [ ] Build evidence timeline UI.
- [ ] Add unit/API/e2e/replay tests and run agent eval.

## Success criteria

- [ ] One seeded candidate completes proposal -> shadow -> confirmation in replay.
- [ ] One invalid candidate is rejected with an explainable gate code.
- [ ] No rule activates without manager confirmation.
- [ ] Shadow result is reproducible and cannot mutate production state.
- [ ] Existing playbook tests remain green.
- [ ] Agent prompt/version/eval requirements are satisfied when AG-RULE changes.

## Risk assessment

- **Risk:** “self-writing” becomes fake because fixture evidence is too thin.
	**Signal:** candidate has no three distinct evidence refs or uses only one
	event. **Response:** show “chưa đủ bằng chứng” and stop the lifecycle.
- **Risk:** new candidate state diverges from playbook. **Signal:** same rule
	has two statuses in API responses. **Response:** make playbook lifecycle the
	sole writer and expose an adapter read model.
- **Risk:** operators over-trust an attractive improvement score. **Signal:**
	UI primary action skips shadow result. **Response:** block confirm until a
	completed shadow result exists.

## Security and rollback

- Restrict evidence to the manager's store and role scope.
- Redact staff-private messages in evidence views for unauthorized roles.
- Do not execute condition strings; allow only registry keys and typed values.
- Rollback by disabling discovery UI/router; existing active rules remain
	governed by the current playbook, not deleted by the rollback.

## Handoff

Phase 07 must demo one complete rule lifecycle and one rejected proposal. Phase
06 may display active rule signals on the Living Map through read-only events.
