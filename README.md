# NHỊP QUÁN

**Crew Operations** — hệ sinh thái AI agent vận hành quán cà phê. Ca làm việc là hạt nhân; cẩm nang tự viết là bộ nhớ; điều phối lõi không dùng LLM.

| | |
|---|---|
| **Sản phẩm** | NHỊP QUÁN |
| **Repository** | [github.com/KanTrun/Crew-Operations](https://github.com/KanTrun/Crew-Operations) |
| **Cuộc thi** | Xây dựng Hệ điều hành Doanh nghiệp số AI · Khoa CNTT HUTECH · 2026 |
| **Hồ sơ** | [`NHIP-QUAN-HO-SO-TONG-THE .md`](./NHIP-QUAN-HO-SO-TONG-THE%20.md) |
| **Kế hoạch Lô 1** | [`plans/260821-2221-nhip-quan-lot1-full-delivery/`](./plans/260821-2221-nhip-quan-lot1-full-delivery/) |
| **Kết quả đo §18.2** | [`docs/ket-qua-tong-hop.md`](./docs/ket-qua-tong-hop.md) |

---

## Tóm tắt

Monorepo gồm **lõi tất định** (CP-SAT xếp ca, cổng VF fail-closed, opsengine) và **10 agent Lô 1** (AG-TKB, AG-MSG, …) phục vụ quản lý quán qua web PWA + kênh tin (Telegram / Zalo / Facebook Page). Mọi thay đổi lịch và hiệu lực ca đi qua người phê duyệt — agent chỉ trích xuất và đề xuất.

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

## Cấu trúc repo

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

---

## Yêu cầu

- **Python** ≥ 3.12 · **Node** ≥ 20 (web)
- **Docker Desktop** (khuyến nghị demo toàn tuyến)
- File **`.env`** ở root (copy từ [`.env.example`](./.env.example), không commit)

---

## Chạy nhanh (Docker — khuyến nghị)

Dùng wrapper để tránh lỗi BuildKit khi clone vào thư mục có dấu tiếng Việt:

```bash
cp .env.example .env   # điền key LLM / kênh tin nếu cần live
make docker-up         # = python scripts/docker_stack.py up
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

> **Windows:** nếu build lỗi header non-ASCII, clone hoặc junction sang đường dẫn ASCII, ví dụ `C:\nhipquan` — xem [`docs/runbook-demo.md`](./docs/runbook-demo.md).

---

## Chạy local (không Docker)

```bash
make setup
make demo-local          # API + hướng dẫn web
cd apps/web && npm run dev
```

Đăng nhập demo: xem [`docs/runbook-demo.md`](./docs/runbook-demo.md) (tài khoản `lan` / `hung` / `minh`).

---

## Biến môi trường chính

| Biến | Mục đích |
|------|----------|
| `CA_AGENT_MODE` | `replay` (CI) hoặc `live` (LLM thật) |
| `GROQ_API_KEY` / `GEMINI_API_KEY` / `OPENROUTER_API_KEY` | Router LLM khi live |
| `NHIPQUAN_MSG_BACKEND` | `telegram` · `zalo` · `console` |
| `NHIPQUAN_FB_PAGE_TOKEN` / `NHIPQUAN_FB_PAGE_ID` | Facebook Page quán |
| `NHIPQUAN_PAGE_MODE` | `live` khi nối Meta |

Chi tiết: [`.env.example`](./.env.example) · runbook [Telegram](./docs/runbooks/telegram-bot-connect.md) · [Zalo](./docs/runbooks/zalo-oa-connect.md) · [Facebook Page](./docs/runbooks/facebook-page-connect.md).

---

## Makefile

| Lệnh | Mô tả |
|------|--------|
| `make setup` | Cài Python editable + npm web |
| `make test` | Pytest toàn monorepo (`CA_AGENT_MODE=replay`) |
| `make lint` | Ruff + ESLint web |
| `make bench` | Solver tuần + `verify_hard` |
| `make eval` | AG-TKB, AG-MSG, nhóm A §18.2 |
| `make metrics` | Bảng metrics fixture ADR-012 |
| `make seed-ops` | 6 bề mặt vận hành (host) |
| `make docker-seed-ops` | Cùng seed trong container |
| `make demo` / `demo-reset` | Demo API / reset Docker |

---

## Đội & GitHub

- [`docs/team.md`](./docs/team.md) — map vai trò A/B/C/D  
- [`docs/github-operating-model.md`](./docs/github-operating-model.md) — nhánh, PR, CI, tags  

| Vai trò | Vùng nhánh | Sở hữu chính |
|---------|------------|--------------|
| A | `feat/solver-*` `feat/gates-*` `feat/ops-*` `feat/playbook-*` | solver, gates, opsengine, playbook |
| B | `feat/api-*` `feat/orc-*` `ci/*` `chore/infra-*` | api, orchestration, CI, infra |
| C | `feat/agents-*` `feat/router-*` `feat/eval-*` | agents, router, eval |
| D | `feat/web-*` `feat/tpl-*` `docs/*` | web PWA, templates, docs |

**Tags phát hành:** `v0.1.0-semifinal` · `v1.0.0-final`

---

## Quy tắc bất biến

1. Hợp đồng dữ liệu trước, mã nguồn sau  
2. `main` luôn xanh và luôn demo được  
3. Không vào `main` nếu không qua PR được duyệt  
4. Không LLM ghi lịch / điều phối  

---

## Tài liệu thêm

| Tài liệu | Nội dung |
|----------|----------|
| [`docs/runbook-demo.md`](./docs/runbook-demo.md) | Demo &lt; 5 phút |
| [`docs/phan-cong-nhanh.md`](./docs/phan-cong-nhanh.md) | Chia việc nhánh |
| [`docs/ket-qua-tong-hop.md`](./docs/ket-qua-tong-hop.md) | 12 con số hồ sơ |
| [`THIRD_PARTY.md`](./THIRD_PARTY.md) | Phụ thuộc & license |

---

*Repository **Crew-Operations** chứa mã nguồn sản phẩm **NHỊP QUÁN**. Tên thư mục clone trên máy có thể khác (ví dụ đường dẫn có dấu) — không ảnh hưởng tên repo GitHub.*
