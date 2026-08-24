# NHỊP QUÁN

Hệ sinh thái AI agent vận hành quán cà phê — ca làm việc là hạt nhân, cẩm nang tự viết là bộ nhớ.

**Cuộc thi:** Xây dựng Hệ điều hành Doanh nghiệp số AI · Khoa CNTT HUTECH · 2026  
**Repo:** https://github.com/KanTrun/CA-CONG-BANG  
**Hồ sơ:** [`NHIP-QUAN-HO-SO-TONG-THE .md`](./NHIP-QUAN-HO-SO-TONG-THE%20.md)  
**Plan:** [`plans/260821-2221-nhip-quan-lot1-full-delivery/`](./plans/260821-2221-nhip-quan-lot1-full-delivery/)

## Chạy nhanh (Docker)

```bash
docker compose -f infra/docker/compose.yml up --build
```

- Web: http://localhost:3000  
- API health: http://localhost:8000/health  
- Postgres: `localhost:5432` · Redis: `localhost:6379`

Hoặc:

```bash
make demo
```

## Đội & GitHub

Xem [`docs/team.md`](./docs/team.md) và [`docs/github-operating-model.md`](./docs/github-operating-model.md).

| Vai trò | Vùng nhánh | Sở hữu chính |
|---------|------------|--------------|
| A | `feat/solver-*` `feat/gates-*` `feat/ops-*` `feat/playbook-*` | solver, gates, opsengine, playbook |
| B | `feat/api-*` `feat/orc-*` `ci/*` `chore/infra-*` | api, orchestration, CI, infra |
| C | `feat/agents-*` `feat/router-*` `feat/eval-*` | 9 agents Lô 1, router, eval |
| D | `feat/web-*` `feat/tpl-*` `docs/*` | Next.js PWA, YAML templates, docs |

## Quy tắc bất biến

1. Hợp đồng dữ liệu trước, mã nguồn sau  
2. `main` luôn xanh và luôn demo được  
3. Không vào `main` nếu không qua PR được duyệt  
4. Không LLM ghi lịch / điều phối  

## Makefile

`setup` · `contracts` · `dev` · `test` · `lint` · `demo` · `demo-reset` · `seed` · `bench` · `eval`
