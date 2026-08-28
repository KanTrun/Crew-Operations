---
title: "Brainstorm — GitHub ownership + foundation delivery"
created: 2026-08-21
status: accepted
---

# Brainstorm — GitHub chia đội + nền chạy được

## Outcome

Repo `KanTrun/CA-CONG-BANG` có: (1) mô hình GitHub 4 vùng nhánh + CODEOWNERS + bảo vệ main + 11 cổng CI khung + conventional commits; (2) monorepo `nhip-quan` skeleton chạy `docker compose` / `make demo`; (3) plan Lot1 đã gắn GitHub ops; (4) pipeline cook tiếp từng phase trên `plans/`.

## Constraints

- Hồ sơ v3.0 §12 là nguồn sự thật ownership; không dùng 4 nhánh cá nhân sống dài
- Chỉ biết GitHub user thật: `@KanTrun` — A/B/C/D khác chưa có handle
- Ngân sách 0đ; stack hồ sơ: FastAPI, Next.js PWA, Postgres, Redis, worker, OR-Tools sau
- Không trim phạm vi user yêu cầu trên giấy; thực thi theo phase vì 104 ngày-người

## Non-goals

- Hoàn thành 10 agent + Cẩm nang 8 bước + 215 tests trong một phiên
- Bật branch protection bắt buộc review nếu chỉ 1 collaborator (sẽ document + bật khi đủ 4 người)
- Lô 2 agents

## Acceptance

- [ ] `main` trên GitHub có README + governance files + monorepo skeleton
- [ ] `.github/CODEOWNERS` + `docs/team.md` map A/B/C/D
- [ ] `docs/github-operating-model.md` đủ §12
- [ ] `infra/docker/compose.yml` chạy api+web+postgres+redis (+worker stub)
- [ ] Plan Lot1 có section GitHub ops; phase 01/02 todo GitHub xanh một phần
- [ ] Issue + PR foundation mở trên repo

## Approaches

| # | Approach | Assumes | Fails first |
|---|----------|---------|-------------|
| A | Governance + scaffold Docker ngay; cook phase-by-phase | User chấp nhận giao hàng dần | Muốn “xong hết sản phẩm” trong 1 PR |
| B | Vibe một PR chứa toàn Lot1 | Agent viết 104 md trong 1 session | Code nông, demo gãy, vi phạm kiến trúc |
| C | Chờ đủ 4 handle rồi mới CODEOWNERS | Đội đã có 4 account | Chặn cả init repo |

**Chọn A.** Rẻ bỏ nhất. CODEOWNERS tạm `@KanTrun` mọi vùng; `docs/team.md` chờ handle thật.

## Unresolved

1. GitHub handles cho người A, C, D (và B nếu không phải KanTrun)
2. Quán chính/dự bị (chặn nghiệp vụ T0 — không chặn scaffold kỹ thuật)
