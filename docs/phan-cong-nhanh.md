# Chia việc theo nhánh — bốn vùng sở hữu

Nguồn luật: hồ sơ §12 và `plans/260821-2221-nhip-quan-lot1-full-delivery/plan.md`.
Tài liệu này chốt **ai sở hữu đường dẫn nào**, **nhánh nào chứa gì**, và **thứ tự merge**
để bốn người làm song song mà không giẫm chân.

## 1. Bốn vùng sở hữu

| Người | Vùng | Tiền tố nhánh | Đường dẫn sở hữu |
|-------|------|---------------|------------------|
| **A** | Lõi tất định | `feat/solver-*` `feat/gates-*` `feat/ops-*` `feat/playbook-*` | `packages/solver` `packages/gates` `packages/opsengine` `packages/playbook` `scripts/solve_tuan.py` `scripts/verify_hard.py` |
| **B** | API · điều phối · hạ tầng | `feat/api-*` `feat/orc-*` `ci/*` `chore/infra-*` | `apps/api` `infra/docker` `.github` `Makefile` `.dockerignore` |
| **C** | Agent · router · eval | `feat/agents-*` `feat/router-*` `feat/eval-*` | `packages/agents` `scripts/eval_*.py` `scripts/ab_report.py` `scripts/replay_orc.py` |
| **D** | Web · template · tài liệu | `feat/web-*` `feat/tpl-*` `docs/*` | `apps/web` `infra/templates` `docs` |

`packages/contracts` đổi thì cần cả bốn duyệt — đổi hợp đồng là đổi luật chung.

## 2. Bảy nhánh đã tách (PR chồng trên PR #8)

Việc S3–S5 từng dồn hết vào `feat/ops-sprint3-van-hanh`. Nay tách thành bảy
nhánh chồng nhau: mỗi nhánh lấy nhánh trước làm base, nên mỗi PR chỉ hiện đúng
phần của mình và không nhánh nào đỏ vì thiếu phụ thuộc.

| # | Nhánh | Chủ | Nội dung | Phạm vi |
|---|-------|-----|----------|---------|
| 1 | `feat/solver-luat-inject` | A | Bơm luật hiệu lực vào tham số CP-SAT | `packages/solver/**` · `scripts/solve_tuan.py` |
| 2 | `feat/api-hom-nay-tieu-thu` | B | `/api/v1/me`, hôm nay giàu dữ liệu, sổ tiêu thụ, hao phí thật, giải CP-SAT khi chuyển `dang_giai` | `apps/api/src/ca_api/interfaces/http/{main,sprint45}.py` · test tương ứng |
| 3 | `chore/infra-docker-full-stack` | B | Image API đủ bảy package + dữ liệu instance, web multi-stage standalone, `.dockerignore`, volume `nhipquan_var`, healthcheck, target `docker-*` | `infra/docker/**` · `.dockerignore` · `.gitignore` · `Makefile` · `scripts/smoke_docker.py` |
| 4 | `feat/eval-ab-replay` | C | Bảng A/B và phát lại phiên điều phối | `scripts/ab_report.py` · `scripts/replay_orc.py` |
| 5 | `feat/web-ops-ui` | D | UI kit, session, lớp gọi API, điều hướng theo vai, trạng thái đang tải | `apps/web/src/**` |
| 6 | `ci/e2e-va-docker-smoke` | B | Cổng e2e Playwright + cổng Docker chạy smoke thật | `.github/workflows/ci.yml` · `apps/web/{playwright.config.ts,e2e/**,package*.json}` |
| 7 | `docs/runbook-va-trang-thai` | D | Runbook Docker, bản đồ mặt hồ sơ, gắn dữ liệu thật, walkthrough, đồng bộ plan | `docs/**` · `plans/**` |

`.github/workflows/ci.yml` đi trọn trong nhánh 6 dù có phần thuộc hạ tầng —
cùng chủ B, tách đôi một file chỉ làm review khó hơn.

## 3. Thứ tự merge

Merge từ trên xuống. GitHub tự trỏ lại base khi nhánh cha merge xong.

```
PR #8  feat/ops-sprint3-van-hanh   nền S3–S5 (đã xanh 11 cổng)
 └─ 1  feat/solver-luat-inject        A
     └─ 2  feat/api-hom-nay-tieu-thu      B — cần apply_luat của (1)
         └─ 3  chore/infra-docker-full-stack  B — cần API chạy được của (2)
             └─ 4  feat/eval-ab-replay            C
                 └─ 5  feat/web-ops-ui                D — cần endpoint của (2)
                     └─ 6  ci/e2e-va-docker-smoke        B — cần web của (5)
                         └─ 7  docs/runbook-va-trang-thai    D — chốt trạng thái
```

Mỗi PR: squash merge, tiêu đề Conventional Commits, một người duyệt theo CODEOWNERS.

> **Cần sửa cấu hình repo:** nhánh mặc định trên GitHub đang là
> `chore/infra-bootstrap`, không phải `main`. Hồ sơ §12 bảo vệ `main`, nên phải
> đổi lại default branch trước khi bật branch protection.

## 4. Luật nhánh

- Nhánh `feat/*` sống tối đa 3 ngày; tối đa 2 nhánh mở mỗi người.
- `git pull --rebase origin main` hằng ngày.
- Việc dở dang đẩy lên `wip/<a|b|c|d>/...`, cấm mở PR vào `main` từ `wip/*`.
- `release/semifinal` cắt ở S6, `release/final` ở S8; tag `v0.1.0-semifinal` và `v1.0.0-final`.
