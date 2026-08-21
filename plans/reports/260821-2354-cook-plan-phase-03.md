# Cook plan — Phase 03 / Sprint 2 (mốc sinh tử solver)

**Mode:** interactive (await approval before implement)  
**Branch:** `feat/solver-sprint2-moc-sinh-tu` (A-owned prefix; B/C/D land via same PR slices or follow-up)  
**Depends:** phase-02 on `main` ✓

## Brainstorm contract (reuse phase + §14.3)

| Field | Content |
|-------|---------|
| **Outcome** | Một lệnh CLI sinh lịch tuần 25×21; script độc lập báo **0** vi phạm cứng; 6 cổng §14.3 xanh |
| **Constraints** | Không cắt cứng; soft có thể 5→3 + ADR nếu trượt; không bịa số AG-TKB; OR-Tools CP-SAT; chi phí LLM = 0 / replay+free stub |
| **Non-goals** | VF-CONFLICT/NUM/RULE; opsengine swap; Cẩm nang sống; POS; quán thật |
| **Acceptance** | Sáu điều §14.3 (dưới) + `make bench` / property fairness 8 tuần |

## Scout summary

Hard checkers c01–c06 + seed 25×21×8 có sẵn. **Thiếu:** CP-SAT, soft×5, sổ nợ, verify CLI độc lập, VF×3, AG-TKB thật, router 4 provider, roster grid, Alembic. Compose 5 service đã có.

## Workstreams (full phase scope)

### Wave A — P0 mốc (gates 1–3)
1. Add `ortools` to `packages/solver`; ADR-004 (CP-SAT), ADR-005/006 (fairness min-max debt)
2. CP-SAT model: vars NV×Ca; hard c01–c06 as constraints; soft s01–s05 as penalties (or cut to 3 + ADR if needed)
3. Fairness debt 4D (cuối tuần / đêm / giờ / vụn); objective minimize max debt
4. CLI `scripts/solve_tuan.py` + `make bench` — timeout 60s, print schedule + timing
5. **Independent** `scripts/verify_hard.py` — reuse checker modules, never trust `SolveResult` alone
6. Adapter seed → `LichInput` (+ synthetic TKB/leave so feasible)
7. Property test: 8 consecutive weeks, max-debt gap does not explode

### Wave B — P1 gates 4–5 + infra
1. `packages/gates`: `vf_schema`, `vf_trace`, `vf_conf` + tests; blur fixture → escalate người
2. AG-TKB package + golden eval script; write real accuracy into `docs/metrics-18-2.md` (honest number)
3. Router: groq / gemini / openrouter / ollama stubs + replay (no paid calls in CI)
4. Alembic skeleton + 1–2 core tables; JWT/session stub enforcing 3 roles on protected routes
5. Branch protection docs note (optional live enable — may skip if GitHub free limits)

### Wave C — P1 gate 6 (D)
1. Web `/roster`: grid đọc lịch từ mock API `GET /api/v1/lich-tuan`
2. Minimal pin/block UX (drag optional if time; read + pin/block satisfies “đọc được”)
3. TKB upload page stub + confirm cạnh ảnh (wire to VF-CONF escalate path)

### Wave D — ship
1. CI: enable real solver-bench job (not stub)
2. Phase file + `plan.md` → completed when gates green
3. PR → merge when CI green

## Demo command (acceptance)

```bash
make seed && make bench          # solve ≤60s
python scripts/verify_hard.py    # all hard lines = 0
cd apps/web && npm run dev       # /roster shows schedule
```

## Risk response (pre-decided)

Hard violation >0 or infinite solve → cut soft 5→3 + ADR; **never** cut hard.

## Out of this cook if blocked

Live GitHub branch protection UI settings (document instead). Real café data (keep ADR-012 fixture).
