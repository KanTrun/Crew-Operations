# Verification — Grand AI Experience Portfolio (plan 260920-1442 Phase 07)

Ngày chạy: 2026-09-20. Branch: `feat/experience-contracts`. Chế độ: replay.

## Kết quả gate (đã chạy thực tế)

| Gate | Command | Kết quả |
|---|---|---|
| Contracts | `python scripts/export_contracts.py` | ✅ 52 schemas + TS types |
| Unit (grand) | `pytest packages/{contracts,agents,opsengine,playbook,tests} + apps/api/tests/unit/...` | ✅ **239 passed** |
| Ruff repo | `ruff check apps/api/src packages scripts` | ✅ All checks passed |
| Mypy (touched) | `mypy ...@<phase files> --no-error-summary` | ✅ sạch |
| Web typecheck | `cd apps/web && npm run typecheck` (tsc --noEmit) | ✅ pass |
| Web build | `npm run build` | ✅ pass (kể cả `/quanverse/*`) |
| e2e War Room | `playwright e2e/war-room.spec.ts` | ✅ 2/2 |
| e2e Shift Rescue | `playwright e2e/shift-rescue.spec.ts` | ✅ 2/2 |
| e2e Rules | `playwright e2e/experience-rules.spec.ts` | ✅ 2/2 |
| e2e Spatial | `playwright e2e/spatial-memory.spec.ts` (WebGL-off) | ✅ 3/3 |
| e2e Quanverse | `playwright e2e/quanverse.spec.ts` | ✅ 5/5 |
| e2e Quanverse mobile | `playwright e2e/quanverse-mobile.spec.ts` (390×844) | ✅ 2/2 |
| e2e Grand replay | `playwright e2e/grand-experience-replay.spec.ts` | ✅ 2/2 |
| Demo script | `python scripts/demo_grand_experience.py` | ✅ 6 bước replay |

## Tổng test

- Python unit+API+integration (experience): **239 passed**
- Playwright e2e (replay, WebGL-off): **18 passed**

## Đo lường sơ bộ (local)

- `make contracts`: < 5s.
- 239 pytest: ~20s.
- e2e suite: ~2-3 phút (chạy tuần tự worker=1, đúng cấu hình CI).
- Replay API snapshot `GET /api/v1/experience/quanverse/snapshot`: < 100ms local.
- War Room simulate 2 scenarios: < 200ms local (deterministic, no network).
- ghi chú: p95 chính thức cần máy demo chuẩn hoá (budget Phase 07 §Performance).

## Gap / ghi chú

- Không commit `.env`, secrets, audio hay dữ liệu khách thật (fixture có nhãn).
- `NHIPQUAN_EXPERIENCE_REPLAY_ROLE=1` chỉ cho role-switch demo; production
  luôn dùng role từ token.
- Voice audio thật deferred (replay-only trong MVP); AR-lite phần fallback được
  test, camera không gọi thật trong CI.
- 3D/WebGL progressive chưa render model thật — 2D là canonical cho acceptance.

## Branch protocol

Đang trên `feat/experience-contracts` (bắt buộc theo Phase 07: từng phase
commit Conventional Commits, squash-merge qua PR khi CI xanh). PI chưa push PR
trong phiên này — theo runbook người merge thực hiện sau khi review.