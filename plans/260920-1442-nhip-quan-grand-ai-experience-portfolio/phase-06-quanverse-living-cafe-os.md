---
phase: 6
title: "QUANVERSE Living Cafe OS"
status: pending
priority: P1
effort: "8-12 days"
dependencies: [1, 2, 3, 5]
---

# Phase 6: QUÁNVERSE Living Cafe OS

## Overview

Xây giao diện sản phẩm mới đứng bên ngoài các màn hình vận hành: một Living Map
duy nhất cho khách, nhân viên, quản lý và chủ quán. Cùng một trạng thái quán
được chiếu khác nhau theo vai trò. Phase này bao phủ các ý tưởng AI Flavor
Universe, Cafe Crisis Room projection, AI Tour Guide entry point và AR-lite
progressive enhancement. QUÁNVERSE không tự thay đổi lịch, rule hoặc memory.

## Evidence and reuse

- Use Phase 01 contracts and Phase 05 anchors/memory APIs.
- Existing web already has Three.js/R3F dependencies and a lightweight 3D ops
	pulse; reuse patterns, do not add a second rendering stack.
- Existing AppShell/auth/session/focus/error presentation are authoritative.
- Existing customer-facing reservation/Facebook capabilities may be exposed as
	read-only cards only after a reviewed adapter; do not merge public and staff
	data without role projection.

## Requirements

### Living Map

- `/quanverse` is a distinct experience route with a strong first viewport.
- Map displays zones, anchors, active events, load/attention signals and the
	next 15-minute horizon.
- Every event has status, timestamp, source and action/proposal state.
- User can switch role only in replay/demo fixture; production role comes from
	authenticated session and cannot be self-selected.
- Role projections:
	- **Khách:** find a seat, state preference, ask for menu/place guidance;
		never see staff/private operations.
	- **Nhân viên:** see assigned attention points and hear short briefings;
		private customer memory is minimized.
	- **Quản lý:** see rescue cases, modes, proposals, capacity and evidence.
	- **Chủ quán:** see high-level experience trends, confirmed rules and audit.

### Cafe Modes

Provide mode proposals, not invisible automation:

```text
troi_mua
gio_cao_diem
khach_doan
thieu_nhan_su
quan_yen_tinh
dem_nhac
```

Activating a mode requires manager/owner confirmation. A mode emits a scoped
event and read-only projection; actions such as staffing or menu changes remain
separate proposals.

### AI Flavor Universe

- Customer can state taste in natural language: “ít ngọt, thơm trà, không sữa”.
- System maps to explicit preference dimensions and suggests from an approved
	menu/catalog fixture.
- It must show why a drink was suggested and flag unknown/allergy information.
- Allergy/intolerance is never inferred from taste. Customer must explicitly
	state it and confirm storage separately.
- Customer can try a “what if” taste slider/session without persisting it.

### AR-lite

- Optional camera overlay points to anchors or onboarding steps using manual
	anchor selection/QR marker, not face tracking or autonomous indoor SLAM.
- If camera permission, WebXR or device capability fails, use map/QR/text path.
- AR does not expose private operational events to a public device.

## Architecture

```text
Authenticated role + optional replay persona
								 |
								 v
Living Map read model (anchor/event/mode projection)
			 |                 |                  |
			 v                 v                  v
2D/isometric renderer  WebGL renderer    AR-lite renderer
			 |                 |                  |
			 +-----------------+------------------+
												 v
Interaction command -> role policy -> proposal/consent API
												 |
												 +--> spatial memory retrieval
												 +--> flavor recommendation (catalog rules)
												 +--> shift rescue / War Room read projection
												 +--> voice dock and replay
```

### Read model and projections

Create a server-side `LivingCafeSnapshot` with role-specific projection:

```python
class LivingCafeSnapshot(BaseModel):
		snapshot_id: str
		store_id: str
		generated_at: datetime
		role: ExperienceRole
		zones: list[ZoneProjection]
		events: list[PublicEventProjection]
		modes: list[ModeProjection]
		next_horizon: list[HorizonItem]
		data_quality: list[DataQualityNotice]
```

The server strips fields before returning the snapshot. Do not rely on client
code to hide private data.

### API contract

```text
GET  /api/v1/experience/quanverse/snapshot
GET  /api/v1/experience/quanverse/modes
POST /api/v1/experience/quanverse/modes/{mode}/propose
POST /api/v1/experience/quanverse/modes/{mode}/confirm
POST /api/v1/experience/quanverse/flavor/recommend
POST /api/v1/experience/quanverse/preferences/propose
DELETE /api/v1/experience/quanverse/preferences/{id}
GET  /api/v1/experience/quanverse/tour/{tour_id}
POST /api/v1/experience/quanverse/ar-session
```

All POST endpoints are idempotent and proposal/consent based. `snapshot`
returns `data_quality` so fixture, stale and unavailable signals are visible.

## Related code files

### Create

- `apps/web/src/app/quanverse/page.tsx`
- `apps/web/src/app/quanverse/loading.tsx`
- `apps/web/src/ui/experience/quanverse/LivingMap.tsx`
- `apps/web/src/ui/experience/quanverse/LivingMap2d.tsx`
- `apps/web/src/ui/experience/quanverse/RoleProjection.tsx`
- `apps/web/src/ui/experience/quanverse/ModeRail.tsx`
- `apps/web/src/ui/experience/quanverse/HorizonTimeline.tsx`
- `apps/web/src/ui/experience/quanverse/FlavorUniverse.tsx`
- `apps/web/src/ui/experience/quanverse/PreferenceConsent.tsx`
- `apps/web/src/ui/experience/quanverse/ArLiteOverlay.tsx`
- `apps/web/src/ui/experience/quanverse/VoiceDock.tsx`
- `apps/web/src/ui/experience/quanverse/quanverse-model.ts`
- `apps/web/src/ui/experience/quanverse/quanverse-fixtures.ts`
- `apps/web/e2e/quanverse.spec.ts`
- `apps/web/e2e/quanverse-mobile.spec.ts`
- `apps/api/src/ca_api/interfaces/http/quanverse.py`
- `apps/api/tests/test_quanverse_api.py`
- `packages/agents/src/ca_agents/ag_quanverse/__init__.py`
- `packages/agents/src/ca_agents/ag_quanverse/flavor.py`
- `packages/agents/src/ca_agents/ag_quanverse/modes.py`
- `packages/agents/tests/test_quanverse_flavor.py`
- `packages/agents/tests/test_quanverse_modes.py`
- `data/fixtures/grand_experience/quanverse.json`
- `data/fixtures/grand_experience/menu-taste-profile.json`

### Modify

- `apps/api/src/ca_api/interfaces/http/main.py` router registration.
- `apps/web/src/app/AppShell.tsx` navigation/route guard.
- `apps/web/src/ui/icons.tsx` for accessible map/voice/control icons.
- `apps/web/src/ui/experience/experience-api.ts` typed calls.
- `apps/web/src/app/globals.css` for scoped experience register tokens only.
- `docs/design-guidelines.md` if the experience register is accepted as a
	durable design-system extension.

## UI/UX contract

- First viewport must communicate “a living cafe” through the map and current
	state, not through a marketing hero or explanatory card stack.
- Use a restrained dark/copper atmosphere consistent with existing hub tokens;
	do not introduce purple gradients or decorative orbs.
- Map controls have icons plus accessible labels/tooltips.
- Desktop: map + right action rail + bottom horizon strip. Mobile: map first,
	bottom sheet for details, fixed voice action above safe-area navigation.
- No nested cards. Use framed tools only for selected anchor, mode confirmation
	and consent modal.
- Motion: T1 state changes, T2 only for optional map camera; reduced motion
	disables camera movement and uses focus/outline transitions.
- All text must fit at mobile widths; test Vietnamese diacritics and long event
	names.

## Implementation steps

1. Write role-projection, privacy and mode lifecycle tests.
2. Implement `LivingCafeSnapshot` server projection from Phase 05 anchors/events
	 plus read-only adapters for rescue/war-room states.
3. Implement flavor recommendation as a deterministic catalog filter/scorer;
	 use LLM only for phrasing when live mode is enabled.
4. Implement preference proposal/consent/delete flow.
5. Build 2D map and event/horizon interactions.
6. Add R3F progressive renderer with a strict object/texture budget. Avoid new
	 3D asset packages unless documented and approved.
7. Add mode rail and confirmation sheet.
8. Add voice dock and route commands to Phase 05/experience voice boundary.
9. Add AR-lite only after 2D/WebGL flows pass; keep it behind capability check.
10. Add mobile, keyboard, screen reader, reduced-motion and offline/replay QA.

## Test scenario matrix

| Case | Expected result |
|---|---|
| Manager loads snapshot | Full authorized operations projection |
| Employee loads snapshot | No customer private memory or owner-only audit |
| Customer loads snapshot | Public seating/menu guidance only |
| Replay persona switches role | Allowed only in fixture mode |
| Manager proposes rain mode | Confirmation proposal with affected projections |
| Employee confirms mode | 403 and no event |
| Taste recommendation | Approved menu result with reasons |
| Allergy not explicit | Ask user; never infer or store |
| Preference consent refused | No retained preference |
| Preference delete | Removed from subsequent snapshot |
| WebGL unsupported | 2D map complete |
| Camera denied | QR/text onboarding complete |
| Offline replay | Seeded living map and voice/text fixture work |
| Long Vietnamese labels | No overlap/overflow at mobile viewport |
| Reduced motion | No camera animation |

## Todo

- [ ] Add LivingCafeSnapshot and role projections.
- [ ] Add deterministic flavor catalog scorer and consent flow.
- [ ] Build 2D map, horizon and mode rail.
- [ ] Build progressive WebGL renderer with budget.
- [ ] Add voice dock and replay states.
- [ ] Add AR-lite capability-gated path.
- [ ] Add desktop/mobile/a11y/e2e tests.

## Success criteria

- [ ] Four role views show the same cafe with correct privacy projections.
- [ ] One manager mode activation changes the map only after confirmation.
- [ ] Customer receives a taste recommendation and can revoke stored preference.
- [ ] Employee receives a contextual voice/text briefing without private leakage.
- [ ] Experience works with WebGL, 2D, voice-live, voice-replay and voice-off.
- [ ] Playwright desktop and mobile tests pass at defined viewports.
- [ ] No new dependency is added without `docs/THIRD_PARTY.md` and license review.

## Risk assessment

- **Risk:** scope becomes a broad metaverse instead of a cafe product. **Signal:**
	a feature cannot be explained as a map interaction, role aid or consented
	memory. **Response:** reject it from Phase 06 and add it to a post-release
	backlog; do not weaken current acceptance.
- **Risk:** 3D performance makes demo unreliable. **Signal:** p95 frame time
	exceeds 32ms on the demo laptop or map takes >2s to interactive. **Response:**
	disable WebGL by default for low capability and ship 2D as the reliable demo.
- **Risk:** role projection leaks data. **Signal:** fixture snapshot contains a
	field not allowed by the projection matrix. **Response:** server-side schema
	test fails and endpoint is blocked.
- **Risk:** personalized recommendation is mistaken for medical advice. **Signal:**
	UI says “safe for allergy” without explicit verified data. **Response:** use
	“phù hợp theo khẩu vị bạn khai báo” and route allergies to human/menu source.

## Security and rollback

- Feature route requires auth except public customer demo mode with a separate
	public projection token containing no staff/private data.
- Camera/microphone permissions are requested only after user action.
- Enforce CSP/asset origin and sanitize all AI text before rendering.
- Rollback flags: `QUANVERSE_ENABLED`, `QUANVERSE_WEBGL_ENABLED`,
	`QUANVERSE_AR_ENABLED`; disabling them leaves existing routes unaffected.

## Handoff

Phase 07 owns the single end-to-end story: customer preference -> employee
brief -> manager mode -> audit. It must not introduce new product features.
