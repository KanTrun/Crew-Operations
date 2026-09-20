<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:3E2723,50:6F4E37,100:C68B59&height=200&section=header&text=Crew%20Operations&fontSize=54&fontColor=ffffff&animation=fadeIn&fontAlignY=36&desc=NHIP%20QUAN&descAlignY=58&descSize=20" width="100%" alt="Crew Operations banner" />

<img src="./logo.png" alt="NHỊP QUÁN — Crew Operations" width="150" />

# ☕ NHỊP QUÁN

### Hệ điều hành vận hành quán cà phê bằng AI agent

**Ca làm việc là hạt nhân** &nbsp;·&nbsp; **Cẩm nang tự viết là bộ nhớ** &nbsp;·&nbsp; **Điều phối lõi không dùng LLM**

<br/>

[![CI](https://github.com/KanTrun/Crew-Operations/actions/workflows/ci.yml/badge.svg)](https://github.com/KanTrun/Crew-Operations/actions/workflows/ci.yml)
[![Skills Verify](https://github.com/KanTrun/Crew-Operations/actions/workflows/skills-verify.yml/badge.svg)](https://github.com/KanTrun/Crew-Operations/actions/workflows/skills-verify.yml)
[![Docker GHCR](https://github.com/KanTrun/Crew-Operations/actions/workflows/docker-ghcr.yml/badge.svg)](https://github.com/KanTrun/Crew-Operations/actions/workflows/docker-ghcr.yml)

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![OR-Tools](https://img.shields.io/badge/OR--Tools-CP--SAT-4285F4?style=for-the-badge&logo=google&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

<br/>

[🚀 **Bắt đầu nhanh**](#cai-dat) &nbsp;•&nbsp;
[🏗 **Kiến trúc**](#gioi-thieu) &nbsp;•&nbsp;
[🔌 **API**](#api-reference) &nbsp;•&nbsp;
[🤖 **Agents**](#agents) &nbsp;•&nbsp;
[🧠 **Skills**](#skills) &nbsp;•&nbsp;
[📚 **Tài liệu**](#tai-lieu)

</div>

<br/>

<table align="center">
  <tr>
    <td align="center" width="140"><h2>21</h2><sub>AI agent</sub></td>
    <td align="center" width="140"><h2>14</h2><sub>kỹ năng đã kiểm định</sub></td>
    <td align="center" width="140"><h2>17+</h2><sub>router API</sub></td>
    <td align="center" width="140"><h2>~36</h2><sub>route web PWA</sub></td>
    <td align="center" width="140"><h2>5</h2><sub>dịch vụ Docker</sub></td>
    <td align="center" width="140"><h2>19</h2><sub>nhân viên demo</sub></td>
  </tr>
</table>

<br/>

<table>
  <tr>
    <td width="50%">

**📦 Sản phẩm** — NHỊP QUÁN
**🗃 Repository** — [KanTrun/Crew-Operations](https://github.com/KanTrun/Crew-Operations)
**🏆 Cuộc thi** — Xây dựng Hệ điều hành Doanh nghiệp số AI · Khoa CNTT HUTECH · 2026

</td>
    <td width="50%">

**📄 Hồ sơ** — [`NHIP-QUAN-HO-SO-TONG-THE .md`](./NHIP-QUAN-HO-SO-TONG-THE%20.md)
**📊 Kết quả đo §18.2** — [`docs/ket-qua-tong-hop.md`](./docs/ket-qua-tong-hop.md)
**⬇️ Clone** — `git clone https://github.com/KanTrun/Crew-Operations.git`

</td>
  </tr>
</table>

> [!NOTE]
> **Tên repo vs tên sản phẩm:** GitHub là **Crew-Operations**; phần mềm và UI vẫn là **NHỊP QUÁN**. Tên thư mục clone trên máy (có thể có dấu tiếng Việt) **không** bắt buộc trùng tên repo.

---

## 🧭 Mục lục

| | | |
|:--|:--|:--|
| 1. [📖 Giới thiệu](#gioi-thieu) | 6. [🔑 Tài khoản demo](#tai-khoan-demo) | 11. [🤖 Agents Lô 1](#agents) |
| 2. [🗂 Cấu trúc thư mục](#cau-truc) | 7. [🔧 Biến môi trường](#bien-moi-truong) | 12. [🧠 Thư viện Kỹ năng](#skills) |
| 3. [🧰 Yêu cầu môi trường](#yeu-cau) | 8. [🛠 Makefile](#makefile) | 13. [🧪 Kiểm thử & đánh giá](#kiem-thu) |
| 4. [🚀 Cài đặt](#cai-dat) | 9. [🔌 API Reference](#api-reference) | 14. [🌿 GitHub — nhánh & quy trình](#github) |
| 5. [▶️ Hướng dẫn chạy](#huong-dan-chay) | 10. [📦 Packages Python](#packages) | 15. [📚 Tài liệu](#tai-lieu) |

---

<a id="gioi-thieu"></a>
## 📖 Giới thiệu

NHỊP QUÁN là monorepo gồm **lõi tất định** (deterministic core) và **21 agent LLM** phục vụ quản lý quán cà phê qua web PWA + kênh tin (Telegram / Zalo / Facebook Page).

### ✨ Triết lý cốt lõi

<table>
  <tr>
    <td width="25%" valign="top">

#### 🧮 Lõi không dùng LLM
Xếp ca bằng **CP-SAT** (Google OR-Tools), cổng kiểm duyệt fail-closed, orchestration tất định.

</td>
    <td width="25%" valign="top">

#### ✅ Người duyệt có tiếng nói cuối
Agent **chỉ trích xuất và đề xuất**. Mọi thay đổi lịch và hiệu lực ca đi qua quản lý / chủ quán.

</td>
    <td width="25%" valign="top">

#### 📓 Cẩm nang sống
Lỗi lặp lại **≥ 3 lần** tự sinh đề xuất luật, qua **8 bước** từ tìm mẫu đến gỡ luật.

</td>
    <td width="25%" valign="top">

#### 🛡 Fail-closed
Khi LLM lỗi hoặc không chắc chắn, hệ thống **từ chối** thay vì bịa dữ liệu.

</td>
  </tr>
</table>

### 🏗 Kiến trúc tổng thể

```mermaid
flowchart TB
    APR["👤 <b>Người phê duyệt</b><br/>lan · hung"]

    subgraph ORCH["⚙️ Điều phối tất định — ghi store duy nhất (SQLite / Postgres)"]
        direction LR
        subgraph AG["🤖 Agents Lô 1"]
            A1["AG-TKB · AG-MSG<br/>AG-COPILOT · ..."]
        end
        subgraph XP["💡 Giải thích & dự đoán"]
            A2["EXPLAIN · BRIEF · SOP"]
        end
        subgraph RU["📓 Cẩm nang"]
            A3["AG-RULE"]
        end
        subgraph CORE["🧮 Lõi tất định"]
            A4["solver · gates<br/>opsengine · playbook"]
        end
    end

    AG --> APR
    XP --> APR
    RU --> APR
    CORE --> APR

    classDef core fill:#6F4E37,stroke:#3E2723,color:#fff
    classDef agent fill:#C68B59,stroke:#6F4E37,color:#fff
    class A4 core
    class A1,A2,A3 agent
```

### 🔄 Luồng nghiệp vụ chính

```mermaid
flowchart LR
    NV["📱 NV gửi tin<br/>Telegram · Zalo · FB"] --> MSG["🏷 AG-MSG<br/>phân loại ý định"]
    MSG --> INBOX["📥 Hộp thư<br/>ràng buộc"]
    INBOX -->|"quản lý duyệt"| SOLVER["🧮 CP-SAT<br/>C01–C06 + soft<br/>+ công bằng 4 trục"]
    SOLVER --> LICH["📅 Lịch tuần"]
    LICH --> CA["✅ Trong ca<br/>điểm danh · phiếu<br/>việc treo · bàn giao"]
    CA -->|"lỗi lặp ≥ 3 lần"| CN["📓 Cẩm nang<br/>8 bước"]
    CN -->|"apply_luat"| SOLVER

    style SOLVER fill:#6F4E37,stroke:#3E2723,color:#fff
    style CN fill:#C68B59,stroke:#6F4E37,color:#fff
```

<details>
<summary><b>📋 Xem chi tiết 7 bước của luồng nghiệp vụ</b></summary>

<br/>

1. NV gửi tin qua kênh (Telegram/Zalo/FB) → AG-MSG phân loại ý định → vào **hộp thư ràng buộc** chờ duyệt.
2. Quản lý duyệt → ràng buộc nạp vào solver → CP-SAT xếp lịch tuần (C01–C06 cứng + soft + công bằng 4 trục).
3. Lịch qua lifecycle: `nhap → dang_giai → cho_duyet → da_duyet → da_cong_bo → da_dong`.
4. Trong ca: điểm danh → phiếu checklist (mở quán/đóng quán/bàn giao) → việc treo → bàn giao.
5. Lỗi lặp lại → cẩm nang 8 bước → luật hiệu lực → bơm lại solver (`apply_luat`).
6. Hệ thống tự giải thích ("tại sao") bằng chuỗi nhân quả, phát hiện mẫu thành công để đề xuất luật tích cực, và mô phỏng kịch bản "nếu… thì…" bằng Math Layer (Digital Twin).
7. Khảo sát giá đối thủ quanh quán (SerpApi + Vision) để hỗ trợ định giá.

</details>

### 📅 Vòng đời lịch tuần

```mermaid
stateDiagram-v2
    direction LR
    [*] --> nhap
    nhap --> dang_giai: chạy solver
    dang_giai --> cho_duyet
    cho_duyet --> da_duyet: quản lý duyệt
    da_duyet --> da_cong_bo: công bố
    da_cong_bo --> da_dong: chủ quán chốt
    da_dong --> [*]
```

### 📓 Cẩm nang 8 bước

```mermaid
flowchart LR
    S1["1️⃣ Tìm mẫu"] --> S2["2️⃣ Đề xuất"] --> S3["3️⃣ Kiểm chứng"] --> S4["4️⃣ Tập sự"] --> S5["5️⃣ Chốt"] --> S6["6️⃣ Hiệu lực"] --> S7["7️⃣ Áp dụng"] --> S8["8️⃣ Gỡ"]
```

---

<a id="cau-truc"></a>
## 🗂 Cấu trúc thư mục

```text
Crew-Operations/
├── apps/
│   ├── api/                    # FastAPI service (ca_api)
│   │   ├── src/ca_api/
│   │   │   ├── interfaces/http/   # 17+ router module — mọi endpoint REST/WS
│   │   │   │                      #   sprint3, sprint45, channels, copilot, copilot_voice,
│   │   │   │                      #   pos, meeting, ops_explain, ops_predict, trends,
│   │   │   │                      #   pricing_radar, serpapi_system, mail, ai_learning,
│   │   │   │                      #   chat, reservations, skills
│   │   │   ├── services/          # chat_ws, fb_moderation, đặt bàn
│   │   │   ├── orchestration/     # Clock, StateMachine, IdempotencyStore
│   │   │   ├── ai_learning/       # rollout luật AI, bảo vệ dữ liệu
│   │   │   ├── domain/            # entities, policies
│   │   │   ├── persist.py         # SQLite/Postgres store + auth
│   │   │   └── worker.py          # worker nền: brief sáng, solver tuần, nhắc phiếu
│   │   ├── alembic/               # migration Postgres
│   │   └── tests/
│   └── web/                    # Next.js 15 PWA (ca-web)
│       ├── src/app/               # ~36 route: roster, inbox, copilot, chat, page-quán…
│       ├── src/lib/               # API client, session
│       └── e2e/                   # Playwright
├── packages/
│   ├── contracts/              # ca_contracts — Pydantic schema chia sẻ (ADR-013)
│   ├── solver/                # ca_solver — CP-SAT + C01–C06 + fairness 4 trục
│   ├── gates/                 # ca_gates — VF-SCHEMA/TRACE/CONF/RULE/SCOPE/STALE/NUM
│   ├── opsengine/             # ca_ops — phiếu YAML, việc treo, escalate
│   ├── playbook/              # ca_playbook — cẩm nang 8 bước, distiller SOP→Skill
│   └── agents/                # ca_agents — 21 agent, router LLM, messaging ports
├── config/
│   └── tham-so-lao-dong.yaml  # tham số lao động (trần giờ, khoảng nghỉ)
├── data/
│   ├── seed/                  # sample.json — 21 ca mẫu, lịch sử 8 tuần
│   ├── fixtures/ · golden/     # dữ liệu kiểm thử tất định
│   ├── uploads/               # ảnh TKB, minh chứng upload
│   └── out/                   # lich_tuan.json, cam_nang.json (runtime)
├── infra/
│   ├── docker/                # compose.yml — postgres·redis·api·worker·web
│   ├── templates/             # phiếu YAML: mo_quan, dong_quan, ban_giao_ca
│   ├── aws/ · oracle/         # runbook triển khai cloud
├── skills/                     # 14 kỹ năng (13 skill Repo-To-Skill + 1 router) đã kiểm định
├── scripts/                    # demo, eval, seed, docker_stack.py, do_metrics.py…
├── plans/                      # AgentKit plans, journals, reports
└── docs/                       # runbook, ADR, hướng dẫn, research
```

| Thành phần | Đường dẫn | Vai trò |
|:-----------|:----------|:--------|
| 📜 Hợp đồng dữ liệu | `packages/contracts` | Pydantic models + JSON Schema + TypeScript types |
| 🧮 Solver | `packages/solver` | CP-SAT, ràng buộc cứng C01–C06, soft, công bằng |
| 🚧 Cổng VF | `packages/gates` | VF-TRACE, VF-CONF, VF-SCHEMA, VF-RULE, VF-SCOPE, VF-STALE |
| ✅ Ops | `packages/opsengine` | Phiếu checklist, việc treo, nhắc quá hạn |
| 📓 Playbook | `packages/playbook` | Cẩm nang 8 bước, ghi nhận sửa, distiller |
| 🤖 Agents | `packages/agents` | AG-TKB, AG-MSG, AG-COPILOT, AG-PRICING, AG-PREDICT, AG-EXPLAIN, AG-TWIN…, router LLM, messaging |
| ⚡ API | `apps/api` | FastAPI · SQLite/Postgres · worker nền |
| 🖥 Web | `apps/web` | Next.js PWA (quản lý, NV, inbox, page quán) |
| 🐳 Infra | `infra/docker` | Compose 5 dịch vụ |
| 🧠 Skills | `skills/` | 14 kỹ năng vận hành đã kiểm định (13 skill + 1 router) |

---

<a id="yeu-cau"></a>
## 🧰 Yêu cầu môi trường

| Công cụ | Phiên bản | Ghi chú |
|:--------|:----------|:--------|
| ![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white) | ≥ 3.12 | Khuyến nghị dùng `uv` |
| ![Node](https://img.shields.io/badge/Node.js-339933?logo=nodedotjs&logoColor=white) | ≥ 20 | Cho web |
| ![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white) | Docker Desktop | Khuyến nghị demo toàn tuyến |
| 📄 `.env` | ở root | Copy từ `.env.example` — **không commit** |

---

<a id="cai-dat"></a>
## 🚀 Cài đặt

### 🐳 Cách 1 — Docker toàn tuyến (khuyến nghị)

```bash
git clone https://github.com/KanTrun/Crew-Operations.git
cd Crew-Operations          # hoặc thư mục bạn đặt tên
cp .env.example .env        # điền key LLM / kênh tin nếu cần live
make docker-up              # = python scripts/docker_stack.py up
make docker-smoke           # kiểm toàn tuyến backend
```

> [!WARNING]
> **Windows:** BuildKit có thể lỗi khi đường dẫn clone có ký tự non-ASCII. Clone/junction sang đường dẫn ASCII, ví dụ `mklink /J C:\nhipquan D:\CA-CÔNG-BẰNG` — chi tiết [`docs/runbook-demo.md`](./docs/runbook-demo.md).

### 💻 Cách 2 — Local (không Docker)

```bash
# 1. Cài Python packages (editable) + npm web
make setup

# 2. Seed dữ liệu demo (19 nhân viên, idempotent)
python scripts/seed_19_staff.py
# hoặc seed đầy đủ: make seed-demo

# 3. Chạy API
cd apps/api
uv run uvicorn ca_api.interfaces.http.main:app --reload --port 8000

# 4. Chạy worker nền (terminal khác)
python -m ca_api.worker

# 5. Chạy web (terminal khác)
cd apps/web && npm run dev
```

<details>
<summary><b>🗄 Migration Postgres (Alembic)</b></summary>

<br/>

```bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/nhip_quan
cd apps/api
uv run alembic -c alembic/alembic.ini upgrade head      # áp mọi migration
uv run alembic -c alembic/alembic.ini downgrade -1       # lùi 1 bước
uv run alembic -c alembic/alembic.ini revision -m "mo_ta" # tạo migration mới
```

</details>

---

<a id="huong-dan-chay"></a>
## ▶️ Hướng dẫn chạy

### 🌐 Dịch vụ & URL (Docker)

| Dịch vụ | URL / cổng |
|:--------|:-----------|
| 🖥 Web PWA | http://localhost:3000 |
| ⚡ API + OpenAPI docs | http://localhost:8000/docs |
| 💚 Health | http://localhost:8000/health |
| 🐘 Postgres | `localhost:5433` (container 5432) |
| 🔴 Redis | `localhost:6379` |

Dừng: `make docker-down` · Xóa volume: `make docker-reset`

### 🔧 Chạy local từng phần

| Việc | Lệnh |
|:-----|:-----|
| API dev | `uvicorn ca_api.interfaces.http.main:app --reload --port 8000` (từ `apps/api`) |
| Worker nền | `python -m ca_api.worker` |
| Web dev | `cd apps/web && npm run dev` |
| Demo API script | `make demo-local` (`python scripts/demo_api.py`) |
| Seed 6 bề mặt vận hành | `make seed-ops` |
| Seed toàn bộ demo | `make seed-demo` |
| Reset demo Docker | `make demo-reset` |

### ⏰ Worker nền làm gì

`ca_api.worker` chạy việc định kỳ (mỗi job một khoá mốc, idempotent):

| Giờ | Job | Kết quả |
|:----|:----|:--------|
| 🌅 06:00 | `brief_sang` | Sinh bản tin sáng (ca hôm nay, treo, tồn cảnh báo) → kv `brief_hom_nay` |
| 🌙 22:00 Chủ nhật | `solver_tuan` | CP-SAT tuần sau → kv `worker_de_xuat_lich` **chờ quản lý duyệt** (worker không tự công bố) |
| 🌃 23:00 | `tong_ket_ngay` | Gom tiêu thụ/hao phí trong ngày |

<details>
<summary><b>📌 Chi tiết hành vi của worker & ca trống</b></summary>

<br/>

- Nhắc phiếu quá hạn 2 cấp (nhắc NV → báo chủ quán), mỗi cặp (phiếu, cấp) chỉ nhắn một lần.
- Ca thiếu sau CP-SAT được lưu thành `open_shift`; nhân viên nhận qua `POST /api/v1/open-shifts/claim` với xác nhận availability đúng tuần. Claim đầu tiên được bảo vệ bằng transaction.
- Mỗi lần chạy lịch tạo một `schedule_run` có version, snapshot input, fingerprint và idempotency key; chạy lại cùng key với input khác sẽ bị từ chối.
- Quản lý xử lý ca thiếu bằng `POST /api/v1/lich/resolve-gaps`; hệ thống revalidate ràng buộc, chạy lại CP-SAT và lưu assignment authoritative trước khi chuyển sang chờ duyệt.
- Chỉ run authoritative còn mới và đầy đủ mới được chuyển `da_duyet` hoặc `da_cong_bo`; khi công bố, thông báo được gửi tới nhân viên của đúng tuần.
- `GET /api/v1/chat/scheduler` trả về hội thoại riêng duy nhất giữa nhân viên và `ai_scheduler`.
- Worker đánh dấu và báo quản lý các open shift quá hạn; SLA mặc định 120 phút, cấu hình bằng `OPEN_SHIFT_SLA_MINUTES`.

</details>

---

<a id="tai-khoan-demo"></a>
## 🔑 Tài khoản demo

> [!IMPORTANT]
> Mật khẩu mọi tài khoản: **`nhipquan`**. Danh sách đầy đủ 19 NV: [`docs/runbook-demo.md`](./docs/runbook-demo.md).

| Tài khoản | Vai trò | Dùng để |
|:----------|:--------|:--------|
| 👩‍💼 `lan` | `quan_ly` | Người phê duyệt chính — inbox, duyệt đổi ca, xếp lịch |
| 👑 `hung` | `chu_quan` | Nâng/hạ vai, audit, chốt luật cẩm nang |
| ☕ `minh` | `nhan_vien` | Ca sáng, bind Telegram demo |
| 📚 `chi` | `nhan_vien` | TKB xung đột T2, bind Zalo demo |
| 🌱 `rosa` | `nhan_vien` | Mới đăng ký — demo onboarding |

Đăng nhập lấy token:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"lan","password":"nhipquan"}'
# → {"token":"...","role":"quan_ly","nv_id":"nv_01",...}
# Dùng: Authorization: Bearer <token>
```

---

<a id="bien-moi-truong"></a>
## 🔧 Biến môi trường

<details open>
<summary><b>⚙️ Lõi hệ thống & LLM</b></summary>

<br/>

| Biến | Mục đích |
|:-----|:---------|
| `CA_AGENT_MODE` | `replay` (mặc định, CI) hoặc `live` (LLM thật) |
| `GROQ_API_KEY` / `GEMINI_API_KEY` / `OPENROUTER_API_KEY` / `BAI_API_KEY` | Router LLM khi live |
| `GROQ_MODEL` / `GEMINI_MODEL` / `OPENROUTER_MODEL` / `BAI_MODEL` | Chọn model từng provider |
| `DATABASE_URL` | Postgres (mặc định SQLite `data/quan.db`) |
| `REDIS_URL` | Redis Pub/Sub realtime |
| `NHIPQUAN_CORS_ORIGINS` | Danh sách origin cách nhau dấu phẩy |
| `NHIPQUAN_LOI_GIAI_SEED` | Thêm 21 NV mẫu vào pool xếp lịch (chỉ dev/demo) |
| `OPEN_SHIFT_SLA_MINUTES` | SLA mặc định trước khi escalate open shift, mặc định `120` |

</details>

<details open>
<summary><b>💬 Kênh tin & Page</b></summary>

<br/>

| Biến | Mục đích |
|:-----|:---------|
| `NHIPQUAN_MSG_BACKEND` | `telegram` · `zalo` · `console` |
| `NHIPQUAN_ZALO_ENABLED` / `NHIPQUAN_ZALO_OA_ACCESS_TOKEN` | Zalo OA (kênh ưu tiên VN) |
| `NHIPQUAN_TELEGRAM_BOT_TOKEN` / `NHIPQUAN_TELEGRAM_WEBHOOK_SECRET` | Telegram bot |
| `NHIPQUAN_FB_PAGE_TOKEN` / `NHIPQUAN_FB_PAGE_ID` | Facebook Page |
| `NHIPQUAN_PAGE_MODE` | `live` khi nối Meta, `replay`/`disconnected` |
| `NHIPQUAN_FB_WEBHOOK_VERIFY` | Verify token webhook Messenger |
| `NHIPQUAN_SMTP_*` | Gửi Gmail qua SMTP (App Password) |
| `NHIPQUAN_ALLOW_MSG_REPLAY` | Chỉ bật khi pytest kênh tin |

</details>

<details open>
<summary><b>🔍 Khảo sát giá & Copilot Voice</b></summary>

<br/>

| Biến | Mục đích |
|:-----|:---------|
| `SERPAPI_API_KEY` | Khóa SerpApi (**bắt buộc** cho AG-PRICING) |
| `SERPAPI_ENABLED` | Bật/tắt SerpApi (`true`/`false`) |
| `SERPAPI_MONTHLY_LIMIT` | Giới hạn request SerpApi mỗi tháng (ví dụ `100`) |
| `VOICE_IDLE_TIMEOUT_SECONDS` | Ngắt phiên Copilot Voice khi im lặng quá lâu (ví dụ `60`) |
| `VOICE_SESSION_MAX_SECONDS` | Thời lượng tối đa một phiên Copilot Voice (ví dụ `300`) |

```bash
# Khảo sát giá thị trường (AG-PRICING)
SERPAPI_API_KEY=
SERPAPI_ENABLED=true
SERPAPI_MONTHLY_LIMIT=100

# Copilot Voice (Gemini Live)
VOICE_IDLE_TIMEOUT_SECONDS=60
VOICE_SESSION_MAX_SECONDS=300
```

</details>

📎 **Runbook kết nối:** [Telegram](./docs/runbooks/telegram-bot-connect.md) · [Zalo](./docs/runbooks/zalo-oa-connect.md) · [Facebook Page](./docs/runbooks/facebook-page-connect.md)

---

<a id="makefile"></a>
## 🛠 Makefile

| Lệnh | Mô tả |
|:-----|:------|
| `make setup` | Cài Python editable + npm web |
| `make test` / `test-unit` | Pytest toàn monorepo (`CA_AGENT_MODE=replay`) |
| `make lint` | Ruff + `tsc --noEmit` web |
| `make bench` | Solver tuần + `verify_hard` |
| `make eval` | AG-TKB, AG-MSG, nhóm A §18.2 |
| `make ab` / `make replay PHIEN=<key>` | Báo cáo A/B / replay orchestration |
| `make metrics` | 7 con số §18.2 trên fixture ADR-012 |
| `make seed` / `seed-ops` / `seed-demo` | Sinh fixture / 6 bề mặt / toàn bộ demo |
| `make docker-up/down/ps/logs/smoke/reset` | Stack Docker qua `scripts/docker_stack.py` |
| `make demo` / `demo-reset` | Demo API / reset Docker |
| `make test-fb` / `test-fb-post` | Kiểm tra / đăng Facebook Page |

> [!CAUTION]
> Gọi Docker qua `scripts/docker_stack.py` (wrapper tắt BuildKit, ghim tên project ASCII) — **không** gọi `docker compose` trực tiếp.

---

<a id="api-reference"></a>
## 🔌 API Reference

**Base URL:** `http://localhost:8000` · **OpenAPI:** [`/docs`](http://localhost:8000/docs) · **Auth:** `Authorization: Bearer <token>` từ `/api/v1/auth/login`

**Chú giải quyền:**

| 🟢 | 🔵 | 🟡 | 🔴 |
|:--:|:--:|:--:|:--:|
| Công khai | Mọi vai đã đăng nhập | `quan_ly` + `chu_quan` | `chu_quan` |

> 💡 Bấm vào từng nhóm bên dưới để mở rộng.

<details>
<summary><b>🩺 Health & Auth</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/health` | 🟢 | Trạng thái service + `minimal_data_mode` |
| POST | `/api/v1/auth/register` | 🟢 | Đăng ký NV mới (luôn vai `nhan_vien`), trả token luôn. Body: `username`, `password`, `display_name` |
| POST | `/api/v1/auth/login` | 🟢 | Đăng nhập → `token`, `role`, `nv_id`, `store_id` |
| GET | `/api/v1/me` | 🔵 | Thông tin phiên hiện tại |
| GET | `/api/v1/contracts` | 🟢 | 5 hợp đồng dữ liệu mẫu (ADR-012) |

</details>

<details>
<summary><b>📅 Lịch tuần (roster)</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/api/v1/lich-tuan?tuan=2026-W36&so_tuan=1..4` | 🟡 | Lịch tuần hiệu lực: phân công, khung giờ, trạng thái lifecycle, solver meta |
| PATCH | `/api/v1/lich-tuan/khung-gio` | 🟡 | Sửa template giờ 3 khung (sáng/chiều/tối). Body: `{sang:{bat_dau,ket_thuc},…}` |
| POST | `/api/v1/lich-tuan/pin` | 🟡 | Ghim/bỏ ghim NV vào ca. Body: `ca_id`, `nv_id`, `pinned` |
| PATCH | `/api/v1/lich-tuan/lifecycle` | 🟡 | Chuyển trạng thái lịch; `dang_giai` chạy solver ngay rồi sang `cho_duyet`. Chỉ 🔴 đổi `tuan_iso` |
| GET | `/api/v1/lich/lifecycle` | 🔵 | Trạng thái lifecycle hiện tại |
| POST | `/api/v1/lich/lifecycle` | 🟡 | Chuyển trạng thái theo ma trận hợp lệ; `da_dong`/mở lại cần 🔴 + lý do |
| GET | `/api/v1/lich/ics` | 🔵 | Xuất lịch dạng iCalendar |
| GET | `/api/v1/lich/xlsx` | 🔵 | Xuất lịch dạng Excel |
| GET | `/api/v1/lich/pdf` | 🔵 | Xuất lịch dạng PDF |
| GET | `/api/v1/ops/pickers` | 🔵 | NV + ca cho dropdown |

</details>

<details>
<summary><b>🕳 Ca trống (Open Shifts)</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| POST | `/api/v1/open-shifts` | 🟡 | Tạo ca trống |
| GET | `/api/v1/open-shifts` | 🔵 | Danh sách ca trống |
| POST | `/api/v1/open-shifts/claim` | 🔵 | Nhận ca (transaction-safe — claim đầu tiên thắng) |

</details>

<details>
<summary><b>✅ Phiếu & điểm danh (opsengine)</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| POST | `/api/v1/diem-danh` | 🔵 | Điểm danh NV trong ca |
| GET | `/api/v1/phieu/mau` | 🟢 | Liệt kê mọi mẫu phiếu trong `infra/templates/` |
| POST | `/api/v1/phieu/start` | 🔵 | Bắt đầu phiếu (yêu cầu đã điểm danh). Body: `mau`, `ca_id` |
| GET | `/api/v1/phieu/{phieu_id}` | chủ phiếu/🟡 | Trạng thái phiếu + tín hiệu escalate |
| POST | `/api/v1/phieu/{phieu_id}/buoc` | chủ phiếu/🟡 | Hoàn thành bước theo đúng thứ tự. Body: `ma`, `gia_tri` |
| POST | `/api/v1/phieu/{phieu_id}/minh-chung` | chủ phiếu/🟡 | Nộp ảnh minh chứng (data URL ≤ 400KB) |
| POST | `/api/v1/phieu/{phieu_id}/treo` | chủ phiếu/🟡 | Treo việc từ phiếu. Body: `noi_dung` |
| GET | `/api/v1/viec-treo` | 🔵 | Danh sách việc treo |
| PATCH | `/api/v1/viec-treo/{treo_id}` | 🟡 | Đóng việc treo (`trang_thai: xong`) |
| POST | `/api/v1/orc/dispatch` | 🟡 | Dispatch N task song song, idempotent theo `key` |

</details>

<details>
<summary><b>📥 Hộp thư & ràng buộc</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/api/v1/inbox` | 🟡 | Hộp thư tin nhắn nội bộ |
| POST | `/api/v1/inbox` | 🟡 | Thêm mục hộp thư. Body: `tom_tat`, `agent` |
| POST | `/api/v1/msg/classify` | 🔵 | AG-MSG phân loại tin. Body: `text`, `backend` |
| GET | `/api/v1/inbox/rang-buoc` | 🟡 | Hộp thư ràng buộc ca (kèm gợi ý đổi ca) |
| POST | `/api/v1/inbox/rang-buoc/{item_id}` | 🟡 | Duyệt/từ chối; duyệt đổi ca cần `ca_id`+`doi_tac_nv_id` |
| GET | `/api/v1/inbox/candidates/{item_id}` | 🟡 | Xếp hạng ứng viên đổi ca |
| POST | `/api/v1/inbox/rang-buoc/{item_id}/smart-approve` | 🟡 | Duyệt 1-chạm với ứng viên AI đề xuất |

</details>

<details>
<summary><b>🖼 TKB (thời khoá biểu)</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| POST | `/api/v1/tkb/extract` | 🔵 | AG-TKB trích TKB từ ảnh. Body: `image_path_or_id` |
| POST | `/api/v1/tkb/upload` | 🔵 | Upload ảnh TKB (≤ 8MB) hoặc dùng `fixture_id` → extract |
| POST | `/api/v1/tkb/confirm` | 🔵 | Xác nhận khoảng bận theo `tuan_iso`, gắn vào NV (NV chỉ gắn cho mình) |

</details>

<details>
<summary><b>⚖️ Công bằng & hôm nay</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/api/v1/cong-bang` | 🔵 | Số dư công bằng 4 trục (cuối tuần/đêm/giờ/short); NV chỉ thấy mình |
| GET | `/api/v1/cong-bang/bao-cao` | 🔵 | Báo cáo text/plain, không xếp hạng tên |
| GET | `/api/v1/hom-nay` | 🔵 | Tổng quan hôm nay: lịch, treo, inbox chờ, tồn, `viec_cho_toi` |
| GET | `/api/v1/tieu-thu` | 🔵 | Sổ tiêu thụ nguyên liệu |
| POST | `/api/v1/tieu-thu` | 🟡 | Ghi tiêu thụ. Body: `hang`, `so_luong`, `don_vi` |
| POST | `/api/v1/waste` | 🔵 | Ghi chú hao phí. Body: `thu`, `ghi_chu` |
| GET | `/api/v1/waste` | 🔵 | Cụm hao phí (AG-WASTE) + ghi chú gốc |

</details>

<details>
<summary><b>📓 Bàn giao & cẩm nang</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/api/v1/handover` | 🔵 | Lịch sử bàn giao |
| POST | `/api/v1/handover` | 🔵 | Trích bàn giao (AG-HANDOVER) + VF-NUM + phát hiện mâu thuẫn |
| GET | `/api/v1/cam-nang` | 🔵 | Luật cẩm nang + mẫu + pipeline snapshot |
| POST | `/api/v1/cam-nang/chay-8-buoc` | 🟡 | Chạy pipeline 8 bước từ lần sửa thật (≥ 3 mẫu) |
| POST | `/api/v1/cam-nang/duyet` | chốt cần 🔴 | Duyệt/từ chối luật `cho_chu_quan`. Body: `id`, `ok` |
| POST | `/api/v1/cam-nang/go` | 🔴 | Gỡ luật hiệu lực. Body: `id` |
| POST | `/api/v1/sop` | 🔵 | Hỏi đáp SOP (AG-SOP). Body: `question`, `ngu_canh` |
| GET | `/api/v1/sop/golden` | 🔵 | Chạy bộ câu hỏi golden — mọi câu có nguồn hoặc `chua_co` |

</details>

<details>
<summary><b>💡 Tự giải thích (Self-Explaining System) — AG-EXPLAIN</b></summary>

<br/>

Prefix: `/api/v1/ops/explain`. Agent: **AG-EXPLAIN** — dịch mã lý do của solver thành câu tiếng Việt có căn cứ (grounded).

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| POST | `/explain` | 🔵 | Chuỗi nhân quả cho câu hỏi "tại sao" |
| GET | `/chains` | 🔵 | Danh sách chuỗi nhân quả |
| POST | `/episodes` | 🔵 | Ghi episode |
| POST | `/reflect` | 🔵 | Reflection |

</details>

<details>
<summary><b>🔮 Playbook dự đoán & Digital Twin — AG-PREDICT · AG-TWIN</b></summary>

<br/>

Prefix: `/api/v1/ops`. Agents: **AG-PREDICT** (phát hiện mẫu thành công → đề xuất luật tích cực) và **AG-TWIN** (mô phỏng "nếu… thì…" bằng Math Layer).

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/predict/suggestions` | 🔵 | Đề xuất luật tích cực |
| POST | `/predict/run` | 🟡 | Trigger phát hiện mẫu |
| POST | `/predict/{rule_id}/approve` | 🟡 | Duyệt luật tích cực |
| POST | `/twin/simulate` | 🟡 | Mô phỏng kịch bản |
| GET | `/twin/scenarios` | 🔵 | Danh sách kịch bản |
| POST | `/twin/virtual-staff` | 🟡 | Mô phỏng nhân sự ảo |

</details>

<details>
<summary><b>💰 Khảo sát giá thị trường — AG-PRICING</b></summary>

<br/>

Prefix: `/api/v1/market`. Agent: **AG-PRICING** (SerpApi + Vision). Job chạy bất đồng bộ; giá OCR không chắc chắn chuyển `NEEDS_REVIEW` chờ người xác nhận.

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| POST | `/catchment-survey` | 🟡 | Tạo job khảo sát (trả `202` + `job_id`) |
| GET | `/catchment-survey/{job_id}` | 🔵 | Trạng thái job |
| GET | `/catchment-survey/{job_id}/result` | 🔵 | Kết quả khảo sát |
| POST | `/catchment-survey/{job_id}/review` | 🟡 | Xác nhận giá OCR (`NEEDS_REVIEW`) |
| GET | `/catchment-survey-metrics` | 🔵 | Chi phí Vision & nguồn dữ liệu |
| GET | `/catchment-survey-dashboard` | 🔵 | Dashboard tổng hợp |
| GET | `/serpapi/quota` | 🔵 | Hạn ngạch SerpApi còn lại |

</details>

<details>
<summary><b>🔁 QR & đổi ca</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| POST | `/api/v1/qr` | 🟡 | Phát mã QR điểm danh một lần. Body: `nv_id`, `ca_id` |
| POST | `/api/v1/qr/{token}` | 🔵 | Dùng mã QR (chủ NV, một lần) |
| POST | `/api/v1/cho-doi-ca` | người tham gia | Mở phiếu đổi ca 3 người. Body: `a`, `b`, `c`, `ca_id` |
| GET | `/api/v1/cho-doi-ca` | 🔵 | Danh sách phiếu đổi ca |
| POST | `/api/v1/cho-doi-ca/{swap_id}/dong-y` | người tham gia | Đồng ý tham gia đổi ca |
| POST | `/api/v1/cho-doi-ca/{swap_id}/tu-choi` | người tham gia | Từ chối đổi ca |

</details>

<details>
<summary><b>🧋 Menu & quầy POS</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/api/v1/menu` | 🔵 | Menu đang bán |
| GET | `/api/v1/menu/quan-tri` | 🟡 | Menu toàn bộ (kèm ẩn) |
| PUT | `/api/v1/menu/{mon_id}` | 🟡 | Sửa món (tên, giá, ẩn, BOM) |
| GET | `/api/v1/menu/{mon_id}/anh` | 🟢 | Ảnh món |
| POST | `/api/v1/menu/{mon_id}/anh` | 🟡 | Upload ảnh món |
| GET | `/api/v1/quay/don` | 🔵 | Đơn quầy nội bộ |
| POST | `/api/v1/quay/don` | 🔵 (đã điểm danh) | Tạo đơn theo menu. Body: `dong:[{mon_id,so_luong}]` |
| POST | `/api/v1/quay/don/{don_id}/chuyen` | chủ đơn/🟡 | Chuyển trạng thái (`cho_pha→dang_pha→xong/huy`) |
| POST | `/api/v1/quay/don/{don_id}/chinh` | chủ đơn/🟡 | Sửa số lượng dòng |
| GET | `/api/v1/quay/bao-cao` | 🔵 | Báo cáo quầy |

</details>

<details>
<summary><b>👥 Người dùng & vai trò</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/api/v1/nguoi` | 🔵 | Danh sách người dùng |
| POST | `/api/v1/nguoi/{username}/nang-vai` | 🔴 | Nâng vai (VD `nhan_vien→quan_ly`) |
| POST | `/api/v1/nguoi/{username}/ha-vai` | 🔴 | Hạ vai |

</details>

<details>
<summary><b>💬 Chat nội bộ (realtime)</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| WS | `/ws/chat` | 🔵 (auth trong 5s) | WebSocket chat: `{"event":"auth","token":…}` → `auth:ack` |
| GET | `/api/v1/chat/conversations` | 🔵 | Hội thoại của tôi |
| POST | `/api/v1/chat/conversations` | 🔵 | Tạo hội thoại |
| GET | `/api/v1/chat/conversations/{conv_id}` | thành viên | Chi tiết hội thoại |
| GET | `/api/v1/chat/conversations/{conv_id}/messages` | thành viên | Tin nhắn (phân trang) |
| POST | `/api/v1/chat/conversations/{conv_id}/messages` | thành viên | Gửi tin nhắn |
| POST | `/api/v1/chat/messages/{message_id}/pin` | thành viên | Ghim/bỏ ghim |
| PATCH | `/api/v1/chat/messages/{message_id}` | người gửi | Sửa tin nhắn |
| DELETE | `/api/v1/chat/messages/{message_id}` | người gửi | Xóa tin nhắn |
| POST | `/api/v1/chat/messages/{message_id}/treo` | thành viên | Chuyển tin nhắn thành việc treo |
| POST | `/api/v1/chat/messages/{message_id}/reactions` | thành viên | Thả reaction |
| POST | `/api/v1/chat/conversations/{conv_id}/read` | thành viên | Đánh dấu đã đọc |
| POST | `/api/v1/chat/conversations/{conv_id}/mute` | thành viên | Tắt/bật thông báo |
| GET | `/api/v1/chat/search?q=` | 🔵 | Tìm tin nhắn |
| GET | `/api/v1/chat/online` | 🔵 | NV đang online |
| POST | `/api/v1/chat/upload` | 🔵 | Upload file đính kèm |
| GET | `/api/v1/chat/uploads/{filename}` | 🔵 | Tải file đính kèm |
| GET | `/api/v1/chat/scheduler` | 🔵 | Hội thoại riêng giữa NV và `ai_scheduler` |
| POST | `/api/v1/chat/availability/{id}/confirm` | 🔵 | Xác nhận khả dụng |
| POST | `/api/v1/chat/availability/{id}/correct` | 🔵 | Sửa khả dụng |

</details>

<details>
<summary><b>🧑‍✈️ AG-COPILOT (trợ lý hội thoại)</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| POST | `/api/v1/copilot/message` | 🔵 | Gửi chỉ dẫn ngôn ngữ tự nhiên → `CopilotResponse` (intent, proposal, citations) |
| POST | `/api/v1/copilot/message/stream` | 🔵 | Bản SSE: event `meta` → `delta` → `done` |
| WS | `/api/v1/copilot/voice` | 🔵 | Phiên voice với Gemini Live (giới hạn bởi `VOICE_IDLE_TIMEOUT_SECONDS`, `VOICE_SESSION_MAX_SECONDS`) |
| POST | `/api/v1/copilot/execute-action` | 🔵 | Duyệt/từ chối đề xuất 2 pha. Body: `action_id`, `decision`, `idempotency_key` |
| POST | `/api/v1/copilot/action/{action_id}/amend` | 🔵 | Sửa đề xuất trước khi duyệt (`correction_diff` theo intent) |
| GET | `/api/v1/copilot/action/{action_id}` | 🔵 | Xem đề xuất + snapshot |
| GET | `/api/v1/copilot/audit` | 🔵 | Audit trail copilot |
| GET | `/api/v1/copilot/permissions` | 🔵 | Ma trận role × intent |
| GET | `/api/v1/copilot/capabilities` | 🔵 | Danh mục năng lực theo vai |
| POST | `/api/v1/copilot/navigate` | 🔵 | Đề xuất điều hướng UI |

</details>

<details>
<summary><b>📡 Kênh tin (Telegram / Zalo)</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| POST | `/api/v1/channels/bind/issue` | 🔵 | Phát mã bind NV (nhắn `/bind <mã>` trên kênh) |
| POST | `/api/v1/channels/bind` | 🟡 | Bind thủ công. Body: `channel`, `external_user_id`, `nv_id` |
| GET | `/api/v1/channels/bind` | 🔵 | Danh sách bind (NV chỉ thấy mình) |
| GET | `/api/v1/channels/status` | 🔵 | Trạng thái nối kênh thật — không giả lập |
| POST | `/api/v1/channels/replay` | 🟡 + env | Replay inbound (chỉ CI/test, cần `NHIPQUAN_ALLOW_MSG_REPLAY=1`) |
| POST | `/api/v1/channels/telegram/webhook` | 🟢 + secret | Webhook Telegram (verify `X-Telegram-Bot-Api-Secret-Token`) |
| POST | `/api/v1/channels/zalo/webhook` | 🟢 + token | Webhook Zalo OA |

</details>

<details>
<summary><b>📘 Page quán (Facebook)</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/api/v1/page/status` | 🔵 | Trạng thái Page (mode, connected — token đã redact) |
| POST | `/api/v1/page/sync` | 🟡 | Đồng bộ threads từ Meta |
| GET | `/api/v1/page/threads` | 🔵 | Threads khách nhắn Page |
| POST | `/api/v1/page/threads/{thread_id}/reply` | 🟡 | Soạn/đăng phản hồi (qua moderation) |
| POST | `/api/v1/page/threads/{thread_id}/approve` | 🟡 | Duyệt phản hồi do AI soạn |
| GET | `/api/v1/page/fb-inbox` | 🔵 | Inbox moderation queue |
| GET | `/api/v1/page/fb-inbox/stats` | 🔵 | Thống kê moderation |
| GET | `/api/v1/page/fb-inbox/{item_id}` | 🔵 | Chi tiết một mục |
| POST | `/api/v1/page/fb-inbox/{item_id}/decide` | 🟡 | Quyết định moderation (đăng/sửa/leo thang) |
| GET/PUT | `/api/v1/page/fb-policy` | 🔵/🟡 | Chính sách moderation |
| POST | `/api/v1/page/audit/reflection` | 🟡 | Chạy reflection AI trên audit |
| GET | `/api/v1/page/audit/reflection/latest` | 🔵 | Kết quả reflection gần nhất |
| GET/POST | `/api/v1/page/drafts` | 🔵/🟡 | Danh sách / tạo bài đăng nháp |
| POST | `/api/v1/page/drafts/ai-generate` | 🟡 | AI soạn bài đăng |
| POST | `/api/v1/page/drafts/{id}` | 🟡 | Đăng bài nháp |

</details>

<details>
<summary><b>🏪 Hồ sơ quán & khuyến mãi</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET/PUT | `/api/v1/store/profile` | 🔵/🟡 | Hồ sơ quán |
| GET/PUT | `/api/v1/store/promotions` | 🔵/🟡 | Khuyến mãi |

</details>

<details>
<summary><b>🎙 Cuộc họp — AG-MEETING</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| POST | `/api/v1/meeting/transcribe` | 🔵 | Audio base64 → transcript diarization |
| POST | `/api/v1/meeting/analyze` | 🔵 | Transcript → hợp đồng `CuocHop` (AG-MEETING) |
| POST | `/api/v1/meeting/process-audio` | 🔵 | 1 bước: upload file → STT → trích xuất |
| POST | `/api/v1/meeting/apply` | 🟡 | Human-in-the-loop: áp action items → việc treo + SOP đề xuất |
| GET | `/api/v1/meetings` | 🔵 | Danh sách cuộc họp đã lưu |

</details>

<details>
<summary><b>✉️ Mail</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/api/v1/me/profile` | 🔵 | Hồ sơ cá nhân |
| PATCH | `/api/v1/me/profile/email` | 🔵 | Cập nhật email cá nhân |
| GET | `/api/v1/users/emails` | 🔵 | Email đồng nghiệp (không PII khác) |
| POST | `/api/v1/mail/send` | 🔵 | Gửi mail (AG-MAILWRITER + quality gate + idempotent) |

</details>

<details>
<summary><b>🪑 Đặt bàn</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/api/v1/reservations?date=&status=` | 🔵 | Danh sách đặt bàn |
| GET | `/api/v1/reservations/tables` | 🔵 | Sơ đồ bàn |
| GET | `/api/v1/reservations/{res_id}` | 🔵 | Chi tiết đơn |
| POST | `/api/v1/reservations/{res_id}/check-in` | 🔵 | Khách nhận bàn (`seated`) |
| POST | `/api/v1/reservations/{res_id}/no-show` | 🔵 | Khách không đến |
| POST | `/api/v1/reservations/{res_id}/complete` | 🔵 | Hoàn tất, giải phóng bàn |
| POST | `/api/v1/reservations/{res_id}/cancel` | 🔵 | Hủy đặt bàn |

</details>

<details>
<summary><b>🧠 Skills (thư viện kỹ năng)</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/skills` | 🟢 | Danh mục 14 kỹ năng + SHA256 |
| GET | `/skills/{skill_id}` | 🟢 | Nội dung SKILL.md + scripts + references |
| POST | `/skills/{skill_id}/verify` | 🟢 | Chạy smoke test kỹ năng ngay |
| POST | `/skills/distill-sop` | 🟡 | Chưng cất SOP → Skill (Hybrid mode) |

</details>

<details>
<summary><b>🎓 AI Learning (học từ phản hồi)</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/api/v1/ai/rules/proposals` | 🔵 | Đề xuất luật AI chờ duyệt |
| GET | `/api/v1/ai/generations` | 🔵 | Lịch sử sinh nội dung AI |
| POST | `/api/v1/ai/feedback` | 🔵 | Ghi phản hồi người dùng (đã sửa/chưa) |
| GET | `/api/v1/ai/evaluations/summary` | 🔵 | Tổng hợp đánh giá |
| GET | `/api/v1/ai/operations/status` | 🔵 | Trạng thái vận hành AI |
| POST | `/api/v1/ai/operations/circuit-breaker` | 🟡 | Bật/tắt circuit breaker |
| GET | `/api/v1/ai/retention/dry-run` | 🔴 | Xem trước dữ liệu sẽ bị xóa theo retention |
| POST | `/api/v1/ai/reflection/gmail/run` | 🟡 | Reflection trên mail đã gửi |
| POST | `/api/v1/ai/reflection/facebook/run` | 🟡 | Reflection trên phản hồi Page |
| POST | `/api/v1/ai/rules/proposals/{id}/approve` | 🟡 | Duyệt đề xuất luật |
| POST | `/api/v1/ai/rules/proposals/{id}/activate` | 🟡 | Kích hoạt luật |
| POST | `/api/v1/ai/rules/proposals/{id}/reject` | 🟡 | Từ chối đề xuất |
| POST | `/api/v1/ai/rules/{id}/pause` | 🟡 | Tạm dừng luật |
| POST | `/api/v1/ai/rules/{id}/rollback` | 🟡 | Rollback luật |

</details>

<details>
<summary><b>📈 Trends & audit</b></summary>

<br/>

| Method | Endpoint | Quyền | Mô tả |
|:-------|:---------|:-----:|:------|
| GET | `/api/v1/trends/apify-usage` | 🔵 | Dùng lượng Apify |
| GET | `/api/v1/trends/radar` | 🔵 | Radar xu hướng TikTok |
| GET | `/api/v1/trends/{trend_id}` | 🔵 | Chi tiết một trend |
| GET | `/api/v1/audit` | 🔴 | Audit trail toàn hệ thống |
| GET | `/api/v1/ab` | 🟢 | Bảng A/B (chưa đo live) |
| GET | `/api/v1/vf/conflict` | 🟢 | Demo phát hiện mâu thuẫn bàn giao |

</details>

---

<a id="packages"></a>
## 📦 Packages Python — API nội bộ

<details>
<summary><b>📜 <code>ca_contracts</code></b> — packages/contracts</summary>

<br/>

Schema Pydantic chia sẻ: `NhanVien`, `Ca`, `LichTuan`, `PhieuMau`, `RangBuocTrichXuat`, `MonNuoc`, `DongDon`, `DonQuay`, `DoanThoaiTranscript`, `ActionItem`, `CopilotIntent`, `CopilotResponse`, `ActionProposal`, `CAPABILITY_REGISTRY`, `COPILOT_ROLE_INTENT_MATRIX`.

</details>

<details>
<summary><b>🧮 <code>ca_solver</code></b> — packages/solver</summary>

<br/>

| Hàm | Mô tả |
|:----|:------|
| `solve_cpsat(data, time_limit_s=60)` | Giải lịch tuần CP-SAT: C01 kỹ năng, C02 đủ người, C03 không đè ca, C04 khoảng nghỉ, C05 trần giờ, C06 TKB/nghỉ phép + soft + minimize max debt |
| `solve_hard_only(data)` | Chỉ kiểm 6 ràng buộc cứng, không giải |
| `build_lich_input(nhan_vien_ngoai=…)` | Dựng `LichInput` từ seed + pool NV thật |
| `load_seed()` | Đọc `data/seed/sample.json` |
| `apply_luat(inp, luat)` | Bơm luật hiệu lực cẩm nang vào input solver |
| `sinh_ly_do(…)` / `sinh_ly_do_toan_lich(…)` | Sinh mã lý do từng phân công / toàn lịch |
| `update_debt_from_assignment` / `zero_debt` | Cập nhật số dư công bằng 4 trục (AXES) |

</details>

<details>
<summary><b>🚧 <code>ca_gates</code></b> — packages/gates</summary>

<br/>

| Hàm | Mô tả |
|:----|:------|
| `run_vf_pipeline(extraction, evidence, schema_keys, …)` | Chạy VF-SCHEMA → VF-TRACE → VF-CONF một lượt, trả `GateResult` |
| `validate_schema` / `validate_trace` / `validate_conf` | 3 cổng lọc trích xuất (fail-closed, retry một lần) |
| `validate_rule` / `validate_scope` / `validate_stale` | Cổng luật, phạm vi vai, snapshot stale |
| `validate_num` | Cổng số liệu bàn giao |
| `present_conflict(a, b)` | Trình bày mâu thuẫn claim |
| `compute_snapshot_hash` | Hash snapshot cho VF-STALE |

</details>

<details>
<summary><b>✅ <code>ca_ops</code></b> — packages/opsengine</summary>

<br/>

| Hàm | Mô tả |
|:----|:------|
| `load_template(ma)` | Đọc phiếu YAML từ `infra/templates/` |
| `start_phieu(run_id, mau, nv_id, ca_id, now_ms, diem_danh)` | Khởi tạo `PhieuRun` (chặn nếu chưa điểm danh) |
| `complete_buoc(run, ma, gia_tri, now_ms)` | Hoàn thành bước đúng thứ tự + anti-fake (nhanh, ảnh quá nhanh, ngưỡng số) |
| `add_treo(run, noi_dung)` | Thêm việc treo |
| `escalate(run, now_ms, han_phut=30)` | Nhắc 2 cấp: `nhac_nhan_vien` → `bao_chu_quan` |
| `dump_run` / `load_run` / `run_to_dict` | Serialize phiếu |

</details>

<details>
<summary><b>📓 <code>ca_playbook</code></b> — packages/playbook</summary>

<br/>

| Hàm | Mô tả |
|:----|:------|
| `record_sua(loai, truoc, sau, ai, now_iso)` | Ghi nhận lần sửa ca |
| `list_sua(include_synthetic=…)` | Danh sách lần sửa |
| `tim_mau(sua)` | Bước 1: tìm mẫu lỗi lặp ≥ 3 lần |
| `de_xuat(mau, sua_rows, ban_nhap)` | Bước 3: dựng luật ứng viên (không bịa — không nguồn trả None) |
| `kiem_chung(luat)` | Bước 4: VF-RULE kiểm chứng |
| `tap_su_tu_sua(luat, sua)` | Bước 5: tập sự từ lần sửa thật |
| `duyet(luat, ok, ai)` / `go_luat(luat, ai)` | Bước 6 chốt / bước 8 gỡ |
| `list_luat` / `save_luat` / `theo_doi` | Quản lý luật |
| `derive_rule_from_edits(mau, sua_rows)` | Suy tất định luật từ lần sửa |
| `pipeline_snapshot()` / `count_luat_that_quan` / `enrich_luat_ui` | Snapshot pipeline + đếm luật quán thật |
| `parse_sop_markdown` / `generate_skill_content` / `distill_sop_to_dir` | Chưng cất SOP → Skill |

</details>

<details>
<summary><b>🤖 <code>ca_agents</code></b> — packages/agents</summary>

<br/>

| Thành phần | Mô tả |
|:-----------|:------|
| `FreeTierRouter` | Route groq → gemini → openrouter → ollama (vision: gemini trước); hết → `tu_choi` |
| `complete()` / `parse_json_object()` (llm.py) | Gọi LLM fail-closed, không bịa payload |
| `agent_mode()` | Đọc `CA_AGENT_MODE` (replay mặc định) |
| `AgentRuntime` / `SkillLoader` / `SkillRef` | Runtime prompt versioned + cache + nạp skill theo trigger |
| `get_port(name)` (messaging.py) | Cổng tin: `replay` / `telegram` / `zalo` / `console` |
| `run_copilot(message, context)` | AG-COPILOT: parse intent → VF-SCOPE → tool whitelist → proposal 2 pha |
| `classify(text, mode, staff)` (ag_msg) | 6 intents 2 tầng + trích ràng buộc có cấu trúc |
| `extract_tkb(source, mode)` (ag_tkb) | Trích TKB từ ảnh (replay fixture / live vision) |
| `find_swap_candidates(…)` (smart_swap) | Xếp hạng ứng viên thế ca |
| `propose_rule` (ag_rule) · `answer` (ag_sop) · `cluster` (ag_waste) · `extract` (ag_handover) | Agent chuyên trách |
| `ag_pricing` — `job_manager`, `orchestrator_v2`, `cost_dashboard`, `vision_menu_extractor`… | AG-PRICING: quản lý job khảo sát giá, điều phối SerpApi + Vision, dashboard chi phí |
| `ag_predict` — `detect_success_patterns`, `de_xuat_luat_tich_cuc` | AG-PREDICT: phát hiện mẫu thành công, đề xuất luật tích cực |
| `ag_explain` — `build_causal_chain`, `answer_reflection` | AG-EXPLAIN: dựng chuỗi nhân quả, trả lời reflection (grounded) |
| `ag_twin` — `simulate_scenario`, `simulate_virtual_staff` | AG-TWIN: mô phỏng kịch bản và nhân sự ảo bằng Math Layer |

</details>

---

<a id="agents"></a>
## 🤖 Agents Lô 1

Tổng cộng **21 agent** (17 agent Lô 1 + 4 agent bổ sung). Bảng dưới là các agent Lô 1; bốn agent bổ sung nằm ngay sau.

| Agent | Vai trò |
|:------|:--------|
| 🧑‍✈️ **AG-COPILOT** | Trợ lý hội thoại đầu não — parse intent, đề xuất hành động 2 pha, audit (có kênh voice qua Gemini Live) |
| 🖼 **AG-TKB** | Trích thời khoá biểu từ ảnh (vision) |
| 🏷 **AG-MSG** | Phân loại 6 ý định tin nhắn + trích ràng buộc |
| 📓 **AG-RULE** | Đề xuất luật cẩm nang từ mẫu lỗi |
| 📖 **AG-SOP** | Hỏi đáp quy trình, trích dẫn nguồn |
| 🗑 **AG-WASTE** | Cụm hóa ghi chú hao phí |
| 🤝 **AG-HANDOVER** | Trích bàn giao ca |
| 📰 **AG-BRIEF** | Sinh bản tin giao ban |
| 🎙 **AG-MEETING** | Trích biên bản họp → action items |
| ✉️ **AG-MAIL / AG-MAILWRITER** | Soạn + gửi mail |
| 💖 **AG-VOC** | Ghi nhớ khách quen, khen/chê |
| 📘 **AG-FBPAGE / AG-CONCIERGE** | Trực Page, báo giá, đặt bàn |
| ☕ **AG-BARISTA / AG-TREND / AG-SUPERVISOR** | Định mức pha / xu hướng / giám sát đầu ra |

### ➕ Agents bổ sung

| Agent | Vai trò | File |
|:------|:--------|:-----|
| 💰 **AG-PRICING** | Khảo sát giá đối thủ (SerpApi + Vision) | `ag_pricing` |
| 🔮 **AG-PREDICT** | Phát hiện mẫu thành công → đề xuất luật tích cực | `packages/agents/src/ca_agents/ag_predict.py` |
| 💡 **AG-EXPLAIN** | Dịch mã lý do solver thành câu tiếng Việt (grounded) | `packages/agents/src/ca_agents/ag_explain.py` |
| 🧪 **AG-TWIN** | Mô phỏng "nếu… thì…" bằng Math Layer | `packages/agents/src/ca_agents/ag_twin.py` |

---

<a id="skills"></a>
## 🧠 Thư viện Kỹ năng (Skills)

**14 kỹ năng** (13 skill chưng cất theo **Repo-To-Skill** / **Playbook-To-Skill** + 1 Skill Router), tuân chuẩn [Agent Skills Format](https://github.com/agentskills/agentskills). Mỗi skill gồm `SKILL.md` + `references/` + `scripts/` (smoke test offline). Xem [`skills/README.md`](./skills/README.md).

> [!TIP]
> **Skill Router** giữ context **≤ 1.500 tokens** bằng Progressive Disclosure — chỉ nạp skill khớp trigger từ khóa.

| Thành phần | Cách hoạt động |
|:-----------|:---------------|
| 🧭 Skill Router | Khớp **trigger từ khóa** của yêu cầu với metadata từng skill, chỉ nạp skill phù hợp |
| 📏 Ngân sách context | ≤ 1.500 tokens (Progressive Disclosure: metadata trước, nội dung đầy đủ khi khớp) |
| 🔌 Nạp trong code | `SkillLoader` / `SkillRef` (`ca_agents`) |
| ⚗️ Chưng cất mới | `POST /skills/distill-sop` (Hybrid mode) · `distill_sop_to_dir` (`ca_playbook`) |

---

<a id="kiem-thu"></a>
## 🧪 Kiểm thử & đánh giá

```bash
make test          # pytest toàn monorepo (CA_AGENT_MODE=replay)
make lint          # ruff + tsc
make bench         # solver tuần + verify_hard
make eval          # eval AG-TKB, AG-MSG, nhóm A §18.2
make metrics       # 7 con số §18.2 (tất định, fixture ADR-012)
cd apps/web && npm run test:e2e   # Playwright e2e
```

> [!NOTE]
> Mọi bản ghi fixture mang nhãn nguồn `mo_phong_fixture`; UI gắn nhãn dữ liệu mẫu qua `co_du_lieu_mau`.

**CI/CD** chạy trên GitHub Actions:

| Workflow | Vai trò |
|:---------|:--------|
| [![CI](https://github.com/KanTrun/Crew-Operations/actions/workflows/ci.yml/badge.svg)](https://github.com/KanTrun/Crew-Operations/actions/workflows/ci.yml) | `ci.yml` — lint + test |
| [![Skills Verify](https://github.com/KanTrun/Crew-Operations/actions/workflows/skills-verify.yml/badge.svg)](https://github.com/KanTrun/Crew-Operations/actions/workflows/skills-verify.yml) | `skills-verify.yml` — kiểm định kỹ năng |
| [![Docker GHCR](https://github.com/KanTrun/Crew-Operations/actions/workflows/docker-ghcr.yml/badge.svg)](https://github.com/KanTrun/Crew-Operations/actions/workflows/docker-ghcr.yml) | `docker-ghcr.yml` — build & đẩy image lên GHCR |

---

<a id="github"></a>
## 🌿 GitHub — nhánh & quy trình

**Remote:** `https://github.com/KanTrun/Crew-Operations.git` · Chi tiết: [`docs/github-operating-model.md`](./docs/github-operating-model.md)

### 🌳 Nhánh gốc

```mermaid
gitGraph
    commit id: "init"
    branch release/semifinal
    branch release/final
    checkout main
    commit id: "feat"
    commit id: "feat "
    checkout release/semifinal
    merge main tag: "v0.1.0-semifinal"
    checkout main
    commit id: "feat  "
    checkout release/final
    merge main tag: "v1.0.0-final"
```

| Nhánh | Vai trò |
|:------|:--------|
| `main` | Nguồn sự thật — luôn xanh, luôn demo được |
| `release/semifinal` | Đóng băng tuần 6 → tag `v0.1.0-semifinal` |
| `release/final` | Đóng băng tuần 8 → tag `v1.0.0-final` |

### 👥 Bốn vùng sở hữu (tiền tố nhánh)

| Người | Tiền tố nhánh | Sở hữu chính |
|:-----:|:--------------|:-------------|
| **A** | `feat/solver-*` `feat/gates-*` `feat/ops-*` `feat/playbook-*` | solver, gates, opsengine, playbook |
| **B** | `feat/api-*` `feat/orc-*` `ci/*` `chore/infra-*` | api, orchestration, CI, infra, Docker |
| **C** | `feat/agents-*` `feat/router-*` `feat/eval-*` | agents, router, eval, messaging |
| **D** | `feat/web-*` `feat/tpl-*` `docs/*` | Next.js PWA, YAML templates, docs |

**Luật:** nhánh `feat/*` ≤ 3 ngày · ≤ 2 nhánh mở/người · `git pull --rebase origin main` hằng ngày · vào `main` chỉ qua **squash merge** + PR. WIP: `wip/a|b|c|d/...` — cấm PR thẳng vào `main`.

### 📜 Quy tắc bất biến

1. 📑 Hợp đồng dữ liệu trước, mã nguồn sau
2. 💚 `main` luôn xanh và luôn demo được
3. 🔒 Không vào `main` nếu không qua PR được duyệt
4. 🚫 Không LLM ghi lịch / điều phối

---

<a id="tai-lieu"></a>
## 📚 Tài liệu

| Tài liệu | Nội dung |
|:---------|:---------|
| [`docs/runbook-demo.md`](./docs/runbook-demo.md) | Demo < 5 phút, 19 tài khoản, 6 kịch bản A–F |
| [`docs/huong-dan-demo-thi.md`](./docs/huong-dan-demo-thi.md) | Hướng dẫn demo thi |
| [`docs/phan-cong-nhanh.md`](./docs/phan-cong-nhanh.md) | Chia việc nhánh, thứ tự merge |
| [`docs/github-operating-model.md`](./docs/github-operating-model.md) | PR, CI 11 cổng, commits |
| [`docs/ket-qua-tong-hop.md`](./docs/ket-qua-tong-hop.md) | 12 con số hồ sơ §18.2 |
| [`docs/runbooks/`](./docs/runbooks/) | Kết nối Telegram, Zalo, Facebook |
| [`docs/adr/`](./docs/adr/) | Architecture Decision Records |
| [`THIRD_PARTY.md`](./THIRD_PARTY.md) | Phụ thuộc & license |

---

## 📄 License

Xem [`THIRD_PARTY.md`](./THIRD_PARTY.md) cho phụ thuộc và license của các thành phần.

<div align="center">

<br/>

**☕ NHỊP QUÁN** — *Ca làm việc là hạt nhân · Cẩm nang tự viết là bộ nhớ · Lõi không dùng LLM*

<sub>Xây dựng Hệ điều hành Doanh nghiệp số AI · Khoa CNTT HUTECH · 2026</sub>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:C68B59,50:6F4E37,100:3E2723&height=120&section=footer" width="100%" alt="footer" />

</div>