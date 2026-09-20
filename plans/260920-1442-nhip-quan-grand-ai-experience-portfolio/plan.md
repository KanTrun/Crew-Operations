---
title: "NHIP QUAN Grand AI Experience Portfolio"
description: "Xay portfolio trai nghiem AI doc lap cho toan quan: mo phong, cuu ca, tu viet luat, ky uc khong gian va Living Cafe OS."
status: pending
priority: P1
effort: "8-12 weeks, staged delivery"
branch: "feat/grand-ai-experience-portfolio"
tags: [feature, frontend, backend, api, critical, experimental]
created: 2026-09-20
blockedBy: []
blocks: []
---

# NHIP QUAN - Grand AI Experience Portfolio

## Overview

Xay mot portfolio tinh nang AI moi co the dung doc lap ben ngoai cac man hinh
van hanh hien tai, nhung co adapter doc du lieu NHIP QUAN khi can. Portfolio
gom War Room Digital Twin, AI Shift Rescue, Quan tu viet luat, HON QUAN Spatial
Memory va QUANVERSE Living Cafe OS. Cac y tuong phu AI Crisis Room, AI Tour
Guide, AI Flavor Universe va AR-lite duoc bao phu trong cac phase tuong ung.

Muc tieu trinh dien khong phai "them mot chatbot". Muc tieu la cho thay mot
quan co the nghe, hieu, mo phong, ghi nho, ho tro nhieu vai tro va van giu
quyen quyet dinh o con nguoi.

## Brainstorm contract (accepted)

| Field | Decision |
|---|---|
| **Outcome** | Mot portfolio trai nghiem AI co voice input/output, giao dien map/3D, memory co consent, cac luong hanh dong co kiem chung va demo xuyen vai tro trong toi da 5 phut. |
| **Constraints** | Python 3.12, FastAPI, Next.js 15, React Three Fiber/Three.js da co trong web, khong de LLM ghi DB truc tiep, fail-closed, replay offline, 2D fallback, PR-only vao `main`, khong commit secrets. |
| **Non-goals** | Khong thay the solver/gates hien tai; khong camera nhan dien khuon mat; khong dieu khien thiet bi that; khong POS/IoT bat buoc; khong huan luyen model rieng; khong photorealistic 3D o ban dau. |
| **Acceptance** | Moi y tuong co contract, API/UI flow, fixture replay, unit/integration/e2e tests, consent/audit, accessibility/reduced-motion, rollback; portfolio demo duoc va merge qua PR xanh. |

## Evidence and reuse boundary

- Existing reusable foundation: `packages/agents/src/ca_agents/ag_twin`,
	`ag_predict`, `ag_explain/episodic_memory.py`, AG-COPILOT voice transport,
	Copilot proposal/audit, CP-SAT solver, fairness, `@react-three/fiber`,
	`@react-three/drei`, existing 3D ops pulse.
- Existing predictive/twin plan: [`260918-nhip-quan-os-brain`](../260918-nhip-quan-os-brain/plan.md).
	This portfolio consumes its contracts and deterministic math; it must not
	duplicate or silently change them. Any incompatible contract needs an ADR.
- Existing UI authority: [`docs/design-guidelines.md`](../../docs/design-guidelines.md).
	New experience surfaces may use a distinct "experience register", but keep
	typography, Vietnamese copy, focus states, reduced motion and safe-area rules.
- Existing Git authority: [`docs/github-operating-model.md`](../../docs/github-operating-model.md)
	and [`docs/runbook-demo.md`](../../docs/runbook-demo.md).

## Architecture decisions locked for downstream agents

1. **New product boundary:** the MVP is a separately routable product surface
	inside the existing Next.js app: `/quanverse` plus `apps/web/src/ui/experience/`
	and versioned API routers under `apps/api`. It may read current app data
	through adapters; it must not import DB internals or mutate existing
	lifecycle directly. A future `apps/experience` runtime split is optional and
	is not required for this plan's acceptance.
2. **AI boundary:** LLM handles language understanding, response wording and
	 voice. Deterministic services own retrieval, scoring, simulation, policy,
	 permission, consent, audit and writes.
3. **Memory boundary:** every memory has owner, source, consent state,
	 visibility, retention, evidence refs and revocation path. Unconfirmed
	 memories are never phrased as confirmed facts.
4. **Rendering boundary:** 2D/isometric view is the canonical fallback;
	 WebGL/3D/AR are progressive enhancement. No core acceptance criterion may
	 require WebGL, camera, microphone or live network.
5. **Action boundary:** every mutation is a proposal first. A verified human
	 confirmation is required before changing roster, rules, memories,
	 customer preferences or experience modes.

## Dependency and execution graph

```text
Phase 01 Foundation and contracts
			 ├── Phase 02 War Room + Crisis Room
			 ├── Phase 03 AI Shift Rescue
			 ├── Phase 04 Quan tu viet luat
			 ├── Phase 05 HON QUAN + AI Tour Guide
			 └── Phase 06 QUANVERSE + Flavor Universe + AR-lite
												 └── Phase 07 Integration, demo, release
```

Phase 02-06 may be developed in parallel only after Phase 01 contracts are
merged. Phase 06 additionally consumes read-only projections from Phase 02/03
and Phase 05 anchors/memory, so it starts after those contracts and read
adapters exist. Phase 07 is sequential and owns cross-feature integration,
visual QA, performance budgets, release branch, PR and merge gates.

## Phase roadmap

| # | Phase | Priority | Depends on | Deliverable |
|---|---|---:|---|---|
| 1 | [Foundation and contracts](./phase-01-start.md) | P1 | - | Product boundary, shared event/voice/memory/action contracts, fixtures, branch protocol |
| 2 | [War Room Digital Twin](./phase-02-war-room-digital-twin.md) | P1 | 1 + existing twin plan | Multi-scenario simulation and Cafe Crisis Room |
| 3 | [AI Shift Rescue](./phase-03-ai-shift-rescue.md) | P1 | 1 | Absence-to-safe-replacement flow with fairness-aware ranking |
| 4 | [Quan tu viet luat](./phase-04-quan-tu-viet-luat.md) | P1 | 1 + 2/3 signals | Human-confirmed rules learned from repeated decisions and tested in shadow mode |
| 5 | [HON QUAN Spatial Memory](./phase-05-hon-quan-spatial-memory.md) | P1 | 1 + voice | Spatial memories, evidence timeline, consent and AI Tour Guide |
| 6 | [QUANVERSE Living Cafe OS](./phase-06-quanverse-living-cafe-os.md) | P1 | 1 + 2/3 read projections + 5 | Role-aware living map, customer preferences, Flavor Universe and AR-lite |
| 7 | [Integration, demo, release](./phase-07-integration-demo-release.md) | P1 | 2-6 | Demo route, e2e, accessibility/performance, branch/PR/merge/release |

## File ownership strategy

| Area | Owning phase | Rule |
|---|---|---|
| Shared contracts and replay fixtures | 1 | Contracts merge first; later phases extend, never redefine silently |
| Simulation and crisis APIs | 2 | No direct UI-owned calculations |
| Shift rescue policy/API | 3 | Reuse solver/gates; no duplicate scheduler |
| Rule learning/playbook bridge | 4 | Preserve 8-step lifecycle and fail-closed |
| Spatial memory/voice retrieval | 5 | Own memory schema and consent policy |
| Living map/role surfaces/AR | 6 | Own experience UI; adapters only for data access |
| Integration/docs/release | 7 | No feature logic added here; only wiring and gates |

## Success criteria

- [ ] A fresh AI IDE can start from this file, open the linked phase, and find
	exact scope, files, contracts, tests and stop conditions without this chat.
- [ ] Each named idea has a working replay demo, not only a visual mockup.
- [ ] Voice, memory and 3D failure degrade to text, 2D and replay without
	blocking the primary workflow.
- [ ] No unconfirmed AI output mutates production data.
- [ ] All new contracts are generated/validated and all touched package tests,
	web typecheck, e2e smoke and CI gates pass.
- [ ] Implementation lands through `feat/*` branches created from the newest
	`origin/main`, commits use Conventional Commits, PRs are reviewed, and only
	then is `main` updated by squash merge.

## Handoff

Implementation should begin only after plan review with:

```text
/ak:cook --parallel D:\CA-CÔNG-BẰNG\plans\260920-1442-nhip-quan-grand-ai-experience-portfolio\plan.md
```

The implementer must not pull, commit, push or merge from an unreviewed plan.
Use Phase 07's exact release checklist for those operations.

<!-- slug: nhip-quan-grand-ai-experience-portfolio -->