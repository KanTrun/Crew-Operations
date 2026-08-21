---
title: "NHIP QUAN Lot1 Full Delivery"
description: "Giao hàng toàn bộ Lô 1 NHỊP QUÁN theo hồ sơ v3.0 — 8 sprint + tuần 0, playbook AgentKit đầy đủ."
status: pending
priority: P1
effort: "8 weeks (104 person-days build + 36 harden)"
tags: [nhip-quan, lot1, agentkit, hutech-2026]
created: 2026-08-21
blockedBy: []
blocks: []
---

# NHỊP QUÁN — Kế hoạch Lô 1 Full Delivery

## Overview

Chuyển `NHIP-QUAN-HO-SO-TONG-THE .md` (v3.0) thành kế hoạch AgentKit có thể chạy: **tuần 0 + sprint 1–8**, 10 agent Lô 1, lõi tất định, Cẩm nang sống, nộp bán kết rồi bảo vệ. Nguồn sự thật nghiệp vụ vẫn là hồ sơ; plan này là **lịch giao hàng + lệnh vận hành**.

**Brainstorm:** [reports/260821-2221-brainstorm-nhip-quan-lot1.md](../reports/260821-2221-brainstorm-nhip-quan-lot1.md)

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | `main` luôn xanh; `make demo` chạy được mọi lúc | P1 |
| 2 | Ship 10 agent Lô 1 + 6 cổng VF + CP-SAT + opsengine + playbook | P1 |
| 3 | Một luật Cẩm nang sống đi hết 8 bước trên dữ liệu thật (hoặc nói thật nếu chưa đủ bằng chứng) | P1 |
| 4 | Nộp `v0.1.0-semifinal` (S6) và `v1.0.0-final` (S8) | P1 |
| 5 | 12 con số mục 18.2 = đo thật hoặc "chưa đo" + lý do; ngân sách 0 đồng kiểm được | P1 |

## Brainstorm contract (accepted)

| Field | Value |
|-------|-------|
| **Outcome** | Hệ điều hành quán ca-làm-việc-centric, Lô 1, demo + bảo vệ được |
| **Constraints** | 4 người, 0 đồng, điều phối/lõi không LLM, PR-only main, không POS |
| **Non-goals** | Lô 2 (4 agent), agent đã loại mục 6.3, module tài chính |
| **Acceptance** | Cổng ra từng sprint (mục 14) + 13 việc ngày 1–2 (18.1) + thẻ phiên bản |

## Architecture (from hồ sơ §5–§7, §11)

```
Người phê duyệt
      ▲
Bộ điều phối (deterministic) ── ghi DB duy nhất
      │
 ┌────┴────┬──────────┬──────────┐
 Làn đọc   Làn diễn   Làn học    Lõi (no agents)
 10 agents EXPLAIN/   AG-RULE    CP-SAT · rules ·
 Lô 1      BRIEF/SOP             opsengine · playbook
      │
 6 cổng VF (fail-closed) → người hoặc lõi
```

**Packages:** `contracts` · `solver` · `gates` · `opsengine` · `playbook` · `agents` · `apps/api` · `apps/web`

**Owners:** A solver/gates/ops/playbook · B api/orc/ci · C agents/router/eval · D web/tpl/docs

**Repo:** https://github.com/KanTrun/CA-C-NG-B-NG  
**GitHub ops detail:** [`docs/github-operating-model.md`](../../docs/github-operating-model.md) · [`docs/team.md`](../../docs/team.md)  
**Foundation brainstorm:** [reports/260821-2235-brainstorm-github-foundation.md](../reports/260821-2235-brainstorm-github-foundation.md)

---

## GitHub operating model (hồ sơ §12 — đầy đủ trong plan)

### Bốn vùng nhánh (không dùng nhánh cá nhân sống dài)

| Người | Vai trò | Tiền tố sở hữu | WIP (cấm PR vào main) |
|-------|---------|----------------|------------------------|
| **A** | Solver, gates, ops, playbook | `feat/solver-*` `feat/gates-*` `feat/ops-*` `feat/playbook-*` | `wip/a/...` |
| **B** | API, orchestration, CI, infra | `feat/api-*` `feat/orc-*` `ci/*` `chore/infra-*` | `wip/b/...` |
| **C** | Agents, router, eval | `feat/agents-*` `feat/router-*` `feat/eval-*` | `wip/c/...` |
| **D** | Web, templates, docs | `feat/web-*` `feat/tpl-*` `docs/*` | `wip/d/...` |

**Luật:** feat sống ≤3 ngày · tối đa 2 nhánh mở/người · `git pull --rebase origin main` hằng ngày · **squash merge** vào `main` · `release/semifinal` (S6) · `release/final` (S8) · tags `v0.1.0-semifinal` / `v1.0.0-final`.

### CODEOWNERS (path → owner)

| Path | Review bắt buộc |
|------|-----------------|
| `/packages/solver|gates|opsengine|playbook/` | A |
| `/packages/agents/` | C |
| `/apps/api/` (trừ orchestration) | B |
| `/apps/api/**/orchestration/` | B **và** A |
| `/apps/web/` · `/infra/templates/` · `/docs/` | D |
| `/infra/` · `/.github/` | B |
| `/packages/contracts/` | A+B+C+D |

Handle GitHub: xem `docs/team.md` (hiện `@KanTrun` tạm mọi vùng cho đến khi đủ 4 account).

### Conventional Commits

`feat|fix|refactor|perf|test|docs|chore|ci` + scope `solver|gates|ops|playbook|api|orc|agents|router|web|tpl|contracts|infra`

### Mười một cổng CI

Lint/type · unit (≥85% packages/domain) · integration · architecture AST · solver bench · agent eval · web · e2e (main/release) · Docker build · no live LLM in tests · YAML templates.

### Bảo vệ `main`

PR bắt buộc · 1 duyệt CODEOWNERS · dismiss stale reviews · CI xanh · branch up to date · cấm force-push/xoá · áp dụng cả admin (bật khi repo có ≥2 collaborator).

---

## Playbook lệnh AgentKit (toàn dự án)

### A. Vòng đời dự án (bắt buộc theo thứ tự)

| Khi nào | Lệnh / skill | Việc |
|---------|----------------|------|
| Lần đầu | `ak doctor` → `ak init` (nếu cần) → `git init` trong monorepo | Kiểm môi trường AgentKit |
| Chốt ý định | `/ak:brainstorm` ✅ đã chạy | Outcome / constraints / non-goals / acceptance |
| Lập kế hoạch | `/ak:plan` → `ak plan create` ✅ · `ak plan add-phase` ✅ | Plan + phases trên đĩa |
| Ghim plan | `ak plan use <plan-dir>` | Worktree biết plan đang active |
| Theo dõi | `ak plan status` · `ak plan kanban` · `ak plan validate` | Tiến độ / TUI / format |
| Mỗi phase | `/ak:cook` (hoặc `/ak:cook --parallel` khi độc lập) | Implement đúng phase |
| Bug | `/ak:fix` (sau scout + root cause) | Sửa nguyên nhân, không vá triệu chứng |
| PR / merge | `/ak:ship` + CODEOWNERS | Squash merge vào `main` |
| Cuối sprint | `/ak:journal` · `/ak:retro` | Ghi nhật ký + rút kinh nghiệm |
| Đóng plan | `ak plan check <phase>` · `ak plan close` · `ak plan archive` | Đóng phase/plan |

### B. Lệnh theo loại công việc

| Việc trong hồ sơ | AgentKit |
|------------------|----------|
| Nghiên cứu hạn mức LLM, LICENSE, Bộ luật LĐ (18.3) | `/ak:research` |
| Khởi tạo monorepo, Makefile, pre-commit | `/ak:bootstrap` hoặc cook phase T0/S1 |
| Schema DB + Alembic | `/ak:databases` |
| CI 11 cổng, Docker, bảo vệ `main` | `/ak:devops` |
| **UI/UX xuất sắc (bắt buộc khi chạm web)** | xem **§ UI/UX AgentKit pipeline** bên dưới |
| Viết ADR / runbook / hồ sơ nộp | `/ak:docs` |
| Kim tự tháp 215 tests, Playwright | `/ak:test` · `/ak:web-testing` |
| Quét secret / dependency | `/ak:security-scan` |
| Review PR theo checklist §12.4 | `/ak:code-review` |
| Dashboard plan | `ak gui` hoặc `ak config` → `http://localhost:3456/plans` |
| Reindex nếu sửa tay lệch store | `ak plan reindex` |

### UI/UX AgentKit pipeline (bắt buộc cho mọi `feat/web-*`)

**Hợp đồng thẩm mỹ:** [`docs/design-guidelines.md`](../../docs/design-guidelines.md)  
**Brainstorm:** [reports/260821-2249-brainstorm-uiux-pipeline.md](../reports/260821-2249-brainstorm-uiux-pipeline.md)

| Bước | Lệnh | Việc |
|------|------|------|
| 0 | Đọc `docs/design-guidelines.md` | Không được bỏ qua tokens / register / dials |
| 1 | `/ak:ui-ux-pro-max` | Style, palette, type, a11y, touch 44×44, UX rules theo product type *cafe ops PWA* |
| 2 | `/ak:frontend-design` | Craft anti-slop: composition, motion, states; **Product register** |
| 3 | (tuỳ chọn) `/ak:stitch` | Mockup annotated trước khi code nếu cần preview |
| 4 | `/ak:frontend-development` | Implement Next.js/PWA đúng tokens |
| 5 | `/ak:web-testing` | a11y + mobile + visual smoke |
| 6 | Self-review gate Frontend Design | Contrast, reduced-motion, one-hand phiếu |

**Dials (Product app — quản lý + nhân viên):**

| Dial | Giá trị | Lý do |
|------|---------|--------|
| `DESIGN_VARIANCE` | **3** | Lưới lịch / phiếu cần quen thuộc, không art-direction loạn |
| `MOTION_INTENSITY` | **2** | 150–250ms state only; không page-load choreography |
| `VISUAL_DENSITY` | **6** | Nhiều thông tin ca/tuần; hairline + mono số; **không** card-slop |

**Cấm khi cook web:** Inter/Roboto mặc định · purple-on-white · cream+terracotta cliché · emoji-as-icon · hero overlay badges · bỏ focus ring.

**Lệnh copy-paste mỗi PR web:**

```text
/ak:ui-ux-pro-max "NHIP QUAN cafe shift PWA — roster grid, mobile run-form one-hand, playbook, fairness board"
/ak:frontend-design  # dials 3/2/6, Product register, follow docs/design-guidelines.md
/ak:frontend-development
/ak:web-testing
```

### C. Makefile (sản phẩm) — chạy mỗi ngày / mỗi PR

`make setup|contracts|dev|test|test-unit|lint|bench|eval|ab|replay|budget|seed|demo|demo-reset`

### D. Nhịp tuần chuẩn (mọi sprint)

```text
Thứ 2  ak plan status · /ak:cook phase hiện tại (A∥B∥C∥D theo vùng nhánh)
Giữa tuần  /ak:code-review trên PR · make test-unit cục bộ
Thứ 6  cổng ra sprint (mắt + lệnh) · /ak:journal · /ak:retro ngắn
        nếu xanh: ak plan check phase-N · mở phase N+1
        nếu đỏ: cắt phạm vi đúng hồ sơ (không cắt ràng buộc cứng)
```

### E. Map phase → skill cook chính

| Phase | Cook focus | Skills phụ |
|-------|------------|------------|
| 01 T0 | Research + docs + **seed design-guidelines** | research, docs, devops |
| 02 S1 | Contracts + **PWA shell qua UI pipeline** | ui-ux-pro-max → frontend-design → frontend-development |
| 03 S2 | Solver + AG-TKB + **lưới lịch (UI pipeline)** | A/C cook + D: full UI pipeline |
| 04 S3 | Ops + **phiếu mobile one-hand (UI pipeline)** | ui-ux-pro-max → frontend-design → web-testing |
| 05 S4 | Quán thật + fairness/today boards | UI pipeline + ship |
| 06 S5 | Playbook + SOP chat UI | UI pipeline + e2e |
| 07 S6 | Semifinal package | docs, ship tag |
| 08 S7 | Harden + đo — **no features** | test, security-scan, journal |
| 09 S8 | Freeze + demo drill | ship final, retro |

---

## Phases

| # | Phase | Status | Effort | Depends |
|---|-------|--------|--------|---------|
| 1 | [Tuần 0 — Ngày 1–2 & chuẩn bị](./phase-01-start.md) | Pending | 2 ngày | — |
| 2 | [Sprint 1 — Nền và hợp đồng](./phase-02-sprint-1-nen-va-hop-dong.md) | Pending | 17,25 md | 1 |
| 3 | [Sprint 2 — Mốc sinh tử solver](./phase-03-sprint-2-moc-sinh-tu-solver.md) | Pending | 17,75 md | 2 |
| 4 | [Sprint 3 — Vận hành & ghi nhận sửa](./phase-04-sprint-3-van-hanh-va-ghi-nhan-sua.md) | Pending | 18,00 md | 3 |
| 5 | [Sprint 4 — Quán dùng thật](./phase-05-sprint-4-qun-dung-that.md) | Pending | 18,00 md | 4 |
| 6 | [Sprint 5 — Cẩm nang sống](./phase-06-sprint-5-cam-nang-song.md) | Pending | 17,25 md | 5 |
| 7 | [Sprint 6 — Nộp bán kết](./phase-07-sprint-6-nop-ban-ket.md) | Pending | 14,75 md | 6 |
| 8 | [Sprint 7 — Làm cứng và đo](./phase-08-sprint-7-lam-cung-va-do.md) | Pending | 18 md | 7 |
| 9 | [Sprint 8 — Đóng băng và bảo vệ](./phase-09-sprint-8-dong-bang-va-bao-ve.md) | Pending | 18 md | 8 |

## Backlog sau bảo vệ (không cook trong plan này)

- Lô 2: AG-FORECAST · AG-INVOICE · AG-SHELF · AG-MENUOPS (mục 13.6)
- Tích hợp POS chỉ khi quán đồng ý (mở lại Barista Copilot)

## Success Criteria (toàn plan)

- [ ] 13 việc 18.1 xong trước khi mở Sprint 1 đầy đủ
- [ ] Mốc sinh tử 1 (S2): lịch 25 người, 0 vi phạm cứng, kiểm bằng script độc lập
- [ ] Mốc sinh tử 2 (S4): lịch tuần + ≥5 phiếu thật tại quán
- [ ] S5: ≥1 luật đi hết 8 bước **hoặc** thuyết trình trung thực về số luật thật
- [ ] S6: ≥165 tests, tag `v0.1.0-semifinal`, 10× `PHAM_VI.md`, 11 ADR
- [ ] S7: 215 tests; 12 số mục 18.2 hoàn tất
- [ ] S8: tag `v1.0.0-final`; demo 10 phút ×5, ≥2 lần offline
- [ ] Chi phí dự án = 0 đồng kiểm được (sổ 14 dòng)

## Risk register (rút từ §16)

| Risk | Signal | Pre-decided response |
|------|--------|----------------------|
| Không có quán | T0 việc 1 trễ >48h | Chuyển quán dự bị ngay |
| Trượt mốc S2 | Soft constraint >60s / vi phạm | Cắt soft 5→3 + ADR; **không** cắt cứng |
| Quán không đổi giữa tuần (S4) | 0 phiếu thật | Lùi công bố lịch; ưu tiên 1 ca thử |
| Không đủ 3 lần sửa cùng mẫu (S5) | Bảng ghi nhận trống mẫu | Demo trên lịch sử dựng lại; nói số thật |
| Hết hạn mức LLM | `make budget` vượt | Router → Ollama; tắt agent không critical |

## Next command

```bash
ak plan use ./plans/260821-2221-nhip-quan-lot1-full-delivery
ak plan validate ./plans/260821-2221-nhip-quan-lot1-full-delivery
# rồi: /ak:cook phase-01 (Tuần 0) — ưu tiên xin quán + chốt contracts
```

<!-- slug: nhip-quan-lot1-full-delivery -->
