---
phase: 7
title: "Integration, demo, branch delivery and release"
status: pending
priority: P1
effort: "5-8 days"
dependencies: [2, 3, 4, 5, 6]
---

# Phase 7: Integration, demo, branch delivery and release

## Overview

Hop nhat cac phase doc lap thanh mot cau chuyen demo 5 phut, chay toan bo gate
chat luong, kiem tra privacy/performance/accessibility va dua code qua quy
trinh branch -> commit -> push -> PR -> review -> squash merge -> xac minh
`main`. Phase nay khong them feature moi; thieu sot chuc nang quay ve phase so
huu tuong ung.

## Integration contract

```text
1. Khach: "Toi thich it ngot va cho yen tinh."
	-> Flavor recommendation + consented preference proposal.
2. Nhan vien: "Quan dang can chu y gi?"
	-> Voice/text briefing tu Living Map va spatial memory da xac nhan.
3. Quan ly: kich hoat "Troi mua" mode.
	-> Proposal -> confirmation -> map/horizon projection thay doi.
4. Quan ly bao vang dot xuat.
	-> Shift Rescue xep hang nguoi thay an toan va candidate bi chan.
5. Quan ly hoi "Neu them mot nguoi thi sao?"
	-> War Room so sanh baseline va cac scenario.
6. He thong hien quyet dinh lap lai va hoi:
	"Co phai day la luat cua quan minh?"
	-> Shadow test -> playbook proposal, khong tu kich hoat.
```

Presenter must complete the story in replay mode without live LLM, microphone,
camera, WebGL or network. Live mode is a bonus and must be labeled live/replay
honestly.

## Required integration tests

- `LivingCafeSnapshot` contains only fields allowed for the authenticated role.
- A confirmed spatial memory can explain an event but cannot change it.
- A Shift Rescue confirmation becomes an event and may become rule evidence,
  but does not auto-create a rule.
- Rule shadow test consumes rescue/twin events through contracts only.
- Mode confirmation creates one idempotent event and updates projections.
- Every proposal has a snapshot hash; stale confirmation returns 409.
- Every mutation path has a corresponding audit event.

## Failure matrix

| Failure | Required experience |
|---|---|
| Live LLM unavailable | Replay/deterministic text response; no fake live badge |
| Voice permission denied | Text composer and browser audio/replay path |
| WebGL unavailable | Complete 2D/isometric map |
| Camera denied | QR/manual anchor path |
| API timeout | Vietnamese safe error + retry; no duplicate action |
| Stale snapshot | Explain changed data; require recomputation |
| Insufficient evidence | Show "chua du bang chung"; block rule confirmation |
| No safe replacement | Escalation actions; no unsafe candidate |
| Fixture data | Visible fixture chip; no measured-result claim |
| Unauthorized role | 403 projection; no client-only hiding |

## Demo and UX quality gates

- Record one clean 5-minute replay run and one deliberate failure run.
- Verify desktop 1440x900 and mobile 390x844.
- Verify Vietnamese diacritics, long names, keyboard focus, screen reader
  labels, modal escape, touch target size and safe-area bottom action.
- Verify reduced-motion preference.
- Verify map is nonblank and interactive with WebGL enabled, then rerun with
  WebGL disabled.
- Verify buttons have accessible labels; no emoji icons or placeholder copy.
- Verify no nested cards or prohibited palette/gradient regression.

## Performance budgets

- First interactive route <= 2.0s in local replay on demo machine.
- Initial route JS payload must not exceed baseline by >20% without a decision.
- 3D map <= 50 visible objects in MVP and no per-frame allocations.
- Map p95 <= 100ms in 2D and <= 200ms in 3D on target laptop.
- API replay p95 <= 500ms for snapshot, <= 2s for three scenarios.
- Preserve existing voice idle/max duration limits.

## Required verification commands

Run the narrowest command first after each feature merge, then full gates:

```powershell
make contracts
make test-unit
make lint

Push-Location apps/web
npm run typecheck
npx playwright test e2e/war-room.spec.ts e2e/shift-rescue.spec.ts e2e/spatial-memory.spec.ts e2e/quanverse.spec.ts
Pop-Location

make test
make demo
make docker-smoke
```

Use actual Makefile target names if they differ. Do not claim a skipped gate
passed; record command, exit code and residual failures in the PR.

## Related code and documentation files

### Create

- `docs/runbook-grand-ai-experience.md`
- `docs/architecture-grand-ai-experience.md`
- `docs/adr/ADR-016-grand-ai-experience-boundary.md`
- `docs/adr/ADR-017-spatial-memory-consent.md`
- `docs/adr/ADR-018-progressive-3d-fallback.md`
- `apps/web/e2e/grand-experience-replay.spec.ts`
- `scripts/demo_grand_experience.py` or repository-equivalent demo script
- `plans/260920-1442-nhip-quan-grand-ai-experience-portfolio/reports/verification.md`

### Modify

- `README.md` for the new product surface and local demo route.
- `docs/huong-dan-demo-thi.md` for the 5-minute script.
- `docs/THIRD_PARTY.md` only when a dependency is added.
- `docs/ket-qua-tong-hop.md` only for measured results, never target claims.
- `.github/CODEOWNERS` only if new ownership paths require it.
- `.github/workflows/ci.yml` only for required feature gates, preserving all
	existing gates.

## Branch, pull, commit, push, PR and merge protocol

Execute this only after plan approval and only with a clean worktree or
explicit handling of the user's unrelated changes.

### 1. Prepare isolated worktree

```powershell
git fetch origin
git worktree add -b feat/grand-ai-experience-portfolio ..\nhip-quan-grand-ai origin/main
Set-Location ..\nhip-quan-grand-ai
git pull --rebase origin main
git status --short
```

If the target branch exists, inspect it first. Do not reset or discard
unrelated changes. If the current worktree is dirty, leave it untouched and
use the clean worktree.

### 2. Implement by phase branches

```text
feat/experience-contracts
feat/experience-war-room
feat/experience-shift-rescue
feat/experience-rule-learning
feat/experience-spatial-memory
feat/experience-quanverse
```

Each branch starts from newest `origin/main` or the approved contracts branch.
Branches are short-lived and go through PR. Contracts merge first. Phase 02-06
may use separate worktrees after Phase 01 is available.

### 3. Commit protocol

Use focused Conventional Commits:

```text
feat(contracts): add grand experience contracts
feat(api): add war room simulation boundary
feat(agents): add deterministic shift rescue ranking
feat(playbook): add rule shadow test bridge
feat(web): add quanverse living map
test(experience): cover replay and privacy projections
docs(experience): add grand AI demo runbook
```

Before each commit:

```powershell
git diff --check
git status --short
git diff --stat
```

Never commit `.env`, tokens, private logs, raw audio, customer data or local DB.

### 4. Push and PR

```powershell
git push -u origin <branch>
gh pr create --base main --head <branch> --title "feat(experience): ..." --body-file pr-body.md
```

PR body includes outcome, phases/files, contract changes, security/privacy,
test results, screenshots/replay, known gaps, rollback and this plan link.
Required reviews follow CODEOWNERS. Contracts, agents, orchestration and web
must run their corresponding gates.

### 5. Merge to main

Only after CI is green, review is approved and branch is up to date:

```powershell
gh pr checks <pr-number>
gh pr review <pr-number> --approve
gh pr merge <pr-number> --squash --delete-branch
git fetch origin
git switch main
git pull --rebase origin main
make demo
```

If branch protection disallows CLI approval/merge, stop and report the exact
human action. Never force-push, reset hard or bypass review.

### 6. Release verification

```powershell
git switch main
git pull --rebase origin main
make test
make docker-smoke
git tag -a v1.0.0-final -m "release: grand AI experience portfolio"
git push origin v1.0.0-final
```

Create the final tag only after the team accepts the release checklist. For a
semifinal release use the repository release branch/tag policy instead.

## Todo

- [ ] Merge Phase 01 contracts first.
- [ ] Integrate Phase 02-06 through public contracts/adapters.
- [ ] Run cross-feature and privacy projection tests.
- [ ] Run desktop/mobile/reduced-motion/WebGL-off visual QA.
- [ ] Record performance baseline and replay artifacts.
- [ ] Update docs and ADRs after implementation evidence exists.
- [ ] Create feature branches from newest `origin/main`.
- [ ] Commit focused changes with Conventional Commits.
- [ ] Push branches and open PRs.
- [ ] Wait for review/CI; squash merge only when green.
- [ ] Pull merged `main`, rerun demo/smoke, tag only accepted release.

## Success criteria

- [ ] One five-minute replay demo completes all five main ideas without live
	network, live LLM, microphone, camera or WebGL.
- [ ] Live voice/3D/AR bonus path works when enabled and fails gracefully when
	disabled.
- [ ] All cross-feature mutations require valid role, consent/proposal,
	snapshot freshness and audit.
- [ ] Contracts, unit, lint/typecheck, integration, architecture, no-live-LLM,
	web and required e2e gates pass.
- [ ] Performance budgets are measured and documented.
- [ ] Docs describe measured state and label fixture/demo claims.
- [ ] PRs are reviewed and squash-merged into `main`; post-merge `main` passes
	`make demo` and `make docker-smoke`.
- [ ] Rollback instructions are tested for flags and migrations.

## Risk assessment

- **Risk:** parallel branches conflict in shared contracts/UI shell. **Signal:**
	same file is modified by multiple phase PRs. **Response:** contracts branch
	owns shared schemas; later branches rebase and use adapters.
- **Risk:** portfolio is too large for the timeline. **Signal:** a phase misses
	its gate twice or demo exceeds 5 minutes. **Response:** stop feature growth,
	keep the five named outcomes, and ask for an approved release slice; do not
	silently redefine complete.
- **Risk:** merge bypasses review. **Signal:** required CI/review missing.
	**Response:** stop merge and report the missing gate.
- **Risk:** synthetic numbers are presented as real impact. **Signal:** UI or
	slides omit fixture labels. **Response:** block release until corrected.

## Security and rollback

- Run secret scan before every push and inspect changed files for raw audio,
	personal data and env values.
- Confirm public customer mode cannot reach staff snapshots or audit logs.
- Keep experience flags default-off until replay and authorization tests pass.
- Rollback order: disable experience flags, stop live voice/AR, migrate down
	only tested additive schema, revert via PR. Never use `git reset --hard` on a
	shared branch.

## Handoff to another AI IDE/model

1. Read this `plan.md` completely.
2. Read the owned phase completely and every listed "Files to read".
3. Run `git status`, `git branch --show-current`, `git fetch origin`; never
	 assume the current branch is current.
4. Confirm Phase 01 is merged before Phase 02-06.
5. Write contracts/tests before behavior changes where required.
6. Do not invent a new scheduler, memory store, auth path or LLM tool path.
7. Validate narrowly after each edit, then run the phase gate.
8. Report exact files, commands, exit codes and known gaps. Never claim
	 commit/push/merge unless the command succeeded.

## Next steps

After user approval:

```text
/ak:cook --parallel D:\CA-CÔNG-BẰNG\plans\260920-1442-nhip-quan-grand-ai-experience-portfolio\plan.md
```

Use `/ak:plan red-team` and `/ak:plan validate` before cook if not already run
by the selected planning mode.
