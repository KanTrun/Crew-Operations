# NHỊP QUÁN

**Crew Operations** — hệ sinh thái AI agent vận hành quán cà phê. Ca làm việc là hạt nhân; cẩm nang tự viết là bộ nhớ; điều phối lõi **không** dùng LLM.

| | |
|---|---|
| **Sản phẩm** | NHỊP QUÁN |
| **Repository** | [**KanTrun/Crew-Operations**](https://github.com/KanTrun/Crew-Operations) |
| **Clone** | `git clone https://github.com/KanTrun/Crew-Operations.git` |
| **Cuộc thi** | Xây dựng Hệ điều hành Doanh nghiệp số AI · Khoa CNTT HUTECH · 2026 |
| **Hồ sơ** | [`NHIP-QUAN-HO-SO-TONG-THE .md`](./NHIP-QUAN-HO-SO-TONG-THE%20.md) |
| **Kế hoạch Lô 1** | [`plans/260821-2221-nhip-quan-lot1-full-delivery/`](./plans/260821-2221-nhip-quan-lot1-full-delivery/) |
| **Kết quả đo §18.2** | [`docs/ket-qua-tong-hop.md`](./docs/ket-qua-tong-hop.md) |

> **Tên repo vs tên sản phẩm:** GitHub là **Crew-Operations**; phần mềm và UI vẫn là **NHỊP QUÁN**. Tên thư mục clone trên máy (có thể có dấu tiếng Việt) **không** bắt buộc trùng tên repo.

---

## Tóm tắt

Monorepo gồm **lõi tất định** (CP-SAT xếp ca, cổng VF fail-closed, opsengine) và **10 agent Lô 1** (AG-TKB, AG-MSG, …) phục vụ quản lý quán qua web PWA + kênh tin (Telegram / Zalo / Facebook Page). Mọi thay đổi lịch và hiệu lực ca đi qua **người phê duyệt** — agent chỉ trích xuất và đề xuất.

```
Người phê duyệt
      ▲
Điều phối (deterministic) ── ghi store duy nhất
      │
 ┌────┴────┬──────────┬──────────┐
 Agents    EXPLAIN/    AG-RULE    Lõi: solver · gates ·
 Lô 1      BRIEF/SOP              opsengine · playbook
```

---

## Cấu trúc monorepo

| Thành phần | Đường dẫn | Vai trò |
|------------|-----------|---------|
| Hợp đồng dữ liệu | `packages/contracts` | JSON Schema · TypeScript types |
| Solver | `packages/solver` | CP-SAT, ràng buộc cứng C01–C06 |
| Cổng VF | `packages/gates` | VF-TRACE, VF-CONF, VF-SCHEMA, … |
| Ops | `packages/opsengine` | Việc treo, nhắc, sổ tiêu thụ |
| Playbook | `packages/playbook` | Cẩm nang 8 bước, ghi nhận sửa |
| Agents | `packages/agents` | AG-TKB, AG-MSG, router LLM, messaging ports |
| API | `apps/api` | FastAPI · SQLite/Postgres · worker |
| Web | `apps/web` | Next.js PWA (quản lý, NV, inbox, page quán) |
| Infra | `infra/docker` | Compose: postgres, redis, api, worker, web |
| Plans | `plans/` | AgentKit phases, journals, brainstorm |
| Scripts | `scripts/` | Demo, eval, solver, Docker wrapper |

---

## Yêu cầu

- **Python** ≥ 3.12 · **Node** ≥ 20 (web)
- **Docker Desktop** (khuyến nghị demo toàn tuyến)
- File **`.env`** ở root (copy từ [`.env.example`](./.env.example) — **không commit**)

---

## Chạy nhanh (Docker — khuyến nghị)

```bash
git clone https://github.com/KanTrun/Crew-Operations.git
cd Crew-Operations          # hoặc thư mục bạn đặt tên
cp .env.example .env        # điền key LLM / kênh tin nếu cần live
make docker-up              # = python scripts/docker_stack.py up
make docker-smoke
```

| Dịch vụ | URL |
|---------|-----|
| Web | http://localhost:3000 |
| API + OpenAPI | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Postgres | `localhost:5432` |
| Redis | `localhost:6379` |

Dừng: `make docker-down` · Xóa volume: `make docker-reset`

> **Windows:** BuildKit có thể lỗi khi đường dẫn clone có ký tự non-ASCII. Clone/junction sang đường dẫn ASCII, ví dụ `C:\nhipquan` — chi tiết [`docs/runbook-demo.md`](./docs/runbook-demo.md).

`docker_stack.py` tự đọc `.env` ở root (`--env-file`) và mount vào container `api` / `worker`.

---

## Chạy local (không Docker)

```bash
make setup
make demo-local
cd apps/web && npm run dev
```

Tài khoản demo: [`docs/runbook-demo.md`](./docs/runbook-demo.md) (`lan` / `hung` / `minh` · mật khẩu `nhipquan`).

---

## Biến môi trường chính

| Biến | Mục đích |
|------|----------|
| `CA_AGENT_MODE` | `replay` (CI) hoặc `live` (LLM thật) |
| `GROQ_API_KEY` / `GEMINI_API_KEY` / `OPENROUTER_API_KEY` | Router LLM khi live |
| `NHIPQUAN_MSG_BACKEND` | `telegram` · `zalo` · `console` |
| `NHIPQUAN_FB_PAGE_TOKEN` / `NHIPQUAN_FB_PAGE_ID` | Facebook Page quán |
| `NHIPQUAN_PAGE_MODE` | `live` khi nối Meta |
| `NHIPQUAN_FB_WEBHOOK_VERIFY` | Verify token webhook Messenger |

Runbook: [Telegram](./docs/runbooks/telegram-bot-connect.md) · [Zalo](./docs/runbooks/zalo-oa-connect.md) · [Facebook Page](./docs/runbooks/facebook-page-connect.md)

---

## Makefile (tóm tắt)

| Lệnh | Mô tả |
|------|--------|
| `make setup` | Cài Python editable + npm web |
| `make test` | Pytest toàn monorepo (`CA_AGENT_MODE=replay`) |
| `make lint` | Ruff + ESLint web |
| `make bench` | Solver tuần + `verify_hard` |
| `make eval` | AG-TKB, AG-MSG, nhóm A §18.2 |
| `make metrics` | Bảng metrics fixture ADR-012 |
| `make seed-ops` | 6 bề mặt vận hành (host) |
| `make docker-up` / `docker-down` / `docker-smoke` / `docker-reset` | Stack Docker qua `scripts/docker_stack.py` |
| `make demo` / `demo-reset` | Demo API / reset Docker |

---

## GitHub — nhánh & quy trình

**Remote:** `https://github.com/KanTrun/Crew-Operations.git`

Chi tiết đầy đủ: [`docs/github-operating-model.md`](./docs/github-operating-model.md) · [`docs/phan-cong-nhanh.md`](./docs/phan-cong-nhanh.md) · [`docs/team.md`](./docs/team.md)

### Nhánh gốc

| Nhánh | Vai trò |
|-------|---------|
| `main` | Nguồn sự thật — luôn xanh, luôn demo được |
| `release/semifinal` | Đóng băng tuần 6 → tag `v0.1.0-semifinal` |
| `release/final` | Đóng băng tuần 8 → tag `v1.0.0-final` |

> Nếu GitHub default branch vẫn là `chore/infra-bootstrap`, đổi về **`main`** trong Settings → General trước khi bật branch protection (hồ sơ §12).

### Bốn vùng sở hữu (tiền tố nhánh)

| Người | Tiền tố nhánh | Sở hữu chính |
|-------|---------------|--------------|
| **A** | `feat/solver-*` `feat/gates-*` `feat/ops-*` `feat/playbook-*` | solver, gates, opsengine, playbook |
| **B** | `feat/api-*` `feat/orc-*` `ci/*` `chore/infra-*` | api, orchestration, CI, infra, Docker |
| **C** | `feat/agents-*` `feat/router-*` `feat/eval-*` | agents, router, eval, messaging |
| **D** | `feat/web-*` `feat/tpl-*` `docs/*` | Next.js PWA, YAML templates, docs |

**WIP:** `wip/a|b|c|d/...` — thử nghiệm, **cấm** PR thẳng vào `main`.

**Luật:** nhánh `feat/*` ≤ 3 ngày · ≤ 2 nhánh mở/người · `git pull --rebase origin main` hằng ngày · vào `main` chỉ qua **squash merge** + PR.

### Nhánh feature đang có trên remote

| Nhánh | Vùng | Nội dung (tóm tắt) |
|-------|------|---------------------|
| `feat/solver-luat-inject` | A | Bơm luật hiệu lực vào CP-SAT |
| `feat/api-hom-nay-tieu-thu` | B | `/me`, hôm nay, sổ tiêu thụ, giải CP-SAT |
| `feat/api-channels-va-tkb-upload` | B | Kênh tin, upload TKB |
| `chore/infra-docker-full-stack` | B | Docker 5 dịch vụ, smoke, volume |
| `chore/infra-bootstrap` | B | Bootstrap monorepo ban đầu |
| `feat/eval-ab-replay` | C | A/B và replay điều phối |
| `feat/agents-messaging-va-tkb-anh` | C | Messaging ports, TKB ảnh |
| `feat/ops-sprint3-van-hanh` | A/B | Sprint 3 vận hành |
| `feat/web-ops-ui` | D | UI kit, session, API layer |
| `feat/web-tkb-kenh-va-ux` | D | TKB, kênh, UX |
| `feat/web-premium-ops-v3` | D | Premium ops UI v3 |
| `feat/web-awwwards-redesign` | D | Redesign web |
| `fix/web-trang-thai-tai` | D | Sửa trạng thái tải web |
| `ci/e2e-va-docker-smoke` | B | Playwright e2e + Docker smoke CI |
| `docs/runbook-va-trang-thai` | D | Runbook demo, trạng thái plan |
| `docs/runbook-kenh-tin-va-tkb` | D | Runbook kênh tin + TKB |

Thứ tự merge chồng PR (nhánh 1→7): xem [`docs/phan-cong-nhanh.md` §3](./docs/phan-cong-nhanh.md).

### Làm việc trên nhánh feature

```bash
git fetch origin
git checkout feat/your-branch
git pull --rebase origin main    # cập nhật từ main hằng ngày
# ... commit ...
git push -u origin feat/your-branch
gh pr create --base main
```

### Lịch sử đổi tên repo (GitHub redirect tự động)

`CA-C-NG-B-NG` → `CA-CONG-BANG` → **`Crew-Operations`** (hiện tại). Link/clone cũ vẫn chuyển hướng; ưu tiên dùng **Crew-Operations** trong docs và `git remote`.

---

## Quy tắc bất biến

1. Hợp đồng dữ liệu trước, mã nguồn sau  
2. `main` luôn xanh và luôn demo được  
3. Không vào `main` nếu không qua PR được duyệt  
4. Không LLM ghi lịch / điều phối  

---

## Tài liệu

| Tài liệu | Nội dung |
|----------|----------|
| [`docs/runbook-demo.md`](./docs/runbook-demo.md) | Demo &lt; 5 phút |
| [`docs/phan-cong-nhanh.md`](./docs/phan-cong-nhanh.md) | Chia việc nhánh, thứ tự merge |
| [`docs/github-operating-model.md`](./docs/github-operating-model.md) | PR, CI 11 cổng, commits |
| [`docs/ket-qua-tong-hop.md`](./docs/ket-qua-tong-hop.md) | 12 con số hồ sơ §18.2 |
| [`docs/runbooks/`](./docs/runbooks/) | Kết nối Telegram, Zalo, Facebook |
| [`THIRD_PARTY.md`](./THIRD_PARTY.md) | Phụ thuộc & license |

---

## Kế hoạch phụ (repo)

| Plan | Trạng thái |
|------|------------|
| [`260821-2221` Lô 1 full delivery](./plans/260821-2221-nhip-quan-lot1-full-delivery/) | Sprint 1–6 done · 7–8 pending |
| [`260827-1438` Kênh tin + Facebook](./plans/260827-1438-kenh-tin-telegram-zalo-va-facebook-page/) | Phase 1–6 done · Phase 7 pending (chờ kết nối Page thật ngoài repo) |
| [`260827-2243` Inbox ↔ TKB](./plans/260827-2243-noi-logic-lich-inbox-tkb/) | Completed (11 edge cases, solver wire, UI modal, 11 tests pass) |
| [`260827` TKB từ ảnh](./plans/260827-tkb-anh-upload-xac-nhan/) | Completed |
| [`260830-0930` TikTok Apify](./plans/260830-0930-tiktok-apify-primary-tiktokwm-fallback/) | Completed (code + 22 tests pass) |
| [`260831-0107` Nâng cấp Ops UI](./plans/260831-0107-nang-cap-mat-van-hanh-ops-ui/) | Completed (picker, hub, API đổi ca — merge `d50b0f5`) |
| [`260831-1159` Roster lưới tóm tắt](./plans/260831-1159-roster-luoi-tom-tat-va-khung-gio/) | Completed (lưới tuần zebra + PATCH khung giờ — merge `fce0383`) |
| [`260901` Copilot bỏ data cứng](./plans/260901-copilot-bo-data-cung/) | Completed (data thật, apply thật, SSE stream, 475 tests — merge PR #27) |

